from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                                 QProgressBar)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont
from models import AnalysisResult


class DifficultyMeter(QFrame):
    """Visual meter showing compression difficulty of the current image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("Compression Difficulty")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        layout.addWidget(self.progress)

        # Label row
        label_row = QHBoxLayout()
        self.difficulty_label = QLabel("—")
        self.difficulty_label.setObjectName("subtitleLabel")
        self.difficulty_label.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))

        self.difficulty_hint = QLabel("")
        self.difficulty_hint.setObjectName("mutedLabel")
        self.difficulty_hint.setAlignment(Qt.AlignmentFlag.AlignRight)

        label_row.addWidget(self.difficulty_label)
        label_row.addStretch()
        label_row.addWidget(self.difficulty_hint)
        layout.addLayout(label_row)

    def update_difficulty(self, analysis: 'AnalysisResult'):
        """Update the meter from analysis results."""
        value = int(analysis.compression_difficulty * 100)

        # Animate
        anim = QPropertyAnimation(self.progress, b"value")
        anim.setStartValue(self.progress.value())
        anim.setEndValue(value)
        anim.setDuration(600)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

        self.difficulty_label.setText(analysis.difficulty_label)

        # Color the progress bar
        if value < 30:
            self.progress.setObjectName("successBar")
            self.difficulty_hint.setText("Great compression potential")
        elif value < 60:
            self.progress.setObjectName("")
            self.difficulty_hint.setText("Moderate compression possible")
        elif value < 80:
            self.progress.setObjectName("warningBar")
            self.difficulty_hint.setText("Complex image, careful compression")
        else:
            self.progress.setObjectName("errorBar")
            self.difficulty_hint.setText("Very complex, minimal compression")

        self.progress.style().unpolish(self.progress)
        self.progress.style().polish(self.progress)

    def clear(self):
        self.progress.setValue(0)
        self.difficulty_label.setText("—")
        self.difficulty_hint.setText("")