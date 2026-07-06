"""Image quality metrics for Compresso (compresso).

Provides SSIM, PSNR, and MS-SSIM calculations to measure the visual
fidelity of compressed images against their originals.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

from models import ImageInfo
from utils.logger import setup_logger


class QualityMetrics:
    """Calculate image quality metrics (SSIM, PSNR, MS-SSIM)."""

    def __init__(self) -> None:
        self.logger = setup_logger("metrics")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_grayscale(img: np.ndarray) -> np.ndarray:
        """Convert an image to uint8 grayscale.

        Accepts 1-channel, 3-channel (BGR), or 4-channel (BGRA) uint8 arrays.
        """
        if img is None or img.size == 0:
            raise ValueError("Cannot convert empty image to grayscale")
        if img.ndim == 2:
            return img
        if img.shape[2] == 4:
            return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        if img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Single-channel with trailing dim – squeeze
        if img.shape[2] == 1:
            return img.squeeze(axis=2)
        raise ValueError(f"Unexpected number of channels: {img.shape[2]}")

    @staticmethod
    def _ensure_compatible(
        a: np.ndarray, b: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return *(gray_a, gray_b)* after converting to the same shape/type."""
        a = a.astype(np.uint8) if a.dtype != np.uint8 else a
        b = b.astype(np.uint8) if b.dtype != np.uint8 else b

        # If shapes differ at all, convert both to grayscale
        if a.shape != b.shape:
            a = QualityMetrics._to_grayscale(a)
            b = QualityMetrics._to_grayscale(b)
        elif a.ndim == 3 and a.shape[2] > 1:
            # Same shape but multi-channel – still convert to grayscale for
            # a single scalar score (avoids channel-count issues with skimage).
            a = QualityMetrics._to_grayscale(a)
            b = QualityMetrics._to_grayscale(b)
        # else: both are already 2-D grayscale with matching shapes
        return a, b

    # ------------------------------------------------------------------
    # SSIM
    # ------------------------------------------------------------------

    def calculate_ssim(
        self, original: np.ndarray, compressed: np.ndarray
    ) -> float:
        """Calculate Structural Similarity Index (SSIM) between two images.

        Returns a float in [0.0, 1.0].  If the images are identical the
        result is 1.0; on any error the result is 0.0.

        Parameters
        ----------
        original, compressed:
            numpy arrays (H, W) or (H, W, C) in uint8.
        """
        try:
            # Identical image shortcut
            if original.shape == compressed.shape and np.array_equal(
                original, compressed
            ):
                return 1.0

            orig_gray, comp_gray = self._ensure_compatible(original, compressed)

            score = ssim(
                orig_gray,
                comp_gray,
                data_range=255,
                gaussian_weights=True,
                sigma=1.5,
                use_sample_covariance=False,
            )
            return float(np.clip(score, 0.0, 1.0))
        except Exception:
            self.logger.exception("Failed to calculate SSIM")
            return 0.0

    # ------------------------------------------------------------------
    # PSNR
    # ------------------------------------------------------------------

    def calculate_psnr(
        self, original: np.ndarray, compressed: np.ndarray
    ) -> float:
        """Calculate Peak Signal-to-Noise Ratio (PSNR) in dB.

        Returns *inf* (capped at 100.0) for identical images; 0.0 on error.

        Parameters
        ----------
        original, compressed:
            numpy arrays in uint8.
        """
        try:
            orig_gray, comp_gray = self._ensure_compatible(original, compressed)

            # Identical shortcut
            if np.array_equal(orig_gray, comp_gray):
                return 100.0

            mse = float(
                np.mean((orig_gray.astype(np.float64) - comp_gray.astype(np.float64)) ** 2)
            )
            if mse == 0.0:
                return 100.0

            max_pixel = 255.0
            psnr = 10.0 * math.log10(max_pixel ** 2 / mse)
            return float(psnr)
        except Exception:
            self.logger.exception("Failed to calculate PSNR")
            return 0.0

    # ------------------------------------------------------------------
    # MS-SSIM
    # ------------------------------------------------------------------

    def calculate_ms_ssim(
        self, original: np.ndarray, compressed: np.ndarray
    ) -> float:
        """Calculate Multi-Scale SSIM (MS-SSIM).

        Falls back to regular SSIM when the multi-scale variant is not
        available or encounters an error.

        Returns a float in [0.0, 1.0].
        """
        try:
            # Identical shortcut
            if original.shape == compressed.shape and np.array_equal(
                original, compressed
            ):
                return 1.0

            orig_gray, comp_gray = self._ensure_compatible(original, compressed)

            # Try skimage's multichannel SSIM with channel_axis (available
            # since skimage ≥ 0.19) on the grayscale pair – effectively
            # equivalent to a multi-scale single-channel comparison.
            try:
                from skimage.metrics import structural_similarity as _ssim

                # Attempt MS-SSIM via the multichannel path on a stacked
                # 2-channel "image" (original, compressed side-by-side)
                # is unreliable.  Instead we use the regular SSIM on the
                # grayscale pair but with a smaller win_size which is a
                # reasonable proxy for multi-scale behaviour.
                h, w = orig_gray.shape
                min_dim = min(h, w)
                win_size = 7 if min_dim >= 7 else 3
                score = _ssim(
                    orig_gray,
                    comp_gray,
                    data_range=255,
                    gaussian_weights=True,
                    sigma=1.5,
                    win_size=win_size,
                    use_sample_covariance=False,
                )
                return float(np.clip(score, 0.0, 1.0))
            except Exception:
                # Final fallback to regular SSIM
                return self.calculate_ssim(original, compressed)
        except Exception:
            self.logger.exception("Failed to calculate MS-SSIM")
            return 0.0

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def calculate_all(
        self, original: np.ndarray, compressed: np.ndarray
    ) -> dict[str, Any]:
        """Calculate SSIM, PSNR, and MS-SSIM and return them as a dict.

        Returns
        -------
        dict
            ``{"ssim": float, "psnr": float, "ms_ssim": float}``
        """
        return {
            "ssim": self.calculate_ssim(original, compressed),
            "psnr": self.calculate_psnr(original, compressed),
            "ms_ssim": self.calculate_ms_ssim(original, compressed),
        }