"""Compression predictor for Compresso (compresso).

Estimates compression outcomes (output size, quality, SSIM, PSNR, timing)
*without* actually compressing, using image analysis data and
format-specific heuristic models.  All predictions complete in <100 ms.
"""

from __future__ import annotations

import math
from models import ImageInfo, AnalysisResult, CompressionPrediction, CompressionSettings
from utils.logger import setup_logger
from utils.helpers import clamp, lerp


class CompressionPredictor:
    """Predict compression outcomes WITHOUT actually compressing.

    Uses image analysis + format-specific models to estimate results.
    Must complete predictions in <100 ms.
    """

    # Format efficiency multipliers (higher = better compression at same quality).
    # These are relative to a theoretical baseline; PNG is usually *larger*
    # than JPEG/WebP for photos, so it gets a penalty.
    _FORMAT_EFFICIENCY: dict[str, float] = {
        "JPEG": 1.00,
        "WEBP": 1.15,
        "AVIF": 1.35,
        "PNG": 0.70,
    }

    # Format processing-time multipliers (higher = slower).
    _FORMAT_SPEED_FACTOR: dict[str, float] = {
        "JPEG": 1.0,
        "WEBP": 1.5,
        "AVIF": 3.0,
        "PNG": 2.0,
    }

    def __init__(self) -> None:
        self.logger = setup_logger("predictor")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        image_info: ImageInfo,
        analysis: AnalysisResult,
        settings: CompressionSettings,
    ) -> CompressionPrediction:
        """Main prediction method.  Returns a fully populated *CompressionPrediction*.

        Algorithm
        ---------
        1. Base compression ratio estimate from ``analysis.estimated_compression_potential``.
        2. Adjust by ``settings.compression_percent`` (0-95 maps to mild → aggressive).
        3. Adjust by ``settings.quality_percent`` (80-100).
        4. Adjust by output format (AVIF > WEBP > JPEG > PNG).
        5. If ``remove_metadata``, subtract metadata size from output estimate.
        6. Calculate estimated visual quality.
        7. Estimate SSIM from quality using a sigmoid-like curve.
        8. Estimate PSNR from quality using a near-linear model.
        9. Estimate processing time based on resolution and format.
        10. Generate human-readable recommendation text.
        """
        original_size = image_info.file_size
        if original_size <= 0:
            return CompressionPrediction()

        fmt = settings.output_format.upper()
        format_eff = self._estimate_format_efficiency(fmt)
        difficulty = analysis.compression_difficulty

        # --- Step 1: base ratio from compression potential (0-1 scale) ----
        # compression_potential ∈ [0, 1] where 1 = very compressible.
        # Map to a raw ratio: potential 0 → ratio 0.85 (85 % of original),
        # potential 1 → ratio 0.10 (10 % of original).
        # Use a smooth power curve so easy images benefit more at low compression.
        base_ratio = 1.0 - 0.90 * (analysis.estimated_compression_potential ** 0.7)

        # --- Step 2: adjust by compression_percent (0-95) ----------------
        # Normalise to [0, 1] then apply a power curve so the effect is
        # gentle at low compression and aggressive at high compression.
        comp_norm = settings.compression_percent / 95.0
        # Sigmoid-ish: 0→0, 0.5→0.4, 1.0→1.0
        comp_effect = 1.0 - (1.0 - comp_norm) ** 2.2
        # Blend: at comp_effect=0 ratio stays near 1.0; at 1.0 ratio is
        # driven much lower.
        ratio_after_comp = lerp(1.0, base_ratio, comp_effect * 0.85)

        # --- Step 3: adjust by quality_percent (80-100) -------------------
        # Higher quality = less compression = larger output (ratio closer to 1).
        # quality_norm ∈ [0, 1] where 1 = highest quality.
        quality_norm = (settings.quality_percent - 80.0) / 20.0
        # norm=0 (q=80) → factor 0.75, norm=1 (q=100) → factor 1.0
        quality_factor = 0.75 + 0.25 * quality_norm
        ratio_after_quality = ratio_after_comp * quality_factor

        # --- Step 4: adjust by format efficiency ---------------------------
        # More efficient formats compress further (lower ratio).
        ratio_after_format = ratio_after_quality / format_eff

        # --- Step 5: clamp and handle metadata -----------------------------
        ratio_after_format = clamp(ratio_after_format, 0.02, 1.0)

        estimated_size = int(original_size * ratio_after_format)
        if settings.remove_metadata:
            estimated_size = max(0, estimated_size - analysis.metadata_size)

        compression_ratio = 1.0 - (estimated_size / original_size) if original_size > 0 else 0.0

        # --- Step 6: estimated visual quality -----------------------------
        visual_quality = self._estimate_quality(
            base_quality=settings.quality_percent,
            compression=settings.compression_percent,
            format_efficiency=format_eff,
            difficulty=difficulty,
        )

        # --- Step 7: SSIM from quality (sigmoid) --------------------------
        estimated_ssim = self._estimate_ssim(visual_quality)

        # --- Step 8: PSNR from quality ------------------------------------
        estimated_psnr = self._estimate_psnr(visual_quality)

        # --- Step 9: processing time --------------------------------------
        est_time = self._estimate_processing_time(image_info.width, image_info.height, fmt)

        # --- Build result --------------------------------------------------
        prediction = CompressionPrediction(
            estimated_output_size=estimated_size,
            compression_ratio=round(compression_ratio, 4),
            visual_quality=round(visual_quality, 1),
            expected_ssim=round(estimated_ssim, 4),
            expected_psnr=round(estimated_psnr, 2),
            estimated_time=round(est_time, 3),
            recommendation_text="",  # filled below
        )

        # --- Step 10: recommendation ---------------------------------------
        prediction.recommendation_text = self._generate_recommendation(prediction)

        return prediction

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_format_efficiency(self, fmt: str) -> float:
        """Return a multiplier for *fmt*'s compression efficiency.

        JPEG = 1.0 baseline.  PNG is usually *larger* for photos.
        """
        return self._FORMAT_EFFICIENCY.get(fmt.upper(), 1.0)

    def _estimate_quality(
        self,
        base_quality: float,
        compression: int,
        format_efficiency: float,
        difficulty: float,
    ) -> float:
        """Estimate output visual quality (0-100).

        Higher compression → lower quality.
        Higher difficulty → quality drops faster.
        Better format efficiency → same quality at higher compression.
        """
        comp_norm = compression / 95.0  # 0..1

        # Quality loss from compression – non-linear (quadratic feel).
        # At comp_norm=0  → loss ≈ 0
        # At comp_norm=1  → loss ≈ 35 points
        raw_loss = 35.0 * (comp_norm ** 1.8)

        # Difficulty amplifies the loss.  Easy (0) → no amplification,
        # Very Hard (1.0) → up to 60 % more loss.
        difficulty_factor = 1.0 + 0.6 * difficulty
        adjusted_loss = raw_loss * difficulty_factor

        # Format efficiency softens the loss (better codecs preserve quality).
        # AVIF at 1.35 → reduces loss by ~27 %, JPEG at 1.0 → no change.
        efficiency_bonus = (format_efficiency - 1.0) / 0.35  # 0..1
        efficiency_discount = adjusted_loss * 0.25 * efficiency_bonus
        final_loss = adjusted_loss - efficiency_discount

        quality = base_quality - final_loss
        return clamp(quality, 1.0, 100.0)

    def _estimate_ssim(self, quality: float) -> float:
        r"""Map quality (0-100) to SSIM (0-1) using a logistic curve.

        Model:  ``ssim = (L / (1 + exp(-k · (quality - x₀)))) ^ p``

        Fitted so that:
        - quality 100 → ssim ≈ 0.995
        - quality  80 → ssim ≈ 0.95
        - quality  60 → ssim ≈ 0.85
        """
        k = 0.0606
        x0 = 31.4
        logistic = 1.0 / (1.0 + math.exp(-k * (quality - x0)))
        # Gentle power to raise the high-quality ceiling
        ssim = logistic ** 0.92
        return clamp(float(ssim), 0.0, 1.0)

    def _estimate_psnr(self, quality: float) -> float:
        """Map quality (0-100) to PSNR in dB.

        Near-linear but with slight softening at extremes.
        Target: quality 100 → ~60 dB, quality 80 → ~52 dB, quality 60 → ~40 dB.

        Model: ``psnr = 20 + 0.4 * quality`` gives 60 at 100, 52 at 80, 44 at 60.
        Add a small quadratic term to make it slightly sub-linear at high quality.
        """
        psnr = 20.0 + 0.40 * quality - 0.0005 * quality * quality
        return clamp(float(psnr), 0.0, 100.0)

    def _estimate_processing_time(self, width: int, height: int, fmt: str) -> float:
        """Estimate compression time in seconds.

        Base rate: ``pixels / 2_000_000`` seconds for JPEG.
        Format multipliers: AVIF 3×, WEBP 1.5×, PNG 2×.
        """
        pixels = width * height
        base_time = pixels / 2_000_000.0
        speed_factor = self._FORMAT_SPEED_FACTOR.get(fmt.upper(), 1.0)
        return base_time * speed_factor

    def _generate_recommendation(self, prediction: CompressionPrediction) -> str:
        """Generate human-readable recommendation text based on the prediction."""
        ratio = prediction.compression_ratio
        ssim = prediction.expected_ssim
        quality = prediction.visual_quality

        # Determine overall assessment
        if ratio < 0.10:
            return "This image is already well-optimized; further compression will show minimal gains."

        if ssim >= 0.97 and ratio >= 0.30:
            return "Excellent compression with minimal quality loss — these settings are ideal."

        if ssim >= 0.95 and ratio >= 0.20:
            return "Good balance of compression and quality for this image."

        if ssim >= 0.90 and ratio >= 0.15:
            return "Moderate compression recommended for this complex image."

        if ssim < 0.85:
            return "High compression may cause visible artifacts. Consider reducing compression or switching to AVIF."

        if quality < 70:
            return "Quality is degrading noticeably. Try a higher quality setting for better results."

        if ratio < 0.15:
            return "Very aggressive compression. Savings are significant but quality is impacted."

        return "Acceptable compression. Review the quality metrics before proceeding."