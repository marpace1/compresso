"""Smart optimizer for Compresso (compresso).

Performs binary-search optimisation to find the lowest quality setting
that still meets a target SSIM threshold, ensuring maximum compression
with acceptable visual fidelity.
"""

from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from models import (
    ImageInfo,
    AnalysisResult,
    CompressionSettings,
    CompressionResult,
)
from utils.logger import setup_logger


class SmartOptimizer:
    """Smart optimisation: binary search for optimal quality to meet SSIM target.

    Uses in-memory compression (``io.BytesIO``) for speed so that each
    search iteration avoids disk I/O.
    """

    def __init__(self) -> None:
        self.logger = setup_logger("optimizer")
        self._compressor = None  # Lazy init to avoid circular import
        self._metrics = None

    # ------------------------------------------------------------------
    # Lazy-imported dependencies
    # ------------------------------------------------------------------

    def _get_compressor(self):
        if self._compressor is None:
            from core.compressor import ImageCompressor

            self._compressor = ImageCompressor()
        return self._compressor

    def _get_metrics(self):
        if self._metrics is None:
            from core.metrics import QualityMetrics

            self._metrics = QualityMetrics()
        return self._metrics

    # ------------------------------------------------------------------
    # In-memory compression helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compress_to_bytes(
        image: Image.Image,
        settings: CompressionSettings,
    ) -> bytes:
        """Compress *image* in-memory and return the raw bytes.

        This mirrors the logic in ``ImageCompressor`` but writes to a
        ``BytesIO`` buffer instead of a file.
        """
        fmt = settings.output_format.upper()
        buf = io.BytesIO()

        pil_quality = ImageCompressor._map_quality_to_pil(
            settings.quality_percent, settings.compression_percent
        )

        if fmt == "JPEG":
            if image.mode != "RGB":
                rgb = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode in ("RGBA", "LA", "PA"):
                    rgb.paste(image, mask=image.split()[-1])
                    image = rgb
                else:
                    image = image.convert("RGB")
            image.save(
                buf, format="JPEG", quality=pil_quality,
                optimize=True, progressive=True,
            )

        elif fmt == "PNG":
            compress_level = min(9, max(0, int(settings.compression_percent / 95.0 * 9)))
            image.save(buf, format="PNG", optimize=True, compress_level=compress_level)

        elif fmt == "WEBP":
            method = min(6, max(0, int(settings.compression_percent / 95.0 * 6)))
            image.save(buf, format="WEBP", quality=pil_quality, method=method)

        elif fmt == "AVIF":
            image.save(buf, format="AVIF", quality=pil_quality, speed=8)

        else:
            # Fallback to JPEG
            image.save(buf, format="JPEG", quality=pil_quality, optimize=True)

        buf.seek(0)
        return buf.getvalue()

    @staticmethod
    def _image_to_cv2(image: Image.Image) -> np.ndarray:
        """Convert a PIL Image to an OpenCV (BGR) uint8 numpy array."""
        if image.mode == "RGBA":
            arr = np.array(image.convert("RGBA"))
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        if image.mode == "RGB":
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        if image.mode == "L":
            return np.array(image)
        # Fallback: convert to RGB first
        return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize_for_ssim(
        self,
        image_info: ImageInfo,
        analysis: AnalysisResult,
        settings: CompressionSettings,
        target_ssim: float = 0.95,
        max_iterations: int = 5,
    ) -> tuple[CompressionSettings, CompressionResult | None]:
        """Binary search for quality that achieves *target_ssim*.

        1. Compress with current settings, measure SSIM.
        2. If below target → increase quality (decrease compression), retry.
        3. If above target → could compress more (increase compression), retry.
        4. Return ``(adjusted_settings, best_result)``.

        Uses in-memory compression (``io.BytesIO``) for speed.
        """
        self.logger.info(
            "Starting SSIM optimisation: target=%.4f, max_iter=%d",
            target_ssim,
            max_iterations,
        )

        # Load original image once
        try:
            original_pil = Image.open(image_info.filepath)
        except Exception as exc:
            self.logger.error("Failed to open image for optimisation: %s", exc)
            return settings, None

        original_cv2 = self._image_to_cv2(original_pil)
        metrics = self._get_metrics()

        # Search bounds for quality_percent (80-100) and compression_percent (0-95).
        # We fix quality_percent and vary compression_percent to find the sweet spot.
        lo_comp = 0
        hi_comp = settings.compression_percent
        best_settings = settings
        best_result: CompressionResult | None = None
        best_ssim = 0.0

        for i in range(max_iterations):
            mid_comp = (lo_comp + hi_comp) // 2
            trial_settings = replace(settings, compression_percent=mid_comp)

            # In-memory compress
            try:
                compressed_bytes = self._compress_to_bytes(original_pil, trial_settings)
            except Exception as exc:
                self.logger.warning("Compression attempt %d failed: %s", i, exc)
                lo_comp = mid_comp + 1
                continue

            # Decode compressed bytes back to image for SSIM comparison
            try:
                compressed_pil = Image.open(io.BytesIO(compressed_bytes))
                compressed_cv2 = self._image_to_cv2(compressed_pil)
            except Exception as exc:
                self.logger.warning("Decode attempt %d failed: %s", i, exc)
                lo_comp = mid_comp + 1
                continue

            ssim_score = metrics.calculate_ssim(original_cv2, compressed_cv2)
            self.logger.debug(
                "Iter %d: comp=%d, ssim=%.4f, size=%d",
                i, mid_comp, ssim_score, len(compressed_bytes),
            )

            # Build a CompressionResult for tracking
            result = CompressionResult(
                success=True,
                output_path=None,  # in-memory only
                output_size=len(compressed_bytes),
                original_size=image_info.file_size,
                compression_ratio=(
                    1.0 - len(compressed_bytes) / image_info.file_size
                    if image_info.file_size > 0
                    else 0.0
                ),
                space_saved=max(0, image_info.file_size - len(compressed_bytes)),
                ssim=ssim_score,
                format_used=trial_settings.output_format,
                quality_used=trial_settings.quality_percent,
            )

            # Track best result: highest compression that still meets target
            if ssim_score >= target_ssim:
                # Meets target — try to compress more (increase compression)
                if ssim_score >= best_ssim or (best_ssim < target_ssim):
                    best_settings = trial_settings
                    best_result = result
                    best_ssim = ssim_score
                lo_comp = mid_comp + 1
            else:
                # Below target — reduce compression (increase quality)
                hi_comp = mid_comp - 1

            # Early exit if we've converged
            if lo_comp > hi_comp:
                break

        self.logger.info(
            "Optimisation complete: best_comp=%d, best_ssim=%.4f",
            best_settings.compression_percent,
            best_ssim,
        )

        return best_settings, best_result

    def find_optimal_settings(
        self,
        image_info: ImageInfo,
        analysis: AnalysisResult,
    ) -> CompressionSettings:
        """Find the best *CompressionSettings* for this image.

        Uses the analysis result to pick a format, then runs a binary
        search to find the highest compression that keeps SSIM > 0.95.
        """
        # Choose format based on analysis recommendation
        fmt = analysis.recommended_format.upper()
        if fmt not in CompressionSettings.VALID_FORMATS or fmt == "ORIGINAL":
            fmt = "JPEG"

        # Start with the analysis-recommended values
        base_settings = CompressionSettings(
            compression_percent=analysis.recommended_compression,
            quality_percent=analysis.recommended_quality,
            output_format=fmt,
            remove_metadata=True,
            preset="custom",
            smart_mode=True,
        )

        # Run optimisation
        adjusted_settings, result = self.optimize_for_ssim(
            image_info=image_info,
            analysis=analysis,
            settings=base_settings,
            target_ssim=0.95,
            max_iterations=5,
        )

        if result is not None and result.ssim is not None:
            self.logger.info(
                "Optimal settings: fmt=%s, comp=%d, quality=%d → ssim=%.4f, saved=%s",
                adjusted_settings.output_format,
                adjusted_settings.compression_percent,
                adjusted_settings.quality_percent,
                result.ssim,
                f"{result.space_saved / 1024:.1f} KB",
            )

        return adjusted_settings