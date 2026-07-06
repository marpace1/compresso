"""Data models for Compresso (compresso).

Comprehensive dataclass-based models for representing image information,
analysis results, compression predictions, results, settings, and batch items.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
from typing import Any, ClassVar


@dataclass(slots=True)
class ImageInfo:
    """Complete metadata and properties of a loaded image."""

    filepath: Path
    filename: str
    format: str
    width: int
    height: int
    bit_depth: int
    has_alpha: bool
    file_size: int
    color_mode: str
    num_channels: int

    @property
    def resolution(self) -> tuple[int, int]:
        """Image dimensions as (width, height)."""
        return (self.width, self.height)

    @property
    def aspect_ratio(self) -> float:
        """Width / height ratio."""
        if self.height == 0:
            return 0.0
        return self.width / self.height

    @property
    def megapixels(self) -> float:
        """Total pixel count in megapixels."""
        return (self.width * self.height) / 1_000_000.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["filepath"] = str(self.filepath)
        d["resolution"] = self.resolution
        d["aspect_ratio"] = self.aspect_ratio
        d["megapixels"] = round(self.megapixels, 2)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImageInfo:
        data = data.copy()
        if isinstance(data.get("filepath"), str):
            data["filepath"] = Path(data["filepath"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(slots=True)
class AnalysisResult:
    """Output of the image analysis pipeline."""

    noise_level: float = 0.0
    texture_complexity: float = 0.0
    edge_density: float = 0.0
    sharpness: float = 0.0
    entropy: float = 0.0
    color_distribution_score: float = 0.0
    metadata_size: int = 0
    is_already_compressed: bool = False
    compression_difficulty: float = 0.0
    difficulty_label: str = "Easy"
    estimated_compression_potential: float = 0.0
    recommended_format: str = "JPEG"
    recommended_quality: int = 85
    recommended_compression: int = 50

    def __post_init__(self) -> None:
        # Auto-derive difficulty_label from compression_difficulty
        if self.compression_difficulty >= 0.75:
            self.difficulty_label = "Very Hard"
        elif self.compression_difficulty >= 0.50:
            self.difficulty_label = "Hard"
        elif self.compression_difficulty >= 0.25:
            self.difficulty_label = "Medium"
        else:
            self.difficulty_label = "Easy"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisResult:
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


@dataclass(slots=True)
class CompressionPrediction:
    """Predicted outcomes before actual compression runs."""

    estimated_output_size: int = 0
    compression_ratio: float = 0.0
    visual_quality: float = 0.0
    expected_ssim: float = 0.0
    expected_psnr: float = 0.0
    estimated_time: float = 0.0
    recommendation_text: str = ""

    @property
    def estimated_savings(self) -> int:
        """Predicted bytes saved (requires external original size context)."""
        return 0  # placeholder; caller computes as original - estimated_output_size

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompressionPrediction:
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


@dataclass(slots=True)
class CompressionResult:
    """Actual results after a compression operation completes."""

    success: bool = False
    output_path: Path | None = None
    output_size: int = 0
    original_size: int = 0
    compression_ratio: float = 0.0
    space_saved: int = 0
    ssim: float | None = None
    psnr: float | None = None
    processing_time: float = 0.0
    format_used: str = ""
    quality_used: int = 85
    metadata_removed: int = 0
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["output_path"] = str(self.output_path) if self.output_path is not None else None
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompressionResult:
        data = data.copy()
        if isinstance(data.get("output_path"), str):
            data["output_path"] = Path(data["output_path"])
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


@dataclass(slots=True)
class CompressionSettings:
    """User-configurable compression parameters."""

    compression_percent: int = 50
    quality_percent: int = 85
    output_format: str = "JPEG"
    remove_metadata: bool = False
    preset: str = "balanced"
    smart_mode: bool = True
    target_size_bytes: int = 0  # 0 = disabled; >0 = binary-search to hit this size

    PRESETS: ClassVar = {  # type: ignore[type-arg]
        "max_quality": {"compression_percent": 10, "quality_percent": 98, "output_format": "PNG", "remove_metadata": True, "smart_mode": True},
        "balanced": {"compression_percent": 50, "quality_percent": 85, "output_format": "JPEG", "remove_metadata": True, "smart_mode": True},
        "max_compression": {"compression_percent": 90, "quality_percent": 60, "output_format": "WEBP", "remove_metadata": True, "smart_mode": True},
        "archive": {"compression_percent": 70, "quality_percent": 75, "output_format": "JPEG", "remove_metadata": True, "smart_mode": False},
        "custom": {},  # user-defined, no overrides
    }
    VALID_PRESETS: ClassVar = frozenset(PRESETS.keys())  # type: ignore[type-arg]
    VALID_FORMATS: ClassVar = frozenset({"JPEG", "PNG", "WEBP", "AVIF", "ORIGINAL"})  # type: ignore[type-arg]

    def __post_init__(self) -> None:
        """Clamp values to valid ranges and apply preset defaults."""
        self.compression_percent = max(0, min(95, self.compression_percent))
        self.quality_percent = max(1, min(100, self.quality_percent))
        if self.preset not in self.VALID_PRESETS:
            self.preset = "balanced"
        if self.output_format not in self.VALID_FORMATS:
            self.output_format = "JPEG"

    def apply_preset(self, preset_name: str | None = None) -> None:
        """Apply a named preset, overriding current values."""
        name = preset_name or self.preset
        if name not in self.PRESETS:
            return
        overrides = self.PRESETS[name]
        for key, value in overrides.items():
            setattr(self, key, value)
        self.preset = name

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompressionSettings:
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


@dataclass(slots=True)
class BatchItem:
    """Represents a single item in a batch compression queue."""

    filepath: Path
    filename: str
    original_size: int = 0
    status: str = "pending"
    result: CompressionResult | None = None
    progress: float = 0.0

    VALID_STATUSES: ClassVar = frozenset({"pending", "processing", "done", "error"})  # type: ignore[type-arg]

    def __post_init__(self) -> None:
        if self.status not in self.VALID_STATUSES:
            self.status = "pending"
        self.progress = max(0.0, min(1.0, self.progress))

    @property
    def is_complete(self) -> bool:
        return self.status in ("done", "error")

    @property
    def space_saved(self) -> int:
        if self.result is not None and self.result.success:
            return self.result.space_saved
        return 0

    @property
    def compression_ratio(self) -> float:
        if self.result is not None and self.result.success:
            return self.result.compression_ratio
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "filepath": str(self.filepath),
            "filename": self.filename,
            "original_size": self.original_size,
            "status": self.status,
            "progress": self.progress,
        }
        d["result"] = self.result.to_dict() if self.result is not None else None
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchItem:
        data = data.copy()
        if isinstance(data.get("filepath"), str):
            data["filepath"] = Path(data["filepath"])
        if data.get("result") is not None and isinstance(data["result"], dict):
            data["result"] = CompressionResult.from_dict(data["result"])
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)