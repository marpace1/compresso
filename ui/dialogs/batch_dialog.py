from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                                 QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
                                 QFileDialog, QAbstractItemView, QFrame)
from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtGui import QFont, QColor
from models import CompressionSettings, CompressionResult, BatchItem
from workers import BatchWorker
from utils.helpers import format_file_size, format_time
from utils.logger import setup_logger

class BatchDialog(QDialog):
    """Dialog for batch compression of multiple images."""
    
    def __init__(self, parent=None, filepaths=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Compression — Compresso")
        self.setMinimumSize(750, 500)
        self.resize(850, 550)
        self.setObjectName("dialog")
        
        self.filepaths: list[Path] = filepaths or []
        self.settings: CompressionSettings = settings or CompressionSettings()
        self.output_dir: Path | None = None
        self.batch_items: list[BatchItem] = []
        self.worker: BatchWorker | None = None
        self.logger = setup_logger("batch_dialog")
        
        self._setup_ui()
        if self.filepaths:
            self._populate_table()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Batch Compression")
        title.setObjectName("titleLabel")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        
        self.count_label = QLabel("0 images")
        self.count_label.setObjectName("subtitleLabel")
        header.addWidget(self.count_label)
        layout.addLayout(header)
        
        # Total progress
        total_layout = QHBoxLayout()
        total_label = QLabel("Overall Progress")
        total_label.setObjectName("subtitleLabel")
        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 100)
        self.total_progress.setValue(0)
        self.total_progress.setTextVisible(True)
        self.total_progress.setFixedHeight(8)
        total_layout.addWidget(total_label)
        total_layout.addWidget(self.total_progress, 1)
        layout.addLayout(total_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Filename", "Original Size", "Status", "Compressed", "Saved", "Time"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        # Buttons row
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        self.add_btn = QPushButton("Add Images")
        self.add_btn.setObjectName("secondaryBtn")
        self.add_btn.clicked.connect(self._add_images)
        buttons.addWidget(self.add_btn)
        
        self.output_btn = QPushButton("Set Output Folder")
        self.output_btn.setObjectName("secondaryBtn")
        self.output_btn.clicked.connect(self._set_output_dir)
        buttons.addWidget(self.output_btn)
        
        self.output_label = QLabel("Same as source")
        self.output_label.setObjectName("mutedLabel")
        buttons.addWidget(self.output_label)
        
        self.start_btn = QPushButton("Start Batch")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedWidth(160)
        self.start_btn.clicked.connect(self._start_batch)
        buttons.addWidget(self.start_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("secondaryBtn")
        self.close_btn.clicked.connect(self.close)
        buttons.addWidget(self.close_btn)
        
        layout.addLayout(buttons)
        
        # Summary (shown after completion)
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("accentLabel")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)
    
    def _populate_table(self):
        self.table.setRowCount(len(self.filepaths))
        for i, fp in enumerate(self.filepaths):
            size = fp.stat().st_size if fp.exists() else 0
            
            name_item = QTableWidgetItem(fp.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, name_item)
            
            size_item = QTableWidgetItem(format_file_size(size))
            self.table.setItem(i, 1, size_item)
            
            status_item = QTableWidgetItem("Pending")
            status_item.setForeground(QColor("#888888"))
            self.table.setItem(i, 2, status_item)
            
            self.batch_items.append(BatchItem(
                filepath=fp, filename=fp.name, original_size=size
            ))
        
        self.count_label.setText(f"{len(self.filepaths)} images")
    
    def _add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.gif *.heic *.avif *.webp)"
        )
        if files:
            new_paths = [Path(f) for f in files]
            self.filepaths.extend(new_paths)
            self._populate_table()  # Re-populate (simpler than appending)
    
    def _set_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if dir_path:
            self.output_dir = Path(dir_path)
            self.output_label.setText(str(self.output_dir))
    
    def _start_batch(self):
        if not self.filepaths:
            return
        
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Processing...")
        self.summary_label.setVisible(False)
        
        self.worker = BatchWorker(self.filepaths, self.settings, self.output_dir)
        self.worker.signals.item_complete.connect(self._on_item_complete)
        self.worker.signals.item_error.connect(self._on_item_error)
        self.worker.signals.item_started.connect(self._on_item_started)
        self.worker.signals.total_progress.connect(self._on_total_progress)
        self.worker.signals.all_complete.connect(self._on_all_complete)
        
        QThreadPool.globalInstance().start(self.worker)
    
    def _on_item_started(self, index: int):
        if index < self.table.rowCount():
            item = self.table.item(index, 2)
            if item:
                item.setText("Processing...")
                item.setForeground(QColor("#888888"))
    
    def _on_item_complete(self, index: int, result: CompressionResult):
        if index < self.table.rowCount():
            # Status
            item = self.table.item(index, 2)
            if item:
                item.setText("Done")
                item.setForeground(QColor("#e5e5e5"))
            
            # Compressed size
            self.table.setItem(index, 3, QTableWidgetItem(format_file_size(result.output_size)))
            
            # Saved
            saved_item = QTableWidgetItem(format_file_size(result.space_saved))
            saved_item.setForeground(QColor("#e5e5e5"))
            self.table.setItem(index, 4, saved_item)
            
            # Time
            self.table.setItem(index, 5, QTableWidgetItem(format_time(result.processing_time)))
    
    def _on_item_error(self, index: int, error: str):
        if index < self.table.rowCount():
            item = self.table.item(index, 2)
            if item:
                item.setText("Error")
                item.setForeground(QColor("#808080"))
                item.setToolTip(error)
    
    def _on_total_progress(self, progress: float):
        self.total_progress.setValue(int(progress * 100))
    
    def _on_all_complete(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start Batch")
        
        # Calculate summary
        total_original = sum(item.original_size for item in self.batch_items)
        total_saved = 0
        total_time = 0
        success = 0
        
        for item in self.batch_items:
            if item.result and item.result.success:
                total_saved += item.space_saved if hasattr(item, 'space_saved') else 0
                total_time += item.result.processing_time
                success += 1
        
        if success > 0:
            pct = (total_saved / total_original * 100) if total_original > 0 else 0
            self.summary_label.setText(
                f"{success}/{len(self.filepaths)} images compressed successfully | "
                f"Saved {format_file_size(total_saved)} ({pct:.1f}%) | "
                f"Total time: {format_time(total_time)}"
            )
            self.summary_label.setVisible(True)
    
    def closeEvent(self, event):
        if self.worker:
            # Let current item finish
            pass
        event.accept()