import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                 QPushButton, QSlider, QComboBox)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (QPixmap, QImage, QPainter, QPen, QColor, QFont,
                            QCursor, QWheelEvent, QMouseEvent, QPainterPath)


class ComparisonView(QWidget):
    """Interactive before/after comparison with draggable divider, zoom, and heatmap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(300)

        self._original_pixmap: QPixmap | None = None
        self._compressed_pixmap: QPixmap | None = None
        self._heatmap_pixmap: QPixmap | None = None
        self._show_heatmap = False

        self._divider_pos = 0.5  # 0-1, fraction of width
        self._dragging_divider = False

        self._zoom = 1.0
        self._pan_offset = QPoint(0, 0)
        self._panning = False
        self._pan_start = QPoint()

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header with title and controls
        header = QHBoxLayout()

        title = QLabel("Before / After")
        title.setObjectName("cardTitle")
        header.addWidget(title)
        header.addStretch()

        # Zoom controls
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("mutedLabel")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header.addWidget(self.zoom_label)

        self._zoom_buttons = []
        for zoom_level in ["100%", "200%", "400%"]:
            btn = QPushButton(zoom_level)
            btn.setObjectName("smallBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(24)
            if zoom_level == "100%":
                btn.setChecked(True)
            zoom_val = int(zoom_level.replace("%", "")) / 100.0
            btn.clicked.connect(lambda checked, z=zoom_val, b=btn: self._set_zoom(z, b))
            header.addWidget(btn)
            self._zoom_buttons.append(btn)

        # Heatmap toggle
        self.heatmap_btn = QPushButton("Heatmap")
        self.heatmap_btn.setObjectName("smallBtn")
        self.heatmap_btn.setCheckable(True)
        self.heatmap_btn.setFixedHeight(24)
        self.heatmap_btn.toggled.connect(self._toggle_heatmap)
        header.addWidget(self.heatmap_btn)

        layout.addLayout(header)

        # Labels
        labels_row = QHBoxLayout()
        self.original_label = QLabel("◄ Original")
        self.original_label.setObjectName("mutedLabel")
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.compressed_label = QLabel("Compressed ►")
        self.compressed_label.setObjectName("mutedLabel")
        self.compressed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        labels_row.addWidget(self.original_label)
        labels_row.addStretch()
        labels_row.addWidget(self.compressed_label)
        layout.addLayout(labels_row)

        # Canvas widget (the actual drawing area)
        self.canvas = ComparisonCanvas(self)
        self.canvas.divider_moved.connect(self._on_divider_moved)
        layout.addWidget(self.canvas, 1)

    def set_images(self, original_path=None, compressed_path=None,
                   original_array=None, compressed_array=None):
        """Set the before/after images from file paths or numpy arrays."""
        if original_path:
            self._original_pixmap = QPixmap(str(original_path))
        elif original_array is not None:
            self._original_pixmap = self._array_to_pixmap(original_array)

        if compressed_path:
            self._compressed_pixmap = QPixmap(str(compressed_path))
        elif compressed_array is not None:
            self._compressed_pixmap = self._array_to_pixmap(compressed_array)

        self._generate_heatmap()
        self.canvas.set_images(self._original_pixmap, self._compressed_pixmap)
        self.canvas.set_heatmap(self._heatmap_pixmap)
        self.canvas.update()

    def _generate_heatmap(self):
        """Generate a grayscale difference map between original and compressed."""
        if self._original_pixmap is None or self._compressed_pixmap is None:
            return

        try:
            import cv2
            orig = self._pixmap_to_array(self._original_pixmap).copy()
            comp = self._pixmap_to_array(self._compressed_pixmap).copy()

            # Ensure same size
            if orig.shape[:2] != comp.shape[:2]:
                comp = cv2.resize(comp, (orig.shape[1], orig.shape[0]))

            # Compute absolute difference per channel, then take mean
            diff = cv2.absdiff(orig, comp)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

            # Gamma-amplified monochrome: white (no change) -> dark (large change)
            # Use gamma < 1 to amplify subtle differences
            gray_f = gray_diff.astype(np.float32) / 255.0
            amplified = np.power(gray_f + 1e-6, 0.35) * 255.0
            gray_val = np.clip(255.0 - amplified, 20.0, 245.0).astype(np.uint8)

            # Build a 3-channel grayscale image (RGB order for QImage)
            rgb_heatmap = np.stack([gray_val, gray_val, gray_val], axis=2)
            h, w = rgb_heatmap.shape[:2]
            qimg = QImage(rgb_heatmap.data, w, h, w * 3,
                          QImage.Format.Format_RGB888)
            self._heatmap_pixmap = QPixmap.fromImage(qimg.copy())
        except Exception:
            self._heatmap_pixmap = None

    def _set_zoom(self, zoom: float, btn=None):
        self._zoom = zoom
        self.zoom_label.setText(f"{int(zoom * 100)}%")
        self.canvas.set_zoom(zoom)

        # Update button check states
        for b in self._zoom_buttons:
            b.setChecked(False)
        if btn:
            btn.setChecked(True)

    def _toggle_heatmap(self, checked):
        self._show_heatmap = checked
        self.canvas.set_show_heatmap(checked)

    def _on_divider_moved(self, pos):
        self._divider_pos = pos

    def _array_to_pixmap(self, arr: np.ndarray) -> QPixmap:
        """Convert numpy array (BGR or RGB) to QPixmap."""
        if arr.ndim == 2:
            h, w = arr.shape
            qimg = QImage(arr.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            h, w, ch = arr.shape
            if ch == 4:
                qimg = QImage(arr.data, w, h, w * 4,
                              QImage.Format.Format_RGBA8888)
            elif ch == 3:
                # Convert BGR to RGB
                import cv2
                rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb.data, w, h, w * 3,
                              QImage.Format.Format_RGB888)
            else:
                return QPixmap()
        return QPixmap.fromImage(qimg.copy())  # .copy() to keep data alive

    def _pixmap_to_array(self, pixmap: QPixmap) -> np.ndarray:
        """Convert QPixmap to numpy array (BGR)."""
        qimg = pixmap.toImage().convertToFormat(
            QImage.Format.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        ptr.setsize(h * w * 4)
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4))
        import cv2
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        return bgr

    def clear(self):
        self._original_pixmap = None
        self._compressed_pixmap = None
        self._heatmap_pixmap = None
        self.canvas.clear()
        self.original_label.setText("◄ Original")
        self.compressed_label.setText("Compressed ►")


class ComparisonCanvas(QWidget):
    """The actual painting canvas for the comparison view."""

    divider_moved = Signal(float)  # 0-1 position

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setMouseTracking(True)

        self._original: QPixmap | None = None
        self._compressed: QPixmap | None = None
        self._heatmap: QPixmap | None = None
        self._show_heatmap = False
        self._divider = 0.5
        self._dragging = False
        self._zoom = 1.0
        self._hover_divider = False

    def set_images(self, original, compressed):
        self._original = original
        self._compressed = compressed
        self.update()

    def set_heatmap(self, heatmap):
        self._heatmap = heatmap

    def set_show_heatmap(self, show):
        self._show_heatmap = show
        self.update()

    def set_zoom(self, zoom):
        self._zoom = zoom
        self.update()

    def clear(self):
        self._original = None
        self._compressed = None
        self._heatmap = None
        self._divider = 0.5
        self.update()

    def paintEvent(self, event):
        if not self._original or not self._compressed:
            self._paint_placeholder()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # Calculate scaled sizes maintaining aspect ratio
        orig_aspect = self._original.width() / max(self._original.height(), 1)
        widget_aspect = w / max(h, 1)

        if orig_aspect > widget_aspect:
            draw_w = w
            draw_h = int(w / orig_aspect)
        else:
            draw_h = h
            draw_w = int(h * orig_aspect)

        x_offset = (w - draw_w) // 2
        y_offset = (h - draw_h) // 2

        # Apply zoom
        if self._zoom > 1.0:
            draw_w = int(draw_w * self._zoom)
            draw_h = int(draw_h * self._zoom)
            x_offset = (w - draw_w) // 2
            y_offset = (h - draw_h) // 2

        # Determine right image
        right_image = (self._heatmap
                       if (self._show_heatmap and self._heatmap)
                       else self._compressed)

        # Draw left (original) - clipped to left of divider
        painter.save()
        clip_left = QRect(x_offset, y_offset,
                          int(draw_w * self._divider), draw_h)
        painter.setClipRect(clip_left)
        painter.drawPixmap(x_offset, y_offset, draw_w, draw_h, self._original)
        painter.restore()

        # Draw right (compressed) - clipped to right of divider
        painter.save()
        div_x = x_offset + int(draw_w * self._divider)
        clip_right = QRect(div_x, y_offset,
                           draw_w - int(draw_w * self._divider), draw_h)
        painter.setClipRect(clip_right)
        painter.drawPixmap(x_offset, y_offset, draw_w, draw_h, right_image)
        painter.restore()

        # Draw divider line
        painter.setPen(QPen(QColor("#e5e5e5"), 1))
        painter.drawLine(div_x, y_offset, div_x, y_offset + draw_h)

        # Draw divider handle (circle)
        handle_y = y_offset + draw_h // 2
        handle_rect = QRect(div_x - 12, handle_y - 20, 24, 40)
        painter.setBrush(QColor("#e5e5e5"))
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawRoundedRect(handle_rect, 6, 6)

        # Draw arrows on handle
        painter.setPen(QPen(QColor("#111111"), 2))
        # Left arrow
        painter.drawLine(div_x - 4, handle_y, div_x + 2, handle_y - 5)
        painter.drawLine(div_x - 4, handle_y, div_x + 2, handle_y + 5)
        # Right arrow
        painter.drawLine(div_x + 4, handle_y, div_x - 2, handle_y - 5)
        painter.drawLine(div_x + 4, handle_y, div_x - 2, handle_y + 5)

        # Labels on images
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Inter", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(x_offset + 8, y_offset + 20, "ORIGINAL")
        label = "COMPRESSED" if not self._show_heatmap else "DIFFERENCE"
        painter.drawText(div_x + 8, y_offset + 20, label)

        painter.end()

    def _paint_placeholder(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setPen(QColor("#555555"))
        font = QFont("Inter", 13)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                         "Compress an image to see comparison")
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            div_x = int(self.width() * self._divider)
            if abs(event.position().x() - div_x) < 20:
                self._dragging = True
                self.setCursor(Qt.CursorShape.SplitHCursor)

    def mouseMoveEvent(self, event):
        div_x = int(self.width() * self._divider)

        if self._dragging:
            self._divider = max(0.02, min(0.98,
                                           event.position().x() / self.width()))
            self.divider_moved.emit(self._divider)
            self.update()
        else:
            # Show resize cursor near divider
            near = abs(event.position().x() - div_x) < 20
            if near != self._hover_divider:
                self._hover_divider = near
                self.setCursor(Qt.CursorShape.SplitHCursor if near
                               else Qt.CursorShape.SizeHorCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.SizeHorCursor)

    def wheelEvent(self, event: QWheelEvent):
        # Zoom with scroll wheel
        delta = event.angleDelta().y()
        if delta > 0:
            new_zoom = min(4.0, self._zoom * 1.2)
        else:
            new_zoom = max(0.5, self._zoom / 1.2)
        self._zoom = round(new_zoom, 1)
        self.update()