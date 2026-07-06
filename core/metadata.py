"""Image metadata handler for Compresso (compresso).

Provides utilities to inspect, estimate the size of, and strip image
metadata (EXIF, GPS, ICC profiles, thumbnails, etc.).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from models import ImageInfo
from utils.logger import setup_logger


class MetadataHandler:
    """Handle reading and stripping image metadata."""

    def __init__(self) -> None:
        self.logger = setup_logger("metadata")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_metadata_size(self, filepath: Path) -> int:
        """Estimate metadata size in bytes.

        Strategy: compare the on-disk file size to an in-memory
        re-encoding of just the pixel data (without any metadata) and
        return the difference as the metadata estimate.  Falls back to
        inspecting EXIF/XMP payloads when re-encoding is impractical.

        Parameters
        ----------
        filepath:
            Path to the image file.

        Returns
        -------
        int
            Estimated metadata size in bytes (≥ 0).
        """
        try:
            file_size = filepath.stat().st_size
            img = Image.open(filepath)
            w, h = img.size

            # Primary: use actual EXIF payload size
            exif_size = self._exif_payload_size(img)

            # Secondary: check for ICC profile
            icc_size = 0
            if "icc_profile" in (img.info or {}):
                icc_data = img.info["icc_profile"]
                icc_size = len(icc_data) if icc_data else 0

            # Tertiary: re-encode without metadata and compare
            try:
                buf = io.BytesIO()
                clean = Image.new(img.mode, img.size)
                clean.putdata(img.getdata())
                clean.save(buf, format=img.format or "PNG", optimize=False)
                reencoded_size = buf.tell()
                # Metadata ≈ file size minus clean re-encoded size
                heuristic_size = max(0, file_size - reencoded_size)
            except Exception:
                heuristic_size = 0

            # Return the most reasonable estimate
            return max(exif_size, icc_size, heuristic_size)

        except Exception:
            self.logger.exception("Failed to estimate metadata size for %s", filepath)
            return 0

    def get_metadata_info(self, filepath: Path) -> dict[str, Any]:
        """Extract metadata summary as a dict.

        Returns
        -------
        dict
            Keys: ``has_gps``, ``has_exif``, ``has_camera_info``,
            ``has_icc_profile``, ``has_thumbnail``, ``metadata_tags_count``.
        """
        result: dict[str, Any] = {
            "has_gps": False,
            "has_exif": False,
            "has_camera_info": False,
            "has_icc_profile": False,
            "has_thumbnail": False,
            "metadata_tags_count": 0,
        }

        try:
            img = Image.open(filepath)
            info = img.info or {}

            # EXIF
            exif = img.getexif()
            if exif and len(exif) > 0:
                result["has_exif"] = True
                result["metadata_tags_count"] += len(exif)

            # GPS
            gps_info = exif.get_ifd(0x8825) if exif else None  # GPSInfoIFD
            if gps_info and len(gps_info) > 0:
                result["has_gps"] = True

            # ICC profile
            if "icc_profile" in info:
                result["has_icc_profile"] = True

            # Thumbnail (embedded in EXIF)
            if exif:
                thumb = exif.get(0x0201)  # ExifTags.THUMBNAIL_OFFSET tag
                if thumb is not None:
                    result["has_thumbnail"] = True

            # Camera info (Make / Model tags)
            if exif:
                make = exif.get(0x010F)  # ExifTags.MAKE
                model = exif.get(0x0110)  # ExifTags.MODEL
                if make or model:
                    result["has_camera_info"] = True

            # Count additional info keys
            result["metadata_tags_count"] += len(info)

        except Exception:
            self.logger.exception("Failed to read metadata info for %s", filepath)

        return result

    def strip_metadata(
        self, image: Image.Image, filepath: Path
    ) -> tuple[Image.Image, int]:
        """Strip all metadata from an image.

        Creates a new :class:`PIL.Image.Image` with the same pixel data
        but **no** EXIF, GPS, ICC profile, or other metadata.

        Parameters
        ----------
        image:
            An open PIL image.
        filepath:
            Original file path (used to estimate bytes removed).

        Returns
        -------
        tuple[Image.Image, int]
            ``(clean_image, bytes_removed_estimate)``
        """
        bytes_before = self.get_metadata_size(filepath)

        try:
            # Create a fresh image with the same mode and pixels
            clean = Image.new(image.mode, image.size)
            clean.putdata(image.getdata())

            # Copy only the essential "transparency" info if needed
            # (so PNG alpha is preserved) but nothing else.
            if "transparency" in image.info:
                clean.info["transparency"] = image.info["transparency"]

            return clean, bytes_before

        except Exception:
            self.logger.exception("Failed to strip metadata for %s", filepath)
            return image, 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _exif_payload_size(img: Image.Image) -> int:
        """Return the byte-length of the EXIF data payload (if any)."""
        try:
            exif = img.getexif()
            if not exif or len(exif) == 0:
                return 0
            # Serialize EXIF to bytes and measure
            exif_bytes = exif.tobytes()
            return len(exif_bytes) if exif_bytes else 0
        except Exception:
            return 0