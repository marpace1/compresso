from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel)
from PySide6.QtCore import Qt
from models import ImageInfo
from utils.helpers import format_file_size

class ImageInfoPanel(QFrame):
    """Panel displaying image metadata and analysis results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Title
        title = QLabel("Original Information")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        # Grid of info items
        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        self.grid.setColumnStretch(1, 1)
        layout.addLayout(self.grid)

        # Create label pairs
        self.labels = {}
        fields = [
            ("filename", "Filename"),
            ("resolution", "Resolution"),
            ("dimensions", "Dimensions"),
            ("file_size", "File Size"),
            ("format", "Format"),
            ("color_depth", "Color Depth"),
            ("color_mode", "Color Mode"),
            ("alpha", "Alpha Channel"),
            ("aspect_ratio", "Aspect Ratio"),
        ]

        for i, (key, label_text) in enumerate(fields):
            key_label = QLabel(label_text)
            key_label.setObjectName("mutedLabel")
            key_label.setMinimumWidth(90)

            value_label = QLabel("—")
            value_label.setObjectName("valueLabel")

            self.grid.addWidget(key_label, i, 0)
            self.grid.addWidget(value_label, i, 1)
            self.labels[key] = value_label

    def update_info(self, info: ImageInfo):
        """Update the panel with ImageInfo data."""
        self.labels["filename"].setText(info.filename)
        self.labels["resolution"].setText(f"{info.width} × {info.height}")
        self.labels["dimensions"].setText(f"{info.resolution[0]} × {info.resolution[1]}")
        self.labels["file_size"].setText(format_file_size(info.file_size))
        self.labels["format"].setText(info.format)
        self.labels["color_depth"].setText(f"{info.bit_depth}-bit")
        self.labels["color_mode"].setText(info.color_mode)
        self.labels["alpha"].setText("Yes" if info.has_alpha else "No")
        self.labels["aspect_ratio"].setText(f"{info.aspect_ratio:.2f}:1")

    def clear(self):
        for label in self.labels.values():
            label.setText("—")