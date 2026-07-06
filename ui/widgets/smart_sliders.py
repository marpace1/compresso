from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                                 QSlider, QPushButton, QComboBox, QSpinBox)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont
from models import ImageInfo, AnalysisResult, CompressionSettings, CompressionPrediction
from utils.helpers import clamp


class DualSmartSliders(QFrame):
    """Two intelligently linked sliders: Compression % and Quality %.
    When one changes, the other predicts its value based on image analysis."""

    settings_changed = Signal(object)  # Emits CompressionSettings
    target_compress_requested = Signal(int)  # Emits target bytes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._analysis = None
        self._image_info = None
        self._updating = False  # Prevent feedback loops
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Section title
        title = QLabel("Compression Controls")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        # --- Smart Mode Toggle ---
        smart_layout = QHBoxLayout()
        self.smart_label = QLabel("Smart Mode")
        self.smart_label.setObjectName("subtitleLabel")
        self.smart_toggle = QPushButton("ON")
        self.smart_toggle.setObjectName("smallBtn")
        self.smart_toggle.setCheckable(True)
        self.smart_toggle.setChecked(True)
        self.smart_toggle.setFixedSize(50, 26)
        self.smart_toggle.clicked.connect(self._on_smart_toggle)
        smart_layout.addWidget(self.smart_label)
        smart_layout.addStretch()
        smart_layout.addWidget(self.smart_toggle)
        layout.addLayout(smart_layout)

        # --- Compression Slider ---
        comp_header = QHBoxLayout()
        comp_label = QLabel("Compression")
        comp_label.setObjectName("subtitleLabel")
        self.comp_value_label = QLabel("50%")
        self.comp_value_label.setObjectName("valueLabel")
        self.comp_value_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        comp_header.addWidget(comp_label)
        comp_header.addStretch()
        comp_header.addWidget(self.comp_value_label)
        layout.addLayout(comp_header)

        self.compression_slider = QSlider(Qt.Orientation.Horizontal)
        self.compression_slider.setRange(0, 95)
        self.compression_slider.setValue(50)
        self.compression_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.compression_slider.valueChanged.connect(self._on_compression_changed)
        layout.addWidget(self.compression_slider)

        # --- Quality Slider ---
        qual_header = QHBoxLayout()
        qual_label = QLabel("Quality")
        qual_label.setObjectName("subtitleLabel")
        self.qual_value_label = QLabel("95%")
        self.qual_value_label.setObjectName("valueLabel")
        self.qual_value_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        qual_header.addWidget(qual_label)
        qual_header.addStretch()
        qual_header.addWidget(self.qual_value_label)
        layout.addLayout(qual_header)

        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(80, 100)
        self.quality_slider.setValue(95)
        self.quality_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        layout.addWidget(self.quality_slider)

        # --- Output Format ---
        fmt_layout = QHBoxLayout()
        fmt_label = QLabel("Output Format")
        fmt_label.setObjectName("subtitleLabel")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["ORIGINAL", "JPEG", "PNG", "WEBP", "AVIF"])
        self.format_combo.setCurrentText("ORIGINAL")
        self.format_combo.setFixedWidth(140)
        self.format_combo.currentTextChanged.connect(self._emit_settings)
        fmt_layout.addWidget(fmt_label)
        fmt_layout.addStretch()
        fmt_layout.addWidget(self.format_combo)
        layout.addLayout(fmt_layout)

        # --- Preset Buttons ---
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Presets")
        preset_label.setObjectName("subtitleLabel")
        self.presets = {}
        for name, text, value in [
            ("max_quality", "Max Quality", 20),
            ("balanced", "Balanced", 50),
            ("max_compression", "Max Compress", 85),
            ("archive", "Archive", 5),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("smallBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked, n=name, v=value: self._apply_preset(n, v, btn))
            self.presets[name] = btn
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        preset_layout.addWidget(preset_label)
        layout.addLayout(preset_layout)

        # --- Recommend Button ---
        self.recommend_btn = QPushButton("Use Recommended Settings")
        self.recommend_btn.setObjectName("primaryBtn")
        self.recommend_btn.setFixedHeight(36)
        self.recommend_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recommend_btn.clicked.connect(self._use_recommended)
        layout.addWidget(self.recommend_btn)

        # --- Target File Size ---
        target_title = QLabel("Target Size")
        target_title.setObjectName("subtitleLabel")
        layout.addWidget(target_title)

        target_input_row = QHBoxLayout()
        target_input_row.setSpacing(6)

        self.target_input = QSpinBox()
        self.target_input.setRange(1, 99999)
        self.target_input.setValue(500)
        self.target_input.setFixedHeight(32)
        self.target_input.setSuffix("")
        self.target_input.setMinimumWidth(100)

        self.target_unit = QComboBox()
        self.target_unit.addItems(["KB", "MB", "GB"])
        self.target_unit.setCurrentText("KB")
        self.target_unit.setFixedHeight(32)
        self.target_unit.setFixedWidth(72)

        self.target_btn = QPushButton("Compress to Target")
        self.target_btn.setObjectName("smallBtn")
        self.target_btn.setFixedHeight(32)
        self.target_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.target_btn.clicked.connect(self._on_target_compress)

        target_input_row.addWidget(self.target_input, 1)
        target_input_row.addWidget(self.target_unit)
        target_input_row.addWidget(self.target_btn)
        layout.addLayout(target_input_row)

    def _on_target_compress(self):
        """Parse the target size input and emit the signal."""
        value = self.target_input.value()
        unit = self.target_unit.currentText()
        multipliers = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}
        target_bytes = int(value * multipliers[unit])
        if target_bytes > 0:
            self.target_compress_requested.emit(target_bytes)

    def set_analysis(self, image_info: ImageInfo, analysis: AnalysisResult):
        """Called when image analysis completes. Sets up slider relationships."""
        self._image_info = image_info
        self._analysis = analysis

        # Set recommended values
        self.quality_slider.blockSignals(True)
        self.compression_slider.blockSignals(True)
        self.compression_slider.setValue(analysis.recommended_compression)
        self.quality_slider.setValue(analysis.recommended_quality)
        self.format_combo.setCurrentText(analysis.recommended_format)
        self.quality_slider.blockSignals(False)
        self.compression_slider.blockSignals(False)

        self.comp_value_label.setText(f"{analysis.recommended_compression}%")
        self.qual_value_label.setText(f"{analysis.recommended_quality}%")

        self._emit_settings()

    def _on_compression_changed(self, value: int):
        if self._updating:
            return
        self._updating = True
        self.comp_value_label.setText(f"{value}%")

        if self._analysis and self.smart_toggle.isChecked():
            quality = self._predict_quality_from_compression(value)
            self.quality_slider.setValue(int(clamp(quality, 80, 100)))
            self.qual_value_label.setText(f"{int(clamp(quality, 80, 100))}%")

        self._updating = False
        self._emit_settings()

    def _on_quality_changed(self, value: int):
        if self._updating:
            return
        self._updating = True
        self.qual_value_label.setText(f"{value}%")

        if self._analysis and self.smart_toggle.isChecked():
            compression = self._predict_compression_from_quality(value)
            self.compression_slider.setValue(int(clamp(compression, 0, 95)))
            self.comp_value_label.setText(f"{int(clamp(compression, 0, 95))}%")

        self._updating = False
        self._emit_settings()

    def _predict_quality_from_compression(self, comp: int) -> float:
        if not self._analysis:
            return 100 - comp * 0.2

        difficulty = self._analysis.compression_difficulty

        t = comp / 95.0
        min_quality = 100 - (15 + difficulty * 20)
        min_quality = max(min_quality, 80)

        quality = 100 - (100 - min_quality) * (t ** (1.5 + difficulty))
        return clamp(quality, 80, 100)

    def _predict_compression_from_quality(self, quality: int) -> float:
        if not self._analysis:
            return (100 - quality) * 5

        difficulty = self._analysis.compression_difficulty
        min_quality = 100 - (15 + difficulty * 20)
        min_quality = max(min_quality, 80)

        if quality >= 100:
            return 0.0
        t = ((100 - quality) / (100 - min_quality)) ** (1 / (1.5 + difficulty))
        compression = t * 95
        return clamp(compression, 0, 95)

    def _emit_settings(self):
        settings = CompressionSettings(
            compression_percent=self.compression_slider.value(),
            quality_percent=self.quality_slider.value(),
            output_format=self.format_combo.currentText(),
            smart_mode=self.smart_toggle.isChecked(),
        )
        self.settings_changed.emit(settings)

    def _apply_preset(self, name: str, comp_value: int, clicked_btn):
        for btn in self.presets.values():
            btn.setChecked(False)
        clicked_btn.setChecked(True)

        self.compression_slider.setValue(comp_value)
        if name == "max_quality":
            self.quality_slider.setValue(98)
        elif name == "balanced":
            self.quality_slider.setValue(95)
        elif name == "max_compression":
            self.quality_slider.setValue(85)
        elif name == "archive":
            self.quality_slider.setValue(99)

    def _use_recommended(self):
        if self._analysis:
            self.compression_slider.setValue(self._analysis.recommended_compression)
            self.quality_slider.setValue(self._analysis.recommended_quality)
            self.format_combo.setCurrentText(self._analysis.recommended_format)
            for btn in self.presets.values():
                btn.setChecked(False)

    def get_settings(self) -> 'CompressionSettings':
        return CompressionSettings(
            compression_percent=self.compression_slider.value(),
            quality_percent=self.quality_slider.value(),
            output_format=self.format_combo.currentText(),
            smart_mode=self.smart_toggle.isChecked(),
        )

    def _on_smart_toggle(self, checked):
        self.smart_toggle.setText("ON" if checked else "OFF")
        self._emit_settings()