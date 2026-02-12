"""
OpenStrandStudio 3D - Layer Panel
UI panel for managing strand layers with collapsible set groups
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QFrame, QColorDialog, QMenu,
    QWidgetAction, QSizePolicy, QDialogButtonBox, QAbstractSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPalette, QPainter, QPen, QBrush


def _clamp_channel(value):
    return max(0, min(255, value))


def _shift_hex_color(hex_color, delta):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{_clamp_channel(r + delta):02x}{_clamp_channel(g + delta):02x}{_clamp_channel(b + delta):02x}"


def _card_color_variants(bg_color):
    highlight = _shift_hex_color(bg_color, 15)
    hover = _shift_hex_color(bg_color, 10)
    shadow = _shift_hex_color(bg_color, -45)
    pressed = _shift_hex_color(bg_color, -35)
    checked = _shift_hex_color(bg_color, -25)
    return highlight, hover, shadow, pressed, checked


def _make_card_style(selector, bg_color, text_color, min_width=None, font_weight=600):
    highlight, hover, shadow, pressed, checked = _card_color_variants(bg_color)
    min_width_rule = f"min-width: {min_width}px;" if min_width else ""
    return f"""
        {selector} {{
            background-color: {bg_color};
            border-top: 1px solid {highlight};
            border-left: 1px solid {highlight};
            border-right: 2px solid {shadow};
            border-bottom: 2px solid {shadow};
            border-radius: 8px;
            padding: 5px 8px;
            color: {text_color};
            {min_width_rule}
            font-size: 11px;
            font-weight: {font_weight};
        }}
        {selector}:hover {{
            background-color: {hover};
            border-top: 1px solid {bg_color};
            border-left: 1px solid {bg_color};
            border-right: 2px solid {shadow};
            border-bottom: 2px solid {shadow};
        }}
        {selector}:pressed {{
            background-color: {pressed};
            border-top: 2px solid {shadow};
            border-left: 2px solid {shadow};
            border-right: 1px solid {highlight};
            border-bottom: 1px solid {highlight};
            padding: 6px 7px 4px 9px;
        }}
        {selector}:checked {{
            background-color: {checked};
            border-top: 2px solid {shadow};
            border-left: 2px solid {shadow};
            border-right: 1px solid {highlight};
            border-bottom: 1px solid {highlight};
        }}
        {selector}:checked:hover {{
            background-color: {hover};
        }}
    """


PANEL_BUTTON_TEXT = "#FFFFFF"

# Layer panel buttons styled to match the main toolbar theme.
TOOLBAR_BUTTON_STYLE = """
    QPushButton {
        background-color: #353538;
        border: 1px solid #3E3E42;
        border-radius: 4px;
        padding: 3px 5px;
        color: #E8E8E8;
        font-size: 11px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #454548;
        border-color: #5A5A5D;
    }
    QPushButton:pressed {
        background-color: #2A2A2D;
    }
    QPushButton:checked {
        background-color: #3D3D50;
        border: 1px solid #7B68EE;
        color: #E8E8E8;
    }
    QPushButton:checked:hover {
        background-color: #4A4A60;
    }
"""


class SetGroupHeader(QPushButton):
    """Collapsible header for a set group"""

    toggled_collapse = pyqtSignal(bool)  # True = collapsed
    duplicate_requested = pyqtSignal(str)  # set number
    rotate_requested = pyqtSignal(str)  # set number

    def __init__(self, set_number: str, parent=None):
        super().__init__(parent)
        self.set_number = set_number
        self.is_collapsed = False
        self.strand_count = 0

        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._toggle)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._update_style()

    def _update_style(self):
        arrow = "▼" if not self.is_collapsed else "▶"
        count_text = f"({self.strand_count})" if self.strand_count > 0 else ""
        self.setText(f"  {arrow}  {self.set_number}  {count_text}")

        base_color = "#2D2D30"
        highlight, hover, shadow, pressed, _ = _card_color_variants(base_color)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base_color};
                border-top: 1px solid {highlight};
                border-left: 3px solid #7B68EE;
                border-right: 2px solid {shadow};
                border-bottom: 2px solid {shadow};
                border-radius: 8px;
                color: #E8E8E8;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
                border-top: 2px solid {shadow};
                border-right: 1px solid {highlight};
                border-bottom: 1px solid {highlight};
                border-left: 3px solid #7B68EE;
                padding: 7px 9px 5px 11px;
            }}
        """)

    def _toggle(self):
        self.is_collapsed = not self.is_collapsed
        self._update_style()
        self.toggled_collapse.emit(self.is_collapsed)

    def set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        self._update_style()

    def update_count(self, count: int):
        self.strand_count = count
        self._update_style()

    def _show_context_menu(self, pos):
        from set_group_menu import build_set_group_menu

        menu = build_set_group_menu(
            self,
            on_duplicate=lambda: self.duplicate_requested.emit(self.set_number),
            on_rotate=lambda: self.rotate_requested.emit(self.set_number)
        )
        menu.exec_(self.mapToGlobal(pos))


class SetGroup(QWidget):
    """A collapsible group containing strands from the same set"""

    duplicate_requested = pyqtSignal(str)  # set number
    rotate_requested = pyqtSignal(str)  # set number

    def __init__(self, set_number: str, parent=None):
        super().__init__(parent)
        self.set_number = set_number
        self.strand_buttons = {}  # name -> LayerButton

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        self.header = SetGroupHeader(self.set_number)
        self.header.toggled_collapse.connect(self._on_toggle)
        self.header.duplicate_requested.connect(self.duplicate_requested.emit)
        self.header.rotate_requested.connect(self.rotate_requested.emit)
        layout.addWidget(self.header)

        # Container for strand buttons
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 2, 0, 5)  # Indent children
        self.content_layout.setSpacing(3)
        layout.addWidget(self.content_widget)

    def _on_toggle(self, collapsed: bool):
        self.content_widget.setVisible(not collapsed)

    def add_strand_button(self, button):
        """Add a strand button to this group"""
        self.strand_buttons[button.strand_name] = button
        self.content_layout.addWidget(button)
        self.header.update_count(len(self.strand_buttons))

    def remove_strand_button(self, name: str):
        """Remove a strand button from this group"""
        if name in self.strand_buttons:
            button = self.strand_buttons.pop(name)
            self.content_layout.removeWidget(button)
            button.deleteLater()
            self.header.update_count(len(self.strand_buttons))

    def is_empty(self):
        return len(self.strand_buttons) == 0

    def get_button(self, name: str):
        return self.strand_buttons.get(name)


class HoverLabel(QLabel):
    """Label with hover effect for context menu items"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self._hovered = False
        self.setMinimumHeight(28)
        self.setContentsMargins(8, 4, 8, 4)
        self._update_style()

    def _update_style(self):
        if self._hovered:
            self.setStyleSheet("""
                QLabel {
                    background-color: #454548;
                    color: #E8E8E8;
                    padding: 4px 8px;
                    border-radius: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    color: #E8E8E8;
                    padding: 4px 8px;
                }
            """)

    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)


class LayerButton(QPushButton):
    """Button representing a single strand layer"""

    visibility_changed = pyqtSignal(str, bool)  # name, visible
    color_changed = pyqtSignal(str, tuple)      # name, color (r,g,b,a)

    def __init__(self, strand_name: str, color=(0.667, 0.667, 1.0, 1.0), parent=None):
        super().__init__(parent)

        self.strand_name = strand_name
        self.strand_color = color
        self.is_visible = True
        self.is_selected = False
        self._deletable = True  # Whether this strand can be deleted

        self._setup_ui()

    def _setup_ui(self):
        """Setup the button appearance (v106 style: flat solid color blocks)"""
        self.setFixedHeight(34)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

        self._update_style()

        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _update_style(self):
        """Update button style - flat solid color like v106"""
        # Convert color to QColor (handle both RGB and RGBA)
        r = int(self.strand_color[0] * 255)
        g = int(self.strand_color[1] * 255)
        b = int(self.strand_color[2] * 255)
        a = self.strand_color[3] if len(self.strand_color) > 3 else 1.0

        alpha = int((a if self.is_visible else a * 0.4) * 255)

        # V106 style: solid color background, lighter on hover, darker when checked
        normal = f"rgba({r}, {g}, {b}, {alpha})"
        lighter = f"rgba({_clamp_channel(r+30)}, {_clamp_channel(g+30)}, {_clamp_channel(b+30)}, {alpha})"
        darker = f"rgba({_clamp_channel(r-40)}, {_clamp_channel(g-40)}, {_clamp_channel(b-40)}, {alpha})"

        if self.is_selected:
            border_rule = "border: 2px solid #E6A822;"
        else:
            border_rule = "border: none;"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {normal};
                {border_rule}
                color: white;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {lighter};
            }}
            QPushButton:checked {{
                background-color: {darker};
                border: 2px solid #E6A822;
            }}
            QPushButton:pressed {{
                background-color: {darker};
            }}
        """)

        self.setText(self.strand_name)

    def set_selected(self, selected: bool):
        """Set selection state"""
        self.is_selected = selected
        self.setChecked(selected)
        self._update_style()

    def set_visible(self, visible: bool):
        """Set visibility state"""
        self.is_visible = visible
        self._update_style()
        self.visibility_changed.emit(self.strand_name, visible)

    def set_color(self, color: tuple):
        """Set strand color"""
        self.strand_color = color
        self._update_style()
        self.color_changed.emit(self.strand_name, color)

    def set_deletable(self, deletable: bool):
        """Set whether this strand can be deleted, triggers repaint for purple dot."""
        if self._deletable != deletable:
            self._deletable = deletable
            self.update()

    def paintEvent(self, event):
        """Custom paint to draw purple dot indicator when strand is deletable."""
        super().paintEvent(event)

        if self._deletable:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            rect = self.rect()
            dot_radius = 5
            # Position: centered vertically, 8px from right edge
            cx = rect.width() - 8
            cy = rect.height() // 2

            # Dark border
            painter.setPen(QPen(QColor(30, 30, 30), 1.5))
            painter.setBrush(QBrush(QColor("#7B68EE")))
            painter.drawEllipse(cx - dot_radius, cy - dot_radius,
                                dot_radius * 2, dot_radius * 2)

            painter.end()

    def _show_context_menu(self, pos):
        """Show right-click context menu with hover effects"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D30;
                color: #E8E8E8;
                border: 1px solid #3E3E42;
                padding: 4px;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3E3E42;
                margin: 4px 8px;
            }
        """)

        # Toggle visibility - with hover label
        visibility_text = "Hide" if self.is_visible else "Show"
        visibility_label = HoverLabel(visibility_text, self)
        visibility_action = QWidgetAction(self)
        visibility_action.setDefaultWidget(visibility_label)
        visibility_action.triggered.connect(lambda: self.set_visible(not self.is_visible))
        menu.addAction(visibility_action)

        # Change color - with hover label
        change_color_label = HoverLabel("Change Color...", self)
        change_color_action = QWidgetAction(self)
        change_color_action.setDefaultWidget(change_color_label)
        change_color_action.triggered.connect(self._pick_color)
        menu.addAction(change_color_action)

        menu.addSeparator()

        # Delete - with hover label (disabled when not deletable)
        delete_label = HoverLabel("Delete", self)
        if not self._deletable:
            delete_label.setEnabled(False)
            delete_label.setStyleSheet(delete_label.styleSheet() + "color: #666666;")
        delete_action = QWidgetAction(self)
        delete_action.setDefaultWidget(delete_label)
        delete_action.setEnabled(self._deletable)
        delete_action.triggered.connect(self._request_delete)
        menu.addAction(delete_action)

        menu.exec_(self.mapToGlobal(pos))

    def _pick_color(self):
        """Open color picker dialog with alpha support"""
        # Get current color with alpha
        r, g, b = [int(c * 255) for c in self.strand_color[:3]]
        a = int(self.strand_color[3] * 255) if len(self.strand_color) > 3 else 255
        current = QColor(r, g, b, a)

        # Create dialog explicitly to style it properly
        color_dialog = QColorDialog(current, self)
        color_dialog.setWindowTitle("Select Strand Color")
        color_dialog.setOption(QColorDialog.DontUseNativeDialog)
        color_dialog.setOption(QColorDialog.ShowAlphaChannel)  # Enable alpha slider

        # Style the dialog with neutral window colors (not strand color)
        color_dialog.setStyleSheet("""
            QColorDialog {
                background-color: #3c3c3c;
            }
            QColorDialog QWidget {
                background-color: #3c3c3c;
                color: #e0e0e0;
            }
            QColorDialog QDialogButtonBox {
                background-color: #3c3c3c;
            }
            QColorDialog QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #606060;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 70px;
            }
            QColorDialog QDialogButtonBox QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #606060;
            }
            QColorDialog QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #707070;
            }
            QColorDialog QPushButton:pressed {
                background-color: #2f2f2f;
            }
            QColorDialog QPushButton:default {
                background-color: #3c3c3c;
                border: 1px solid #808080;
                color: #e0e0e0;
            }
            QColorDialog QPushButton:default:hover {
                background-color: #4a4a4a;
                border: 1px solid #8a8a8a;
            }
            QColorDialog QPushButton:focus {
                outline: none;
            }
            QColorDialog QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #555555;
                padding: 4px;
                border-radius: 2px;
            }
            QColorDialog QAbstractSpinBox {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 2px;
                padding: 2px 4px;
            }
            QColorDialog QAbstractSpinBox::up-button,
            QColorDialog QAbstractSpinBox::down-button {
                background-color: #2a2a2a;
                border-left: 1px solid #555555;
                width: 14px;
            }
            QColorDialog QAbstractSpinBox::up-button:hover,
            QColorDialog QAbstractSpinBox::down-button:hover {
                background-color: #3a3a3a;
            }
            QColorDialog QAbstractSpinBox::lineedit {
                background-color: #2a2a2a;
                color: #e0e0e0;
            }
            QColorDialog QAbstractSpinBox::up-arrow,
            QColorDialog QAbstractSpinBox::down-arrow {
                width: 7px;
                height: 7px;
            }
            QColorDialog QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QColorDialog QSlider::groove:horizontal {
                background-color: #2a2a2a;
                height: 6px;
                border-radius: 3px;
            }
            QColorDialog QSlider::handle:horizontal {
                background-color: #606060;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QColorDialog QSlider::sub-page:horizontal {
                background-color: #3a3a3a;
                border-radius: 3px;
            }
            QColorDialog QSlider::add-page:horizontal {
                background-color: #2a2a2a;
                border-radius: 3px;
            }
        """)
        self._force_color_dialog_button_style(color_dialog)
        self._force_color_dialog_spinbox_style(color_dialog)
        self._force_color_dialog_alpha_label_style(color_dialog)

        if color_dialog.exec_() == QColorDialog.Accepted:
            color = color_dialog.currentColor()
            if color.isValid():
                # Include alpha in the color tuple
                new_color = (color.redF(), color.greenF(), color.blueF(), color.alphaF())
                self.set_color(new_color)

    def _force_color_dialog_button_style(self, color_dialog):
        """Force dialog button styling for native button overrides."""
        button_box = color_dialog.findChild(QDialogButtonBox)
        if not button_box:
            return

        button_style = """
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #606060;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #707070;
            }
            QPushButton:pressed {
                background-color: #2f2f2f;
            }
            QPushButton:default {
                background-color: #3c3c3c;
                border: 1px solid #808080;
                color: #e0e0e0;
            }
            QPushButton:default:hover {
                background-color: #4a4a4a;
                border: 1px solid #8a8a8a;
            }
            QPushButton:focus {
                outline: none;
            }
        """
        for button in button_box.buttons():
            button.setStyleSheet(button_style)

    def _force_color_dialog_spinbox_style(self, color_dialog):
        """Force spinbox styling so alpha matches HSV/RGB fields."""
        spinbox_style = """
            QAbstractSpinBox {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 2px;
                padding: 2px 4px;
            }
            QAbstractSpinBox::lineedit {
                background-color: #2a2a2a;
                color: #e0e0e0;
            }
            QAbstractSpinBox::up-button,
            QAbstractSpinBox::down-button {
                background-color: #2a2a2a;
                border-left: 1px solid #555555;
                width: 14px;
            }
            QAbstractSpinBox::up-button:hover,
            QAbstractSpinBox::down-button:hover {
                background-color: #3a3a3a;
            }
            QAbstractSpinBox::up-arrow,
            QAbstractSpinBox::down-arrow {
                width: 7px;
                height: 7px;
            }
        """
        for spinbox in color_dialog.findChildren(QAbstractSpinBox):
            spinbox.setStyleSheet(spinbox_style)

    def _force_color_dialog_alpha_label_style(self, color_dialog):
        """Force alpha label background to match the dialog theme."""
        alpha_label = None
        for label in color_dialog.findChildren(QLabel):
            if "lpha" in label.text().lower():
                alpha_label = label
                break

        if not alpha_label:
            return

        alpha_label.setStyleSheet("""
            QLabel {
                background-color: #3c3c3c;
                color: #e0e0e0;
            }
        """)

        parent = alpha_label.parent()
        if not parent:
            return

        for frame in parent.findChildren(QFrame):
            if frame.geometry() == alpha_label.geometry():
                frame.setStyleSheet("background-color: #3c3c3c; border: none;")
                break

    def _request_delete(self):
        """Request deletion of this strand via LayerPanel signal."""
        if not self._deletable:
            return
        # Walk up to find the LayerPanel and emit its signal
        parent = self.parent()
        while parent:
            if isinstance(parent, LayerPanel):
                parent.strand_delete_requested.emit(self.strand_name)
                return
            parent = parent.parent()


class LayerPanel(QWidget):
    """Panel displaying all strand layers organized by sets"""

    strand_selected = pyqtSignal(str)           # strand name
    strand_visibility_changed = pyqtSignal(str, bool)  # name, visible
    strand_color_changed = pyqtSignal(str, tuple)      # name, color
    strand_delete_requested = pyqtSignal(str)   # strand name
    set_duplicate_requested = pyqtSignal(str)   # set number
    set_rotate_requested = pyqtSignal(str)      # set number
    deselect_all_requested = pyqtSignal()       # deselect all strands
    add_strand_requested = pyqtSignal()         # request to enter add strand mode
    draw_names_requested = pyqtSignal(bool)     # toggle drawing of strand names

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layer_buttons = {}  # name -> LayerButton
        self.set_groups = {}     # set_number -> SetGroup
        self.selected_strand = None
        self.should_draw_names = False  # Toggle for drawing strand names

        self._setup_ui()

    def _setup_ui(self):
        """Setup the panel UI"""
        self.setMinimumWidth(200)
        self.setMaximumWidth(350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Header
        header = QLabel("Layers")
        header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                padding-left: 8px;
                background-color: #2D2D30;
                color: #E8E8E8;
                border-radius: 4px;
                border-left: 3px solid #7B68EE;
            }
        """)
        layout.addWidget(header)

        # Info label
        self.info_label = QLabel("No strands")
        self.info_label.setStyleSheet("color: #A0A0A0; padding: 10px; font-style: italic;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Scroll area for layer buttons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2D2D30;
                width: 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #454548;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555558;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Container for layer buttons
        self.layers_container = QWidget()
        self.layers_layout = QVBoxLayout(self.layers_container)
        self.layers_layout.setContentsMargins(0, 0, 0, 0)
        self.layers_layout.setSpacing(3)
        self.layers_layout.addStretch()

        scroll.setWidget(self.layers_container)
        layout.addWidget(scroll)

        # Bottom buttons
        buttons_layout2 = QVBoxLayout()

        self.btn_draw_names = QPushButton("Names")
        self.btn_draw_names.setCheckable(True)
        self.btn_draw_names.toggled.connect(self._request_draw_names)
        self.btn_draw_names.setStyleSheet(TOOLBAR_BUTTON_STYLE)
        buttons_layout2.addWidget(self.btn_draw_names)

        self.btn_deselect_all = QPushButton("Deselect")
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        self.btn_deselect_all.setStyleSheet(TOOLBAR_BUTTON_STYLE)
        buttons_layout2.addWidget(self.btn_deselect_all)

        self.btn_new_strand = QPushButton("New")
        self.btn_new_strand.clicked.connect(self._request_add_strand)
        self.btn_new_strand.setStyleSheet(TOOLBAR_BUTTON_STYLE)
        buttons_layout2.addWidget(self.btn_new_strand)

        self.btn_delete_strand = QPushButton("Delete")
        self.btn_delete_strand.clicked.connect(self._request_delete_selected)
        self.btn_delete_strand.setStyleSheet(TOOLBAR_BUTTON_STYLE)
        self.btn_delete_strand.setEnabled(False)
        buttons_layout2.addWidget(self.btn_delete_strand)

        layout.addLayout(buttons_layout2)

        # Apply dark theme (no default button style - each button has its own)
        self.setStyleSheet("""
            QWidget {
                background-color: #252528;
                color: #E8E8E8;
            }
        """)

    def add_strand(self, name: str, color=(0.667, 0.667, 1.0, 1.0)):
        """Add a new strand layer button to appropriate set group"""
        if name in self.layer_buttons:
            return

        # Hide info label when we have strands
        self.info_label.hide()

        # Get set number from name
        set_number = self._get_set_number(name)
        if set_number is None:
            set_number = "0"  # Fallback

        # Create or get the set group
        if set_number not in self.set_groups:
            group = SetGroup(set_number)
            self.set_groups[set_number] = group
            group.duplicate_requested.connect(self._on_set_duplicate_requested)
            group.rotate_requested.connect(self._on_set_rotate_requested)
            # Insert group in sorted order (before stretch)
            self._insert_group_sorted(group)

        # Create button
        button = LayerButton(name, color)
        button.clicked.connect(lambda checked, n=name: self._on_button_clicked(n))
        button.visibility_changed.connect(self.strand_visibility_changed.emit)
        button.color_changed.connect(self._on_strand_color_changed)

        self.layer_buttons[name] = button

        # Add to set group
        self.set_groups[set_number].add_strand_button(button)

    def _insert_group_sorted(self, group: SetGroup):
        """Insert a set group in numerically sorted order"""
        try:
            new_num = int(group.set_number)
        except ValueError:
            new_num = 0

        # Find the right position
        insert_idx = 0
        for i in range(self.layers_layout.count() - 1):  # -1 for stretch
            widget = self.layers_layout.itemAt(i).widget()
            if isinstance(widget, SetGroup):
                try:
                    existing_num = int(widget.set_number)
                except ValueError:
                    existing_num = 0
                if new_num > existing_num:
                    insert_idx = i + 1
                else:
                    break

        self.layers_layout.insertWidget(insert_idx, group)

    def remove_strand(self, name: str):
        """Remove a strand layer button"""
        if name not in self.layer_buttons:
            return

        # Get set number and remove from group
        set_number = self._get_set_number(name)
        if set_number and set_number in self.set_groups:
            group = self.set_groups[set_number]
            group.remove_strand_button(name)

            # Remove empty groups
            if group.is_empty():
                self.layers_layout.removeWidget(group)
                group.deleteLater()
                del self.set_groups[set_number]

        # Remove from layer_buttons dict
        if name in self.layer_buttons:
            del self.layer_buttons[name]

        # Show info label if no strands
        if not self.layer_buttons:
            self.info_label.show()

        # Clear selection if removed strand was selected
        if self.selected_strand == name:
            self.selected_strand = None

    def select_strand(self, name: str):
        """Select a strand in the panel"""
        # Deselect previous
        if self.selected_strand and self.selected_strand in self.layer_buttons:
            self.layer_buttons[self.selected_strand].set_selected(False)

        # Select new
        self.selected_strand = name
        if name and name in self.layer_buttons:
            self.layer_buttons[name].set_selected(True)
            self.btn_delete_strand.setEnabled(self.layer_buttons[name]._deletable)
        else:
            self.btn_delete_strand.setEnabled(False)

    def _on_button_clicked(self, name: str):
        """Handle layer button click"""
        self.select_strand(name)
        self.strand_selected.emit(name)

    def _request_add_strand(self):
        """Request to enter add strand mode"""
        self.add_strand_requested.emit()

    def _request_delete_selected(self):
        """Delete the currently selected strand via the toolbar button."""
        if self.selected_strand:
            self.strand_delete_requested.emit(self.selected_strand)

    def _deselect_all(self):
        """Deselect all strands in panel and canvas"""
        # Deselect in panel
        if self.selected_strand and self.selected_strand in self.layer_buttons:
            self.layer_buttons[self.selected_strand].set_selected(False)
        self.selected_strand = None
        self.btn_delete_strand.setEnabled(False)

        # Emit signal to deselect in canvas
        self.deselect_all_requested.emit()

    def _get_set_number(self, strand_name: str):
        """
        Get the set number from a strand name.
        e.g., "1_1" -> "1", "2_3" -> "2"
        """
        parts = strand_name.split('_')
        if len(parts) >= 1:
            return parts[0]
        return None

    def _get_strands_in_set(self, set_number: str):
        """
        Get all strand names that belong to a set.
        e.g., set "1" -> ["1_1", "1_2", "1_3", ...]
        """
        strands_in_set = []
        for name in self.layer_buttons.keys():
            if self._get_set_number(name) == set_number:
                strands_in_set.append(name)
        return strands_in_set

    def _on_strand_color_changed(self, strand_name: str, color: tuple):
        """
        Handle color change from a strand button.
        Propagates the color to all strands in the same set.
        """
        # Get the set number for this strand
        set_number = self._get_set_number(strand_name)

        if set_number is None:
            # Fallback: just emit for this strand only
            self.strand_color_changed.emit(strand_name, color)
            return

        # Get all strands in this set
        strands_in_set = self._get_strands_in_set(set_number)

        # Update color for all layer buttons in the set
        for name in strands_in_set:
            button = self.layer_buttons.get(name)
            if button:
                # Update button color without triggering another signal
                button.strand_color = color
                button._update_style()

        # Find the main window and update the canvas with batch method
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'canvas'):
            main_window = main_window.parent()

        if main_window and hasattr(main_window, 'canvas'):
            # Use efficient batch update
            try:
                set_num_int = int(set_number)
                main_window.canvas.update_color_for_set(set_num_int, color)
            except ValueError:
                # Fallback to individual updates if set_number isn't a valid int
                for name in strands_in_set:
                    self.strand_color_changed.emit(name, color)

    def _on_set_duplicate_requested(self, set_number: str):
        """Forward set-level duplication requests to the main window."""
        self.set_duplicate_requested.emit(set_number)

    def _on_set_rotate_requested(self, set_number: str):
        """Forward set-level rotation requests to the main window."""
        self.set_rotate_requested.emit(set_number)

    def _request_draw_names(self, checked):
        """Toggle the drawing of strand names and emit the corresponding signal."""
        self.should_draw_names = checked
        self.draw_names_requested.emit(self.should_draw_names)

    def clear(self):
        """Remove all layer buttons and set groups"""
        # Remove all set groups
        for set_number in list(self.set_groups.keys()):
            group = self.set_groups.pop(set_number)
            self.layers_layout.removeWidget(group)
            group.deleteLater()

        # Clear layer buttons dict
        self.layer_buttons.clear()
        self.selected_strand = None

        # Show info label
        self.info_label.show()

    def get_strand_count(self):
        """Get number of strands"""
        return len(self.layer_buttons)

    def is_strand_deletable(self, strand):
        """Check if a strand can be deleted (not both ends occupied by children)."""
        return strand.is_deletable()

    def update_layer_button_states(self, canvas):
        """Update deletable state of all layer buttons based on strand data."""
        strand_map = {s.name: s for s in canvas.strands}
        for name, button in self.layer_buttons.items():
            strand = strand_map.get(name)
            if strand:
                button.set_deletable(strand.is_deletable())
            else:
                button.set_deletable(False)

        # Update toolbar delete button for current selection
        if self.selected_strand and self.selected_strand in self.layer_buttons:
            self.btn_delete_strand.setEnabled(self.layer_buttons[self.selected_strand]._deletable)
        else:
            self.btn_delete_strand.setEnabled(False)
