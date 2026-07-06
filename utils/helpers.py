"""Utility helpers for Compresso (compresso).

Commonly used formatting, path manipulation, math, and animation utilities.
"""

from __future__ import annotations

import math
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_INPUT_FORMATS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".heic", ".avif", ".webp",
})

SUPPORTED_OUTPUT_FORMATS: dict[str, str] = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "AVIF": ".avif",
}

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_file_size(size_bytes: int) -> str:
    """Return a human-readable file size string.

    Examples:
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(1_610_612)
        '1.54 MB'
    """
    if size_bytes < 0:
        return "0 B"

    units = ("B", "KB", "MB", "GB", "TB")
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"

    # Show up to 2 decimal places, stripping trailing zeros
    formatted = f"{size:.2f}".rstrip("0").rstrip(".")
    return f"{formatted} {units[unit_index]}"


def format_time(seconds: float) -> str:
    """Return a human-readable time duration string.

    Examples:
        >>> format_time(2.3)
        '2.30 sec'
        >>> format_time(72.5)
        '1.21 min'
    """
    if seconds < 0:
        return "0 sec"

    if seconds < 60:
        return f"{seconds:.2f} sec"

    minutes = seconds / 60.0
    if minutes < 60:
        return f"{minutes:.2f} min"

    hours = minutes / 60.0
    return f"{hours:.2f} hr"


# ---------------------------------------------------------------------------
# Path / format helpers
# ---------------------------------------------------------------------------


def get_file_extension(filepath: Path) -> str:
    """Return the uppercase file extension *without* the leading dot.

    >>> get_file_extension(Path("photo.jpg"))
    'JPG'
    >>> get_file_extension(Path("archive.tar.gz"))
    'GZ'
    """
    ext = filepath.suffix.lower()
    return ext.lstrip(".").upper() if ext else ""


def is_supported_input(filepath: Path) -> bool:
    """Check whether *filepath* has a supported input image extension."""
    return filepath.suffix.lower() in SUPPORTED_INPUT_FORMATS


def get_output_extension(fmt: str) -> str:
    """Map a format name (e.g. ``'JPEG'``) to its file extension (``'.jpg'``).

    Falls back to ``'.bin'`` for unknown formats.
    """
    return SUPPORTED_OUTPUT_FORMATS.get(fmt.upper(), ".bin")


def generate_output_path(
    original: Path,
    fmt: str,
    output_dir: Path | None = None,
) -> Path:
    """Build an output path for a compressed image.

    * If *output_dir* is given, the file is placed there.
    * The stem is preserved; the extension is derived from *fmt*.
    * If the target already exists, a numeric suffix is appended to avoid
      overwriting (e.g. ``photo_1.jpg``, ``photo_2.jpg``, ...).
    """
    ext = get_output_extension(fmt)
    stem = original.stem

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"{stem}{ext}"
    else:
        target = original.with_name(f"{stem}{ext}")

    # Avoid collisions
    if not target.exists():
        return target

    counter = 1
    while True:
        candidate = target.with_name(f"{stem}_{counter}{ext}")
        if not candidate.exists():
            return candidate
        counter += 1


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------


def calculate_aspect_ratio(w: int, h: int) -> float:
    """Return width / height, or ``0.0`` if *h* is zero."""
    if h == 0:
        return 0.0
    return w / h


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Constrain *value* to the closed interval ``[min_val, max_val]``."""
    return max(min_val, min(max_val, value))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* at parameter *t* ∈ [0, 1]."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Animation / easing
# ---------------------------------------------------------------------------


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out curve for smooth UI animations.

    >>> round(ease_out_cubic(0.0), 4)
    0.0
    >>> round(ease_out_cubic(1.0), 4)
    1.0
    >>> round(ease_out_cubic(0.5), 4)
    0.875
    """
    t = clamp(t, 0.0, 1.0)
    return 1.0 - math.pow(1.0 - t, 3)