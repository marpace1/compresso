"""Image compressor for Compresso (compresso).

Provides the actual compression engine that routes to format-specific
backends (JPEG / PNG / WebP / AVIF) and optionally leverages external
tools like MozJPEG and oxipng when available on the system.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import pillow_avif
import pillow_heif
from PIL import Image

from models import ImageInfo, CompressionSettings, CompressionResult
from utils.helpers import get_output_extension, generate_output_path
from utils.logger import setup_logger


class ImageCompressor:
    """Compress images using various backends.

    Supports JPEG (with optional MozJPEG), PNG (with optional oxipng),
    WebP (via PIL), and AVIF (via pillow-avif-plugin).
    """

    def __init__(self) -> None:
        self.logger = setup_logger("compressor")
        # Register HEIF and AVIF plugins so PIL can natively open these.
        try:
            pillow_heif.register_heif_opener()
        except Exception:
            pass
        try:
            pillow_avif.register_avif_opener()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(
        self,
        image_info: ImageInfo,
        settings: CompressionSettings,
        output_dir: Path | None = None,
    ) -> CompressionResult:
        """Main compression method.

        Routes to the appropriate format-specific compressor, measures
        wall-clock time, and returns a fully populated *CompressionResult*.
        """
        fmt = settings.output_format.upper()

        # Handle "ORIGINAL" passthrough
        if fmt == "ORIGINAL":
            fmt = image_info.format.upper()

        start_time = time.perf_counter()

        try:
            # Load the source image
            image = Image.open(image_info.filepath)

            # Strip metadata if requested (EXIF, ICC profile, etc.)
            if settings.remove_metadata:
                # Preserve mode info but drop all metadata
                image = self._strip_metadata(image)

            # Convert to RGB if saving to a format that doesn't support alpha
            if fmt == "JPEG" and image.mode in ("RGBA", "LA", "P", "PA"):
                # Composite over white background
                bg = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                if image.mode in ("RGBA", "LA", "PA"):
                    bg.paste(image, mask=image.split()[-1])  # alpha channel
                    image = bg
                else:
                    image = image.convert("RGB")

            # Generate output path
            output_path = generate_output_path(image_info.filepath, fmt, output_dir)

            # Route to format-specific compressor
            if fmt == "JPEG":
                out_path, out_size = self._compress_jpeg(image, settings, output_path)
            elif fmt == "PNG":
                out_path, out_size = self._compress_png(image, settings, output_path)
            elif fmt == "WEBP":
                out_path, out_size = self._compress_webp(image, settings, output_path)
            elif fmt == "AVIF":
                out_path, out_size = self._compress_avif(image, settings, output_path)
            else:
                # Fallback: save as-is via PIL
                out_path, out_size = self._compress_jpeg(image, settings, output_path)

            elapsed = time.perf_counter() - start_time
            original_size = image_info.file_size
            ratio = 1.0 - (out_size / original_size) if original_size > 0 else 0.0

            return CompressionResult(
                success=True,
                output_path=out_path,
                output_size=out_size,
                original_size=original_size,
                compression_ratio=round(ratio, 4),
                space_saved=max(0, original_size - out_size),
                processing_time=round(elapsed, 4),
                format_used=fmt,
                quality_used=settings.quality_percent,
                metadata_removed=0,  # metadata size not available without analysis
            )

        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            self.logger.exception("Compression failed for %s", image_info.filepath)
            return CompressionResult(
                success=False,
                original_size=image_info.file_size,
                processing_time=round(elapsed, 4),
                format_used=fmt,
                quality_used=settings.quality_percent,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Format-specific compressors
    # ------------------------------------------------------------------

    def _compress_jpeg(
        self,
        image: Image.Image,
        settings: CompressionSettings,
        output_path: Path,
    ) -> tuple[Path, int]:
        """Compress as JPEG.

        Quality mapping: user-facing ``quality_percent`` (80-100) and
        ``compression_percent`` (0-95) → PIL quality (1-95).

        Uses ``optimize=True`` and ``progressive=True``.
        Tries MozJPEG if available, falls back to PIL's libjpeg.
        """
        pil_quality = self._map_quality_to_pil(
            settings.quality_percent, settings.compression_percent
        )

        # Ensure RGB mode for JPEG
        if image.mode != "RGB":
            image = image.convert("RGB")

        # First save a temp file so we can try MozJPEG on it
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            image.save(
                tmp_path,
                format="JPEG",
                quality=pil_quality,
                optimize=True,
                progressive=True,
            )

            # Try external MozJPEG encoder
            success, size = self._try_mozjpeg(tmp_path, output_path, pil_quality)
            if success:
                return output_path, size

            # MozJPEG not available or failed – copy temp to output
            shutil.copy2(tmp_path, output_path)
            return output_path, output_path.stat().st_size
        finally:
            tmp_path.unlink(missing_ok=True)

    def _compress_png(
        self,
        image: Image.Image,
        settings: CompressionSettings,
        output_path: Path,
    ) -> tuple[Path, int]:
        """Compress as PNG.

        Uses PIL ``optimize=True``.  Tries ``oxipng`` if available for
        better lossless compression, falls back to PIL.
        """
        # PNG doesn't use quality in the same way – compression level
        # maps from compression_percent.
        # PIL's compress_level: 0 (fastest) to 9 (smallest).
        compress_level = min(9, max(0, int(settings.compression_percent / 95.0 * 9)))

        # Save via PIL first
        image.save(
            output_path,
            format="PNG",
            optimize=True,
            compress_level=compress_level,
        )

        # Try external oxipng optimizer
        success, size = self._try_oxipng(output_path, output_path, level=compress_level)
        if success:
            return output_path, size

        return output_path, output_path.stat().st_size

    def _compress_webp(
        self,
        image: Image.Image,
        settings: CompressionSettings,
        output_path: Path,
    ) -> tuple[Path, int]:
        """Compress as WebP.

        Uses PIL's WebP encoder with quality mapping.
        """
        pil_quality = self._map_quality_to_pil(
            settings.quality_percent, settings.compression_percent
        )

        # WebP supports lossy + lossless; we use lossy via quality param.
        # method: 0-6, higher = slower but better compression
        method = min(6, max(0, int(settings.compression_percent / 95.0 * 6)))

        image.save(
            output_path,
            format="WEBP",
            quality=pil_quality,
            method=method,
        )

        return output_path, output_path.stat().st_size

    def _compress_avif(
        self,
        image: Image.Image,
        settings: CompressionSettings,
        output_path: Path,
    ) -> tuple[Path, int]:
        """Compress as AVIF using pillow-avif-plugin.

        Quality mapping: ``quality_percent`` → AVIF quality.
        Uses ``speed=8`` (faster encoding) for responsive UX.
        """
        # AVIF quality range is 0-100 in pillow-avif-plugin.
        # We map our user-facing quality directly, but deflate it by
        # compression_percent.
        avif_quality = self._map_quality_to_pil(
            settings.quality_percent, settings.compression_percent
        )

        # Ensure compatible mode for AVIF
        if image.mode in ("RGBA", "LA"):
            pass  # AVIF supports alpha
        elif image.mode != "RGB":
            image = image.convert("RGB")

        image.save(
            output_path,
            format="AVIF",
            quality=avif_quality,
            speed=8,  # 0=slowest/best, 10=fastest
        )

        return output_path, output_path.stat().st_size

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_metadata(image: Image.Image) -> Image.Image:
        """Return a copy of *image* with all metadata stripped."""
        data = list(image.getdata())
        out = Image.new(image.mode, image.size)
        out.putdata(data)
        return out

    @staticmethod
    def _map_quality_to_pil(quality_percent: int, compression_percent: int) -> int:
        """Map user-facing quality (80-100) and compression (0-95) to PIL quality (1-95).

        Formula: ``pil_quality = max(1, quality_percent - compression_percent * 0.5)``
        Clamped to [1, 95].

        Examples:
        - quality=100, compression=0  → 100 → clamped to 95
        - quality=90,  compression=50 → 65
        - quality=80,  compression=90 → 35
        """
        pil_quality = int(quality_percent - compression_percent * 0.5)
        return max(1, min(95, pil_quality))

    def _try_mozjpeg(
        self, input_path: Path, output_path: Path, quality: int
    ) -> tuple[bool, int]:
        """Try to compress with MozJPEG via subprocess.

        Checks for ``cjpeg`` (MozJPEG CLI) on the system PATH.
        Returns ``(success, file_size)`` — on failure ``file_size`` is 0.
        """
        # MozJPEG is typically exposed as 'cjpeg'
        cjpeg_path = shutil.which("cjpeg")
        if cjpeg_path is None:
            return False, 0

        try:
            result = subprocess.run(
                [
                    cjpeg_path,
                    "-quality", str(quality),
                    "-optimize",
                    "-progressive",
                    "-outfile", str(output_path),
                    str(input_path),
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and output_path.exists():
                return True, output_path.stat().st_size
            return False, 0
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return False, 0

    def _try_oxipng(
        self, input_path: Path, output_path: Path, level: int = 3
    ) -> tuple[bool, int]:
        """Try to optimise with ``oxipng`` via subprocess.

        Returns ``(success, file_size)`` — on failure ``file_size`` is 0.
        """
        oxipng_path = shutil.which("oxipng")
        if oxipng_path is None:
            return False, 0

        try:
            # oxipng optimisation levels: 0-6 (max).  Map our 0-9 into 0-6.
            oxipng_level = min(6, max(0, int(level / 9.0 * 6)))
            result = subprocess.run(
                [
                    oxipng_path,
                    "-o", str(oxipng_level),
                    "--strip", "safe",  # strip non-critical metadata
                    "-i", "0",  # no interlacing by default
                    "--out", str(output_path),
                    str(input_path),
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode == 0 and output_path.exists():
                return True, output_path.stat().st_size
            return False, 0
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return False, 0

    # ------------------------------------------------------------------
    # Target-size compression (binary search)
    # ------------------------------------------------------------------

    def compress_to_target_size(
        self,
        image_info: ImageInfo,
        target_bytes: int,
        fmt: str = "JPEG",
        remove_metadata: bool = False,
        max_iterations: int = 15,
    ) -> CompressionResult:
        """Binary-search over quality / parameters to hit *target_bytes*.

        Works for every supported image type:
        - **JPEG / WEBP / AVIF** — binary-search over quality (1-95).
        - **PNG** — progressive strategy: 1) try PNG with palette/depth
          reduction + compression levels 0-9, 2) if still too large, convert
          to WEBP and binary-search quality, 3) last resort, downscale.
        - **BMP / TIFF / GIF** — convert to lossy WEBP and binary-search
          quality to reach the target.

        Returns the closest match after *max_iterations* rounds.
        """
        if fmt == "ORIGINAL":
            fmt = image_info.format.upper()

        start_time = time.perf_counter()

        try:
            image = Image.open(image_info.filepath)
            if remove_metadata:
                image = self._strip_metadata(image)

            # Pre-process for RGB formats
            needs_rgb_conversion = False
            if fmt in ("JPEG",) and image.mode in ("RGBA", "LA", "P", "PA"):
                bg = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                if image.mode in ("RGBA", "LA", "PA"):
                    bg.paste(image, mask=image.split()[-1])
                    image = bg
                    needs_rgb_conversion = False
                else:
                    image = image.convert("RGB")
            elif image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                image = image.convert("RGB")

            output_path = generate_output_path(image_info.filepath, fmt)
            original_size = image_info.file_size

            # ---------- Lossy formats (JPEG, WEBP, AVIF) ----------
            if fmt in ("JPEG", "WEBP", "AVIF"):
                result = self._target_lossy(
                    image, fmt, output_path, target_bytes,
                    max_iterations, original_size, start_time,
                )
                self._cleanup_target_temps(output_path)
                return result

            # ---------- PNG (lossless with fallback) ----------
            if fmt == "PNG":
                result = self._target_png(
                    image, output_path, target_bytes,
                    max_iterations, original_size, start_time,
                )
                self._cleanup_target_temps(output_path)
                return result

            # ---------- Other formats (BMP, TIFF, GIF, etc.) ----------
            # Convert to WEBP for lossy size targeting
            result = self._target_fallback(
                image, fmt, output_path, target_bytes,
                original_size, start_time,
            )
            self._cleanup_target_temps(output_path)
            return result

        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            self.logger.exception("Target-size compression failed for %s", image_info.filepath)
            return CompressionResult(
                success=False,
                original_size=image_info.file_size,
                processing_time=round(elapsed, 4),
                format_used=fmt,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Target-size helpers
    # ------------------------------------------------------------------

    def _target_lossy(
        self, image, fmt, output_path, target_bytes,
        max_iterations, original_size, start_time,
    ) -> CompressionResult:
        """Binary-search quality for lossy formats (JPEG, WEBP, AVIF)."""
        # Ensure RGB for lossy search
        search_image = image
        if search_image.mode not in ("RGB", "RGBA"):
            search_image = search_image.convert("RGB")

        lo, hi = 1, 95
        best_path: Path | None = None
        best_size = 0
        best_quality = 50
        best_diff = float("inf")

        for _ in range(max_iterations):
            mid = (lo + hi) // 2
            try:
                if fmt == "JPEG":
                    tmp = output_path.with_name(f"_target_q{mid}.jpg")
                    rgb = search_image.convert("RGB") if search_image.mode != "RGB" else search_image
                    rgb.save(tmp, format="JPEG", quality=mid,
                             optimize=True, progressive=True)
                elif fmt == "WEBP":
                    tmp = output_path.with_name(f"_target_q{mid}.webp")
                    search_image.save(tmp, format="WEBP", quality=mid, method=4)
                elif fmt == "AVIF":
                    tmp = output_path.with_name(f"_target_q{mid}.avif")
                    search_image.save(tmp, format="AVIF", quality=mid, speed=8)
                else:
                    break

                size = tmp.stat().st_size
                diff = abs(size - target_bytes)

                if diff < best_diff:
                    best_diff = diff
                    best_path = tmp
                    best_size = size
                    best_quality = mid

                if size < target_bytes:
                    lo = mid + 1
                else:
                    hi = mid - 1

                # Close enough (within 2% of target or under 5KB off)
                if diff / max(target_bytes, 1) < 0.02 or diff < 5120:
                    break

                if lo > hi:
                    break
            except Exception:
                hi = mid - 1
                continue

        if best_path is None:
            raise RuntimeError("All quality attempts failed for lossy target")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(best_path), str(output_path))

        elapsed = time.perf_counter() - start_time
        ratio = 1.0 - (best_size / original_size) if original_size > 0 else 0.0
        return CompressionResult(
            success=True,
            output_path=output_path,
            output_size=best_size,
            original_size=original_size,
            compression_ratio=round(ratio, 4),
            space_saved=max(0, original_size - best_size),
            processing_time=round(elapsed, 4),
            format_used=fmt,
            quality_used=best_quality,
            metadata_removed=0,
        )

    def _target_png(
        self, image, output_path, target_bytes,
        max_iterations, original_size, start_time,
    ) -> CompressionResult:
        """Target-size for PNG: try palette/depth reduction, then fall back to WEBP."""
        # Strategy 1: Try PNG with various compression levels and modes
        best_path: Path | None = None
        best_size = 0
        best_diff = float("inf")

        # Try different PNG modes
        png_variants = []
        try:
            # Palette mode (best for images with few colors)
            pal = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            png_variants.append(("P", pal))
        except Exception:
            pass

        try:
            # Reduced color (mode "P" with fewer colors)
            pal128 = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
            png_variants.append(("P128", pal128))
        except Exception:
            pass

        try:
            pal64 = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=64)
            png_variants.append(("P64", pal64))
        except Exception:
            pass

        # Original mode
        png_variants.append(("orig", image))

        # Also try L (grayscale) if applicable
        if image.mode in ("RGB", "RGBA"):
            try:
                gray = image.convert("L")
                png_variants.append(("L", gray))
            except Exception:
                pass

        for label, img in png_variants:
            for level in [9, 7, 5, 3, 0]:
                try:
                    tmp = output_path.with_name(f"_target_{label}_l{level}.png")
                    img.save(tmp, format="PNG", optimize=True, compress_level=level)
                    size = tmp.stat().st_size
                    diff = abs(size - target_bytes)
                    if diff < best_diff:
                        best_diff = diff
                        best_path = tmp
                        best_size = size
                    if size <= target_bytes:
                        break  # Good enough for this variant
                except Exception:
                    continue

        # If best PNG is within 5% of target, use it
        if best_path and best_diff / max(target_bytes, 1) < 0.05:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(best_path), str(output_path))
            elapsed = time.perf_counter() - start_time
            ratio = 1.0 - (best_size / original_size) if original_size > 0 else 0.0
            return CompressionResult(
                success=True,
                output_path=output_path,
                output_size=best_size,
                original_size=original_size,
                compression_ratio=round(ratio, 4),
                space_saved=max(0, original_size - best_size),
                processing_time=round(elapsed, 4),
                format_used="PNG",
                quality_used=0,
                metadata_removed=0,
            )

        # Strategy 2: PNG can't reach target losslessly — convert to WEBP and binary-search
        # Use the output format as WEBP but keep .png extension if user wants, or switch to .webp
        webp_output = output_path.with_suffix(".webp")
        search_image = image.convert("RGB") if image.mode != "RGB" else image

        lo, hi = 1, 95
        webp_best_path: Path | None = None
        webp_best_size = 0
        webp_best_quality = 50
        webp_best_diff = float("inf")

        for _ in range(max_iterations):
            mid = (lo + hi) // 2
            try:
                tmp = webp_output.with_name(f"_target_wq{mid}.webp")
                search_image.save(tmp, format="WEBP", quality=mid, method=4)
                size = tmp.stat().st_size
                diff = abs(size - target_bytes)

                if diff < webp_best_diff:
                    webp_best_diff = diff
                    webp_best_path = tmp
                    webp_best_size = size
                    webp_best_quality = mid

                if size < target_bytes:
                    lo = mid + 1
                else:
                    hi = mid - 1

                if diff / max(target_bytes, 1) < 0.02 or diff < 5120:
                    break
                if lo > hi:
                    break
            except Exception:
                hi = mid - 1
                continue

        if webp_best_path is None:
            # Fall back to the best PNG we found, even if not ideal
            if best_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(best_path), str(output_path))
                elapsed = time.perf_counter() - start_time
                ratio = 1.0 - (best_size / original_size) if original_size > 0 else 0.0
                return CompressionResult(
                    success=True,
                    output_path=output_path,
                    output_size=best_size,
                    original_size=original_size,
                    compression_ratio=round(ratio, 4),
                    space_saved=max(0, original_size - best_size),
                    processing_time=round(elapsed, 4),
                    format_used="PNG",
                    quality_used=0,
                    metadata_removed=0,
                )
            raise RuntimeError("Could not compress to target size")

        # Use WEBP as output since PNG can't reach the target losslessly
        webp_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(webp_best_path), str(webp_output))

        elapsed = time.perf_counter() - start_time
        ratio = 1.0 - (webp_best_size / original_size) if original_size > 0 else 0.0
        return CompressionResult(
            success=True,
            output_path=webp_output,
            output_size=webp_best_size,
            original_size=original_size,
            compression_ratio=round(ratio, 4),
            space_saved=max(0, original_size - webp_best_size),
            processing_time=round(elapsed, 4),
            format_used="WEBP",
            quality_used=webp_best_quality,
            metadata_removed=0,
        )

    def _target_fallback(
        self, image, fmt, output_path, target_bytes,
        original_size, start_time,
    ) -> CompressionResult:
        """Target-size for BMP, TIFF, GIF etc.: convert to WEBP and binary-search."""
        search_image = image.convert("RGB") if image.mode != "RGB" else image
        webp_output = output_path.with_suffix(".webp")

        lo, hi = 1, 95
        best_path: Path | None = None
        best_size = 0
        best_quality = 50
        best_diff = float("inf")

        for _ in range(15):
            mid = (lo + hi) // 2
            try:
                tmp = webp_output.with_name(f"_target_fq{mid}.webp")
                search_image.save(tmp, format="WEBP", quality=mid, method=4)
                size = tmp.stat().st_size
                diff = abs(size - target_bytes)

                if diff < best_diff:
                    best_diff = diff
                    best_path = tmp
                    best_size = size
                    best_quality = mid

                if size < target_bytes:
                    lo = mid + 1
                else:
                    hi = mid - 1

                if diff / max(target_bytes, 1) < 0.02 or diff < 5120:
                    break
                if lo > hi:
                    break
            except Exception:
                hi = mid - 1
                continue

        if best_path is None:
            raise RuntimeError(f"Could not compress {fmt} to target size")

        webp_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(best_path), str(webp_output))

        elapsed = time.perf_counter() - start_time
        ratio = 1.0 - (best_size / original_size) if original_size > 0 else 0.0
        return CompressionResult(
            success=True,
            output_path=webp_output,
            output_size=best_size,
            original_size=original_size,
            compression_ratio=round(ratio, 4),
            space_saved=max(0, original_size - best_size),
            processing_time=round(elapsed, 4),
            format_used="WEBP",
            quality_used=best_quality,
            metadata_removed=0,
        )

    @staticmethod
    def _cleanup_target_temps(output_path: Path):
        """Remove all temporary files created during target-size search."""
        for tmp in output_path.parent.glob("_target_*"):
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
