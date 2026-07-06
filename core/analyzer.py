"""Image analyzer for Compresso (compresso).

Analyses image characteristics (noise, texture, edges, sharpness,
entropy, colour distribution) and recommends compression settings
based on the results.  All analysis completes in < 500 ms.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from skimage import feature, filters

from .metadata import MetadataHandler
from models import AnalysisResult, ImageInfo
from utils.logger import setup_logger


class ImageAnalyzer:
    """Analyze image characteristics for smart compression."""

    def __init__(self) -> None:
        self.logger = setup_logger("analyzer")
        self._metadata_handler = MetadataHandler()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_image_info(self, filepath: Path) -> ImageInfo:
        """Load image and extract all basic info.

        Parameters
        ----------
        filepath:
            Path to the image file.

        Returns
        -------
        ImageInfo
        """
        pil_img = Image.open(filepath)
        width, height = pil_img.size
        fmt = (pil_img.format or "UNKNOWN").upper()
        file_size = filepath.stat().st_size
        mode = pil_img.mode
        has_alpha = "A" in mode or pil_img.mode == "PA"

        # Channel count
        num_channels = len(pil_img.getbands())

        # Bit depth from mode
        bit_depth = self._bit_depth_from_mode(mode)

        return ImageInfo(
            filepath=filepath,
            filename=filepath.name,
            format=fmt,
            width=width,
            height=height,
            bit_depth=bit_depth,
            has_alpha=has_alpha,
            file_size=file_size,
            color_mode=mode,
            num_channels=num_channels,
        )

    def analyze(self, image_info: ImageInfo) -> AnalysisResult:
        """Run the full analysis pipeline on an image.

        All heavy computation uses OpenCV / NumPy vectorised operations
        and completes in < 500 ms for typical images.

        Parameters
        ----------
        image_info:
            Pre-populated :class:`ImageInfo` (see :meth:`get_image_info`).

        Returns
        -------
        AnalysisResult
        """
        # Load with OpenCV (fast; returns BGR, uint8)
        filepath = str(image_info.filepath)
        img_bgr = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)

        if img_bgr is None:
            self.logger.error("cv2 could not read %s", filepath)
            return AnalysisResult()

        # Ensure uint8
        if img_bgr.dtype != np.uint8:
            if img_bgr.max() <= 1.0:
                img_bgr = (img_bgr * 255).astype(np.uint8)
            else:
                img_bgr = np.clip(img_bgr, 0, 255).astype(np.uint8)

        # Grayscale for most metrics
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if img_bgr.ndim == 3 else img_bgr

        # Calculate all metrics (all vectorised – fast)
        noise = self._calculate_noise_level(gray)
        texture = self._calculate_texture_complexity(gray)
        edge_density = self._calculate_edge_density(gray)
        sharpness = self._calculate_sharpness(gray)
        entropy = self._calculate_entropy(gray)
        color_dist = self._calculate_color_distribution(img_bgr) if img_bgr.ndim == 3 else 0.5

        metadata_size = self._metadata_handler.get_metadata_size(image_info.filepath)
        already_compressed = self._estimate_already_compressed(image_info)

        difficulty, difficulty_label = self._compute_difficulty(
            noise, texture, edge_density, entropy, already_compressed
        )

        compression_potential = self._estimate_compression_potential(
            noise=noise,
            texture=texture,
            edge=edge_density,
            entropy=entropy,
            already_compressed=already_compressed,
            difficulty=difficulty,
        )

        rec_format, rec_quality, rec_compression = self._recommend_settings(
            analysis={
                "noise": noise,
                "texture": texture,
                "edge_density": edge_density,
                "sharpness": sharpness,
                "entropy": entropy,
                "color_distribution": color_dist,
                "already_compressed": already_compressed,
                "difficulty": difficulty,
                "compression_potential": compression_potential,
            },
            image_info=image_info,
        )

        return AnalysisResult(
            noise_level=round(noise, 4),
            texture_complexity=round(texture, 4),
            edge_density=round(edge_density, 4),
            sharpness=round(sharpness, 4),
            entropy=round(entropy, 4),
            color_distribution_score=round(color_dist, 4),
            metadata_size=metadata_size,
            is_already_compressed=already_compressed,
            compression_difficulty=round(difficulty, 4),
            difficulty_label=difficulty_label,
            estimated_compression_potential=round(compression_potential, 4),
            recommended_format=rec_format,
            recommended_quality=rec_quality,
            recommended_compression=rec_compression,
        )

    # ------------------------------------------------------------------
    # Individual metric calculators
    # ------------------------------------------------------------------

    def _calculate_noise_level(self, gray: np.ndarray) -> float:
        """Estimate noise via the median absolute deviation of a Laplacian.

        A Gaussian-noise-robust estimator: the MAD of the Laplacian
        approximates σ for Gaussian noise.  Result is normalised to [0, 1].
        """
        try:
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            mad = np.median(np.abs(lap))
            # σ_noise ≈ mad / 0.6745  (for Gaussian distribution)
            sigma = mad / 0.6745
            # Normalise: typical noise σ is 0-30 for uint8; clamp to [0, 1]
            return float(np.clip(sigma / 30.0, 0.0, 1.0))
        except Exception:
            self.logger.exception("Noise estimation failed")
            return 0.0

    def _calculate_texture_complexity(self, gray: np.ndarray) -> float:
        """Estimate texture complexity via variance of the Laplacian.

        Higher variance → more texture detail.  Normalised to [0, 1].
        """
        try:
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            var = float(np.var(lap))
            # Typical var(Laplacian) ranges 0-5000 for natural images
            return float(np.clip(var / 5000.0, 0.0, 1.0))
        except Exception:
            self.logger.exception("Texture complexity calculation failed")
            return 0.0

    def _calculate_edge_density(self, gray: np.ndarray) -> float:
        """Canny edge detection; ratio of edge pixels to total pixels."""
        try:
            edges = cv2.Canny(gray, 50, 150)
            edge_count = int(np.count_nonzero(edges))
            total = gray.shape[0] * gray.shape[1]
            if total == 0:
                return 0.0
            return float(np.clip(edge_count / total, 0.0, 1.0))
        except Exception:
            self.logger.exception("Edge density calculation failed")
            return 0.0

    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """Variance of the Laplacian as a sharpness metric.

        Normalised to [0, 1].  Higher values indicate sharper images.
        """
        try:
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            var = float(np.var(lap))
            # Typical range: 0-10000 for natural images
            return float(np.clip(var / 10000.0, 0.0, 1.0))
        except Exception:
            self.logger.exception("Sharpness calculation failed")
            return 0.0

    def _calculate_entropy(self, gray: np.ndarray) -> float:
        """Shannon entropy of the grayscale histogram, normalised by log2(256)=8."""
        try:
            hist = np.histogram(gray, bins=256, range=(0, 256))[0].astype(np.float64)
            total = hist.sum()
            if total == 0:
                return 0.0
            prob = hist / total
            # Ignore zero-probability bins
            mask = prob > 0
            entropy = -np.sum(prob[mask] * np.log2(prob[mask]))
            # Normalise by maximum possible entropy (8 bits)
            return float(np.clip(entropy / 8.0, 0.0, 1.0))
        except Exception:
            self.logger.exception("Entropy calculation failed")
            return 0.0

    def _calculate_color_distribution(self, img_bgr: np.ndarray) -> float:
        """How spread-out colours are across channels.

        Uses the mean standard deviation of the B, G, R channels.
        Normalised by 128 (max sensible std for uint8).
        """
        try:
            stds = [float(np.std(img_bgr[:, :, ch])) for ch in range(img_bgr.shape[2])]
            avg_std = sum(stds) / len(stds)
            return float(np.clip(avg_std / 128.0, 0.0, 1.0))
        except Exception:
            self.logger.exception("Color distribution calculation failed")
            return 0.5

    # ------------------------------------------------------------------
    # Heuristics
    # ------------------------------------------------------------------

    def _estimate_already_compressed(self, image_info: ImageInfo) -> bool:
        """Heuristic: is the image already well-compressed?

        Compare file size to raw pixel data size.  If the file is
        smaller than a reasonable compressed expectation, consider it
        already compressed.
        """
        try:
            raw_size = (
                image_info.width
                * image_info.height
                * image_info.num_channels
                * (image_info.bit_depth // 8)
            )
            if raw_size == 0:
                return False

            ratio = image_info.file_size / raw_size

            # JPEG/WEBP/AVIF images with ratio < 0.15 are likely
            # already heavily compressed.  PNG with ratio > 0.5 but
            # < 1.5 may be uncompressible.
            fmt = image_info.format.upper()
            if fmt in ("JPEG", "JPG", "WEBP", "AVIF"):
                return ratio < 0.15
            if fmt == "PNG":
                return ratio < 0.30

            # Generic: if file is < 10% of raw, assume compressed
            return ratio < 0.10
        except Exception:
            return False

    def _compute_difficulty(
        self,
        noise: float,
        texture: float,
        edge: float,
        entropy: float,
        already_compressed: bool,
    ) -> tuple[float, str]:
        """Weighted combination of analysis factors.

        Returns
        -------
        tuple[float, str]
            ``(difficulty_0_to_1, label)`` where label is one of
            ``"Easy"``, ``"Medium"``, ``"Hard"``, ``"Very Hard"``.
        """
        # Weights reflect how much each factor hurts compressibility
        difficulty = (
            0.20 * noise
            + 0.20 * texture
            + 0.15 * edge
            + 0.25 * entropy
            + 0.20 * (0.8 if already_compressed else 0.0)
        )
        difficulty = float(np.clip(difficulty, 0.0, 1.0))

        if difficulty >= 0.75:
            label = "Very Hard"
        elif difficulty >= 0.50:
            label = "Hard"
        elif difficulty >= 0.25:
            label = "Medium"
        else:
            label = "Easy"

        return difficulty, label

    def _estimate_compression_potential(
        self,
        noise: float,
        texture: float,
        edge: float,
        entropy: float,
        already_compressed: bool,
        difficulty: float,
    ) -> float:
        """Estimate how much the image can be compressed (0-1).

        High potential means the image has room for size reduction.
        """
        if already_compressed:
            return float(np.clip(0.15 - difficulty * 0.1, 0.0, 1.0))

        # Low difficulty → high potential; high difficulty → low potential
        potential = 1.0 - difficulty
        # Boost for low-entropy (simple) images
        if entropy < 0.4:
            potential = min(1.0, potential + 0.15)
        # Reduce for noisy/texture-rich images
        if noise > 0.6 or texture > 0.6:
            potential = max(0.0, potential - 0.1)

        return float(np.clip(potential, 0.0, 1.0))

    def _recommend_settings(
        self, analysis: dict[str, Any], image_info: ImageInfo
    ) -> tuple[str, int, int]:
        """Recommend ``(format, quality, compression_percent)``.

        The recommendation considers:
        * Alpha channel → lossless format (PNG / WEBP)
        * Already compressed → same format, modest quality reduction
        * High compression potential → AVIF or WEBP with aggressive settings
        * Difficulty level → quality / compression trade-off
        """
        has_alpha = image_info.has_alpha
        current_fmt = image_info.format.upper()
        difficulty = analysis["difficulty"]
        potential = analysis["compression_potential"]
        sharpness = analysis["sharpness"]
        already_compressed = analysis["already_compressed"]

        # Default fallback
        rec_format = "JPEG"
        rec_quality = 85
        rec_compression = 50

        if has_alpha:
            # Must preserve alpha → PNG or WEBP
            if potential > 0.6:
                rec_format = "WEBP"
                rec_quality = 80
                rec_compression = 60
            else:
                rec_format = "PNG"
                rec_quality = 100  # PNG quality param is compression level (0-9)
                rec_compression = 40

        elif already_compressed:
            # Already compressed well – keep same format, gentle tweak
            if current_fmt in ("JPEG", "JPG"):
                rec_format = "JPEG"
                rec_quality = 82
                rec_compression = 30
            elif current_fmt == "WEBP":
                rec_format = "WEBP"
                rec_quality = 80
                rec_compression = 30
            elif current_fmt == "AVIF":
                rec_format = "AVIF"
                rec_quality = 78
                rec_compression = 30
            else:
                rec_format = "WEBP"
                rec_quality = 82
                rec_compression = 35

        elif potential > 0.7:
            # High compression potential
            if difficulty < 0.3:
                rec_format = "AVIF"
                rec_quality = 65
                rec_compression = 80
            else:
                rec_format = "WEBP"
                rec_quality = 75
                rec_compression = 70

        elif potential > 0.4:
            # Moderate potential
            rec_format = "WEBP"
            rec_quality = 80
            rec_compression = 55

        else:
            # Low potential – preserve quality
            if current_fmt in ("JPEG", "JPG"):
                rec_format = "JPEG"
                rec_quality = 90
                rec_compression = 30
            elif current_fmt == "PNG":
                rec_format = "PNG"
                rec_quality = 100
                rec_compression = 20
            else:
                rec_format = "WEBP"
                rec_quality = 90
                rec_compression = 30

        # Adjust quality/compression based on sharpness (sharp images
        # tolerate slightly lower quality before artifacts are visible)
        if sharpness > 0.6 and rec_quality > 70:
            rec_quality = max(60, rec_quality - 5)
            rec_compression = min(95, rec_compression + 5)

        # Adjust based on difficulty
        if difficulty > 0.5:
            rec_quality = min(100, rec_quality + 5)
            rec_compression = max(10, rec_compression - 10)

        return rec_format, rec_quality, rec_compression

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bit_depth_from_mode(mode: str) -> int:
        """Infer bit depth from a PIL mode string."""
        _depth_map: dict[str, int] = {
            "1": 1,
            "L": 8,
            "P": 8,
            "RGB": 24,
            "RGBA": 32,
            "RGBX": 32,
            "CMYK": 32,
            "YCbCr": 24,
            "LAB": 24,
            "HSV": 24,
            "I": 32,
            "F": 32,
            "LA": 16,
            "PA": 16,
            "L16": 16,  # Pillow extension
            "I;16": 16,
            "I;16B": 16,
            "I;16L": 16,
        }
        # 16-bit modes with extra suffixes
        if mode.startswith("I;16"):
            return 16
        return _depth_map.get(mode, 8)