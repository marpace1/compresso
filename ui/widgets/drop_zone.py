from pathlib import Path
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QPushButton,
                                 QFileDialog, QApplication)
from PySide6.QtCore import Qt, Signal, QMimeData, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QPainter, QColor, QFont

class DropZone(QFrame):
    """Drag-and-drop zone for image files. Also has a Browse button."""
    file_dropped = Signal(Path)     # User dropped a file
    folder_dropped = Signal(Path)   # User dropped a folder (for batch)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon (use unicode/emoji or a simple drawn icon)
        self.icon_label = QLabel("--")
        self.icon_label.setObjectName("dropIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFont(QFont("Inter", 48, QFont.Weight.ExtraLight))
        layout.addWidget(self.icon_label)

        # Main text
        self.title_label = QLabel("Drop image here")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        # Sub text
        self.subtitle = QLabel("or")
        self.subtitle.setObjectName("mutedLabel")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle)

        # Browse button
        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setObjectName("secondaryBtn")
        self.browse_btn.setFixedSize(160, 38)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self._browse)
        layout.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Supported formats hint
        self.formats_label = QLabel("PNG, JPEG, BMP, TIFF, GIF, HEIC, AVIF, WEBP")
        self.formats_label.setObjectName("mutedLabel")
        self.formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.formats_label.setFont(QFont("Inter", 10))
        layout.addWidget(self.formats_label)

    def _browse(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.heic *.avif *.webp)"
        )
        if files:
            self.file_dropped.emit(Path(files[0]))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.is_dir():
                self.folder_dropped.emit(path)
            elif path.is_file():
                self.file_dropped.emit(path)