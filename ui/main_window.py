"""Compresso — Main Window.

Ties together all widgets, workers, and core modules into a cohesive application.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QAction, QFont, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
)

from models import (
    AnalysisResult,
    CompressionPrediction,
    CompressionResult,
    CompressionSettings,
    ImageInfo,
)
from core.analyzer import ImageAnalyzer
from core.compressor import ImageCompressor
from core.metrics import QualityMetrics
from core.predictor import CompressionPredictor
from themes.dark_theme import DarkTheme
from ui.widgets.drop_zone import DropZone
from ui.widgets.image_info_panel import ImageInfoPanel
from ui.widgets.smart_sliders import DualSmartSliders
from ui.widgets.prediction_panel import PredictionPanel
from ui.widgets.difficulty_meter import DifficultyMeter
from ui.widgets.comparison_view import ComparisonView
from ui.widgets.stats_panel import StatsPanel
from ui.dialogs.batch_dialog import BatchDialog
from workers.analysis_worker import AnalysisWorker
from workers.compression_worker import CompressionWorker, TargetSizeWorker
from utils.helpers import (
    format_file_size,
    format_time,
    generate_output_path,
    get_output_extension,
    is_supported_input,
)
from utils.logger import setup_logger


class MainWindow(QMainWindow):
    """Main application window for Compresso."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compresso — Image Compression")
        self.setMinimumSize(700, 500)
        self.resize(1280, 820)

        self.logger = setup_logger("main_window")

        # State
        self._image_info: ImageInfo | None = None
        self._analysis: AnalysisResult | None = None
        self._prediction: CompressionPrediction | None = None
        self._compression_result: CompressionResult | None = None
        self._current_settings: CompressionSettings = CompressionSettings()
        self._remove_metadata = False
        self._original_pixmap: QPixmap | None = None

        # Core engines (lazy-loaded in workers, but keep predictors for live updates)
        self._predictor = CompressionPredictor()

        # Thread pool
        self._thread_pool = QThreadPool.globalInstance()
        self._thread_pool.setMaxThreadCount(4)

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_connections()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(10)

        # ---- App title bar ----
        title_bar = QHBoxLayout()
        self._title_label = QLabel("Compresso")
        self._title_label.setObjectName("titleLabel")
        self._title_label.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        title_bar.addWidget(self._title_label)

        version = QLabel("v1.0.0")
        version.setObjectName("mutedLabel")
        version.setFont(QFont("Inter", 10))
        title_bar.addWidget(version)
        title_bar.addStretch()

        self._status_indicator = QLabel("● Ready")
        self._status_indicator.setObjectName("accentLabel")
        self._status_indicator.setFont(QFont("Inter", 11))
        title_bar.addWidget(self._status_indicator)
        root.addLayout(title_bar)

        # ---- Scrollable content area ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ---- Drop zone ----
        self.drop_zone = DropZone()
        content_layout.addWidget(self.drop_zone)

        # ---- Two-column layout ----
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #2a2a2a; }")
        splitter.setChildrenCollapsible(True)

        # -- Left column --
        left_col = QWidget()
        left_col.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(10)

        self.info_panel = ImageInfoPanel()
        left_layout.addWidget(self.info_panel)

        self.difficulty_meter = DifficultyMeter()
        left_layout.addWidget(self.difficulty_meter)

        self.comparison_view = ComparisonView()
        left_layout.addWidget(self.comparison_view, 1)

        # -- Right column --
        right_col = QWidget()
        right_col.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(10)

        self.smart_sliders = DualSmartSliders()
        right_layout.addWidget(self.smart_sliders)

        self.prediction_panel = PredictionPanel()
        right_layout.addWidget(self.prediction_panel)

        self.stats_panel = StatsPanel()
        right_layout.addWidget(self.stats_panel)

        splitter.addWidget(left_col)
        splitter.addWidget(right_col)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        content_layout.addWidget(splitter, 1)
        scroll.setWidget(content_widget)
        root.addWidget(scroll, 1)

        # ---- Bottom action bar ----
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        # Metadata checkbox
        self.meta_checkbox = QCheckBox("Remove metadata (EXIF, GPS, thumbnails)")
        self.meta_checkbox.setObjectName("mutedLabel")
        self.meta_checkbox.toggled.connect(self._on_metadata_toggle)
        action_bar.addWidget(self.meta_checkbox)

        action_bar.addStretch()

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("secondaryBtn")
        self.reset_btn.setFixedHeight(38)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._reset)
        action_bar.addWidget(self.reset_btn)

        self.batch_btn = QPushButton("Batch Mode")
        self.batch_btn.setObjectName("secondaryBtn")
        self.batch_btn.setFixedHeight(38)
        self.batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_btn.clicked.connect(self._open_batch_dialog)
        action_bar.addWidget(self.batch_btn)

        self.save_btn = QPushButton("Save As")
        self.save_btn.setObjectName("secondaryBtn")
        self.save_btn.setFixedHeight(38)
        self.save_btn.setEnabled(False)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_as)
        action_bar.addWidget(self.save_btn)

        self.compress_btn = QPushButton("Compress")
        self.compress_btn.setObjectName("primaryBtn")
        self.compress_btn.setFixedSize(160, 38)
        self.compress_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compress_btn.clicked.connect(self._compress)
        action_bar.addWidget(self.compress_btn)

        root.addLayout(action_bar)

    def _setup_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setObjectName("menuBar")

        # File menu
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open Image…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._browse_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save As…", self)
        save_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_action.triggered.connect(self._save_as)
        save_action.setEnabled(False)
        self._save_action = save_action
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        batch_action = QAction("Batch Mode…", self)
        batch_action.setShortcut("Ctrl+B")
        batch_action.triggered.connect(self._open_batch_dialog)
        file_menu.addAction(batch_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menu_bar.addMenu("View")

        reset_action = QAction("Reset", self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self._reset)
        view_menu.addAction(reset_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def _setup_connections(self):
        self.drop_zone.file_dropped.connect(self._on_file_dropped)
        self.drop_zone.folder_dropped.connect(self._on_folder_dropped)
        self.smart_sliders.settings_changed.connect(self._on_settings_changed)
        self.smart_sliders.target_compress_requested.connect(self._compress_to_target)

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------

    def _on_file_dropped(self, filepath: Path):
        if not is_supported_input(filepath):
            self._show_error(f"Unsupported format: {filepath.suffix}")
            return
        self._load_image(filepath)

    def _on_folder_dropped(self, folder: Path):
        """Open batch dialog with the folder's images."""
        images = [
            p
            for p in folder.rglob("*")
            if p.is_file() and is_supported_input(p)
        ]
        if not images:
            self._show_error("No supported images found in folder.")
            return
        self._open_batch_dialog(filepaths=images)

    def _browse_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.heic *.avif *.webp)",
        )
        if files:
            self._load_image(Path(files[0]))

    def _load_image(self, filepath: Path):
        self._set_status("Analyzing…", "#888888")
        self._clear_results()

        # Load preview immediately
        try:
            self._original_pixmap = QPixmap(str(filepath))
        except Exception:
            self._original_pixmap = None

        # Start background analysis
        worker = AnalysisWorker(filepath)
        worker.signals.info_ready.connect(self._on_info_ready)
        worker.signals.analysis_complete.connect(self._on_analysis_complete)
        worker.signals.error.connect(self._on_analysis_error)
        self._thread_pool.start(worker)

    def _on_info_ready(self, info: ImageInfo):
        self._image_info = info
        self.info_panel.update_info(info)
        self.setWindowTitle(f"Compresso — {info.filename}")

    def _on_analysis_complete(self, analysis: AnalysisResult):
        self._analysis = analysis
        self.difficulty_meter.update_difficulty(analysis)
        self.smart_sliders.set_analysis(self._image_info, analysis)
        self._update_prediction()
        self._set_status("● Ready — Settings configured", "#e5e5e5")

        # Show preview
        if self._original_pixmap:
            self.comparison_view.set_images(original_path=self._image_info.filepath)

    def _on_analysis_error(self, error: str):
        self._set_status("● Error", "#808080")
        self._show_error(f"Failed to analyze image:\n{error}")

    # ------------------------------------------------------------------
    # Settings & prediction
    # ------------------------------------------------------------------

    def _on_settings_changed(self, settings: CompressionSettings):
        self._current_settings = settings
        self._update_prediction()

    def _update_prediction(self):
        if not self._image_info or not self._analysis:
            return
        self._prediction = self._predictor.predict(
            self._image_info, self._analysis, self._current_settings
        )
        self.prediction_panel.update_prediction(self._prediction)

    # ------------------------------------------------------------------
    # Compression
    # ------------------------------------------------------------------

    def _compress(self):
        if not self._image_info or not self._analysis:
            return

        settings = self._current_settings
        settings.remove_metadata = self._remove_metadata

        self.compress_btn.setEnabled(False)
        self.compress_btn.setText("Processing…")
        self._set_status("Compressing…", "#888888")
        self.stats_panel.clear()

        worker = CompressionWorker(self._image_info, self._analysis, settings)
        worker.signals.progress.connect(self._on_compress_progress)
        worker.signals.complete.connect(self._on_compress_complete)
        worker.signals.error.connect(self._on_compress_error)
        self._thread_pool.start(worker)

    def _on_compress_progress(self, progress: float):
        pass  # Could add a progress bar to the compress button

    def _on_compress_complete(self, result: CompressionResult):
        self._compression_result = result
        self.compress_btn.setEnabled(True)
        self.compress_btn.setText("Compress")
        self.smart_sliders.target_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self._save_action.setEnabled(True)

        if result.success:
            self._set_status("● Compression complete", "#e5e5e5")
            self.stats_panel.update_results(result)

            # Calculate SSIM for stats
            if self._image_info:
                try:
                    metrics = QualityMetrics()
                    import cv2
                    original = cv2.imread(str(self._image_info.filepath))
                    compressed = cv2.imread(str(result.output_path))
                    if original is not None and compressed is not None:
                        ssim_val = metrics.calculate_ssim(original, compressed)
                        psnr_val = metrics.calculate_psnr(original, compressed)
                        result.ssim = ssim_val
                        result.psnr = psnr_val
                        self.stats_panel.update_results(result)
                except Exception:
                    pass

            # Update comparison view
            self.comparison_view.set_images(
                original_path=self._image_info.filepath,
                compressed_path=result.output_path,
            )
        else:
            self._set_status("● Compression failed", "#808080")
            if result.error_message:
                self._show_error(result.error_message)

    def _on_compress_error(self, error: str):
        self.compress_btn.setEnabled(True)
        self.compress_btn.setText("Compress")
        self._set_status("● Error", "#808080")
        self._show_error(f"Compression failed:\n{error}")

    def _compress_to_target(self, target_bytes: int):
        """Binary-search compression to hit a target file size."""
        if not self._image_info:
            return

        fmt = self._current_settings.output_format
        if fmt == "ORIGINAL":
            fmt = self._image_info.format.upper()

        self.compress_btn.setEnabled(False)
        self.compress_btn.setText("Targeting…")
        self.smart_sliders.target_btn.setEnabled(False)
        self._set_status(f"Compressing to {format_file_size(target_bytes)}…", "#888888")
        self.stats_panel.clear()

        worker = TargetSizeWorker(
            self._image_info, target_bytes, fmt, self._remove_metadata
        )
        worker.signals.complete.connect(self._on_compress_complete)
        worker.signals.error.connect(self._on_target_error)
        self._thread_pool.start(worker)

    def _on_target_error(self, error: str):
        self.compress_btn.setEnabled(True)
        self.compress_btn.setText("Compress")
        self.smart_sliders.target_btn.setEnabled(True)
        self._set_status("● Error", "#808080")
        self._show_error(f"Target compression failed:\n{error}")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save_as(self):
        if not self._compression_result or not self._compression_result.success:
            return
        src = self._compression_result.output_path
        if not src or not src.exists():
            return

        ext = get_output_extension(self._current_settings.output_format)
        default_name = src.stem + "_compressed" + ext

        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Compressed Image", str(Path.cwd() / default_name),
            f"Images (*{ext})"
        )
        if dest:
            import shutil
            shutil.copy2(str(src), dest)

    # ------------------------------------------------------------------
    # Batch mode
    # ------------------------------------------------------------------

    def _open_batch_dialog(self, filepaths=None):
        settings = self._current_settings
        settings.remove_metadata = self._remove_metadata
        dialog = BatchDialog(self, filepaths=filepaths, settings=settings)
        dialog.exec()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _on_metadata_toggle(self, checked: bool):
        self._remove_metadata = checked
        self._update_prediction()

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def _reset(self):
        self._image_info = None
        self._analysis = None
        self._prediction = None
        self._compression_result = None
        self._current_settings = CompressionSettings()
        self._original_pixmap = None

        self.info_panel.clear()
        self.difficulty_meter.clear()
        self.prediction_panel.clear()
        self.stats_panel.clear()
        self.comparison_view.clear()
        self.smart_sliders.compression_slider.setValue(50)
        self.smart_sliders.quality_slider.setValue(95)
        self.compress_btn.setEnabled(True)
        self.compress_btn.setText("Compress")
        self.save_btn.setEnabled(False)
        self._save_action.setEnabled(False)
        self.drop_zone.setVisible(True)
        self.setWindowTitle("Compresso — Image Compression")
        self._set_status("● Ready", "#e5e5e5")

    def _clear_results(self):
        self._compression_result = None
        self.stats_panel.clear()
        self.comparison_view.clear()
        self.save_btn.setEnabled(False)
        self._save_action.setEnabled(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text: str, color: str = "#e5e5e5"):
        self._status_indicator.setText(text)
        self._status_indicator.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _show_error(self, message: str):
        QMessageBox.critical(self, "Compresso — Error", message)

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Compresso",
            "<h3>Compresso v1.0.0</h3>"
            "<p>Professional-grade local image compression.</p>"
            "<p>Intelligently analyzes each image and determines "
            "the most efficient compression strategy while "
            "preserving the highest possible visual quality.</p>"
            "<p>Built with Python, PySide6, OpenCV, and love.</p>",
        )