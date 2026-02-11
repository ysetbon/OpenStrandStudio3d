"""
OpenStrandStudio 3D - Custom Title Bar
Windows custom title bar with larger icon/title and native-like controls.
"""

from PyQt5.QtCore import Qt, QPoint, QRect, QSize
from PyQt5.QtGui import QIcon, QImage, QPixmap, QPainter
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QToolButton, QWidget, QStyle


class CustomTitleBar(QWidget):
    """Custom, Cursor-style title bar for frameless windows."""

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(35)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 0, 4, 0)
        self._layout.setSpacing(8)

        self.icon_label = QLabel(self)
        self.icon_label.setObjectName("TitleIconLabel")
        self.icon_label.setFixedSize(48, 35)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self.icon_label, 0, Qt.AlignVCenter)

        self._icon_title_gap = QWidget(self)
        self._icon_title_gap.setFixedWidth(12)
        self._layout.addWidget(self._icon_title_gap, 0, Qt.AlignVCenter)

        self.title_label = QLabel(self._window.windowTitle(), self)
        self.title_label.setObjectName("WindowTitleLabel")
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.title_label.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self.title_label, 0, Qt.AlignVCenter)
        self._layout.addStretch(1)

        self.minimize_button = self._create_button("WindowControlButton")
        self.maximize_button = self._create_button("WindowControlButton")
        self.close_button = self._create_button("WindowCloseButton")

        self.minimize_button.clicked.connect(self._window.showMinimized)
        self.maximize_button.clicked.connect(self._toggle_maximize_restore)
        self.close_button.clicked.connect(self._window.close)

        self._layout.addWidget(self.minimize_button)
        self._layout.addWidget(self.maximize_button)
        self._layout.addWidget(self.close_button)

        self._window.windowTitleChanged.connect(self.title_label.setText)
        self._window.windowIconChanged.connect(self._update_icon)
        self._update_icon(self._window.windowIcon())
        self.update_window_state(self._window.isMaximized())

    def _create_button(self, object_name: str) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName(object_name)
        button.setFixedSize(46, 30)
        button.setFocusPolicy(Qt.NoFocus)
        button.setAutoRaise(True)
        return button

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drag_region(event.globalPos()):
            self._toggle_maximize_restore()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _toggle_maximize_restore(self):
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def _update_icon(self, icon: QIcon):
        if icon.isNull():
            self.icon_label.clear()
            return
        # Keep the icon visually the same size as before the title-bar height reduction.
        icon_size = max(24, min(self.icon_label.width(), self.icon_label.height()) - 1)
        prepared = self._prepare_title_icon(icon, icon_size)
        if prepared.isNull():
            self.icon_label.clear()
            return
        self.icon_label.setPixmap(prepared)

    def _prepare_title_icon(self, icon: QIcon, target_size: int) -> QPixmap:
        # Pull the highest available icon size to avoid blurry upscaling.
        available_sizes = icon.availableSizes()
        if available_sizes:
            largest_size = max(available_sizes, key=lambda size: size.width() * size.height())
            source_pixmap = icon.pixmap(largest_size)
        else:
            source_pixmap = icon.pixmap(QSize(512, 512))

        if source_pixmap.isNull():
            return QPixmap()

        image = source_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        content_rect = self._content_rect(image)
        if content_rect.isNull():
            return source_pixmap.scaled(
                target_size,
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

        # If logo contains a wide wordmark, keep a wider left region for the emblem
        # (not a strict square) so curved edges are not clipped.
        crop_rect = content_rect
        if content_rect.width() > int(content_rect.height() * 1.15):
            emblem_width = min(content_rect.width(), int(content_rect.height() * 1.35))
            crop_rect = QRect(content_rect.left(), content_rect.top(), emblem_width, content_rect.height())

        cropped = image.copy(crop_rect)
        refined_rect = self._content_rect(cropped)
        if not refined_rect.isNull():
            cropped = cropped.copy(refined_rect)

        # Add transparent padding so anti-aliased edges don't appear cut.
        pad = max(2, int(min(cropped.width(), cropped.height()) * 0.08))
        padded = QImage(
            cropped.width() + (pad * 2),
            cropped.height() + (pad * 2),
            QImage.Format_ARGB32,
        )
        padded.fill(0)
        painter = QPainter(padded)
        painter.drawImage(pad, pad, cropped)
        painter.end()

        return QPixmap.fromImage(padded).scaled(
            target_size,
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    def _content_rect(self, image: QImage) -> QRect:
        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return QRect()

        min_x = width
        min_y = height
        max_x = -1
        max_y = -1

        # For transparent images, find any visible pixel.
        if image.hasAlphaChannel():
            for y in range(height):
                for x in range(width):
                    alpha = (image.pixel(x, y) >> 24) & 0xFF
                    if alpha > 0:
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
        else:
            # Opaque fallback: keep the entire image.
            return QRect(0, 0, width, height)

        if max_x < min_x or max_y < min_y:
            return QRect()
        return QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def update_window_state(self, is_maximized: bool):
        left_margin = 18 if is_maximized else 16
        self._layout.setContentsMargins(left_margin, 0, 4, 0)

        style = self.style()
        self.minimize_button.setIcon(style.standardIcon(QStyle.SP_TitleBarMinButton))
        if is_maximized:
            self.maximize_button.setIcon(style.standardIcon(QStyle.SP_TitleBarNormalButton))
            self.maximize_button.setToolTip("Restore")
        else:
            self.maximize_button.setIcon(style.standardIcon(QStyle.SP_TitleBarMaxButton))
            self.maximize_button.setToolTip("Maximize")
        self.close_button.setIcon(style.standardIcon(QStyle.SP_TitleBarCloseButton))

    def is_drag_region(self, global_pos: QPoint) -> bool:
        """True when the point is over the draggable title area."""
        local_pos = self.mapFromGlobal(global_pos)
        if not self.rect().contains(local_pos):
            return False

        child = self.childAt(local_pos)
        if child in (self.minimize_button, self.maximize_button, self.close_button):
            return False
        return True
