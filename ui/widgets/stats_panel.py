from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                                 QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from models import CompressionResult
from utils.helpers import format_file_size, format_time

class StatsPanel(QFrame):
    """Displays actual compression statistics after compression completes."""

    metadata_changed = Signal(bool)  # User toggled metadata removal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setVisible(False)  # Hidden until compression is done
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("Compression Results")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        # Results grid
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.setColumnStretch(1, 1)
        layout.addLayout(self.grid)

        items = [
            ("original_size", "Original Size"),
            ("compressed_size", "Compressed Size"),
            ("space_saved", "Space Saved"),
            ("compression_pct", "Compression"),
            ("quality", "Visual Quality"),
            ("ssim", "SSIM"),
            ("psnr", "PSNR"),
            ("format", "Output Format"),
            ("time", "Processing Time"),
        ]

        self.value_labels = {}
        for i, (key, label_text) in enumerate(items):
            key_label = QLabel(label_text)
            key_label.setObjectName("subtitleLabel")
            key_label.setMinimumWidth(100)

            value_label = QLabel("—")
            value_label.setObjectName("valueLabel")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            value_label.setFont(QFont("Inter", 13, QFont.Weight.Bold))

            self.grid.addWidget(key_label, i, 0)
            self.grid.addWidget(value_label, i, 1)
            self.value_labels[key] = value_label

    def update_results(self, result: CompressionResult):
        """Show compression results."""
        self.setVisible(True)

        if result.ssim is not None:
            quality = max(0, min(100, result.ssim * 100))
        else:
            quality = 0

        self.value_labels["original_size"].setText(format_file_size(result.original_size))
        self.value_labels["compressed_size"].setText(format_file_size(result.output_size))
        self.value_labels["space_saved"].setText(format_file_size(result.space_saved))
        self.value_labels["compression_pct"].setText(f"{result.compression_ratio * 100:.1f}%")

        if result.ssim is not None:
            self.value_labels["quality"].setText(f"{quality:.1f}%")
            self.value_labels["ssim"].setText(f"{result.ssim:.4f}")
        else:
            self.value_labels["quality"].setText("N/A")
            self.value_labels["ssim"].setText("N/A")

        if result.psnr is not None:
            self.value_labels["psnr"].setText(f"{result.psnr:.1f} dB")
        else:
            self.value_labels["psnr"].setText("N/A")

        self.value_labels["format"].setText(result.format_used)
        self.value_labels["time"].setText(format_time(result.processing_time))

        # Color coding
        if result.compression_ratio >= 0.7:
            self.value_labels["compression_pct"].setStyleSheet("color: #e5e5e5; font-weight: bold; font-size: 13px;")
        elif result.compression_ratio >= 0.4:
            self.value_labels["compression_pct"].setStyleSheet("color: #888888; font-weight: bold; font-size: 13px;")

    def clear(self):
        self.setVisible(False)
        for label in self.value_labels.values():
            label.setText("—")
            label.setStyleSheet("")