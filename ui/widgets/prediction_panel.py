from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from models import CompressionPrediction
from utils.helpers import format_file_size, format_time

class PredictionPanel(QFrame):
    """Displays predicted compression results. Updates live as settings change."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._setup_ui()
        self._animations = {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("Prediction")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        # Grid of prediction values
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.setColumnStretch(1, 1)
        layout.addLayout(self.grid)

        # Create label pairs with icons
        items = [
            ("output_size", "Output Size", "—"),
            ("compression", "Compression", "—"),
            ("quality", "Visual Quality", "—"),
            ("ssim", "Expected SSIM", "—"),
            ("psnr", "Expected PSNR", "—"),
            ("time", "Processing Time", "—"),
        ]

        self.labels = {}
        self.value_labels = {}

        for i, (key, label_text, default) in enumerate(items):
            key_label = QLabel(label_text)
            key_label.setObjectName("subtitleLabel")
            key_label.setMinimumWidth(120)

            value_label = QLabel(default)
            value_label.setObjectName("valueLabel")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            value_label.setFont(QFont("Inter", 13, QFont.Weight.Bold))

            self.grid.addWidget(key_label, i, 0)
            self.grid.addWidget(value_label, i, 1)
            self.labels[key] = key_label
            self.value_labels[key] = value_label

        # Recommendation
        self.recommendation_label = QLabel("")
        self.recommendation_label.setObjectName("mutedLabel")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setFont(QFont("Inter", 10))
        layout.addWidget(self.recommendation_label)

    def update_prediction(self, prediction: CompressionPrediction):
        """Update all prediction values with animation."""
        updates = {
            "output_size": format_file_size(prediction.estimated_output_size),
            "compression": f"{prediction.compression_ratio * 100:.1f}%",
            "quality": f"{prediction.visual_quality:.1f}%",
            "ssim": f"{prediction.expected_ssim:.4f}",
            "psnr": f"{prediction.expected_psnr:.1f} dB",
            "time": format_time(prediction.estimated_time),
        }

        for key, text in updates.items():
            label = self.value_labels[key]
            # Animate text change (simple: just update, the theme handles transitions)
            label.setText(text)

            # Color coding for quality
            if key == "quality":
                val = prediction.visual_quality
                if val >= 95:
                    label.setStyleSheet("color: #e5e5e5; font-weight: bold; font-size: 13px;")
                elif val >= 90:
                    label.setStyleSheet("color: #888888; font-weight: bold; font-size: 13px;")
                else:
                    label.setStyleSheet("color: #808080; font-weight: bold; font-size: 13px;")
            elif key == "compression":
                val = prediction.compression_ratio * 100
                if val >= 70:
                    label.setStyleSheet("color: #e5e5e5; font-weight: bold; font-size: 13px;")
                elif val >= 40:
                    label.setStyleSheet("color: #888888; font-weight: bold; font-size: 13px;")
                else:
                    label.setStyleSheet("color: #808080; font-weight: bold; font-size: 13px;")

        self.recommendation_label.setText(prediction.recommendation_text)

    def clear(self):
        for label in self.value_labels.values():
            label.setText("—")
            label.setStyleSheet("")
        self.recommendation_label.setText("")