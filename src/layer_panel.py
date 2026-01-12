"""
OpenStrandStudio 3D - Layer Panel
UI panel for managing strand layers (no hierarchy in 3D)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QFrame, QColorDialog, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette


class LayerButton(QPushButton):
    """Button representing a single strand layer"""

    visibility_changed = pyqtSignal(str, bool)  # name, visible
    color_changed = pyqtSignal(str, tuple)      # name, color (r,g,b)

    def __init__(self, strand_name: str, color=(0.9, 0.5, 0.1), parent=None):
        super().__init__(parent)

        self.strand_name = strand_name
        self.strand_color = color
        self.is_visible = True
        self.is_selected = False

        self._setup_ui()

    def _setup_ui(self):
        """Setup the button appearance"""
        self.setFixedHeight(36)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

        self._update_style()

        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _update_style(self):
        """Update button style based on state"""
        # Convert color to QColor
        r, g, b = [int(c * 255) for c in self.strand_color]

        if self.is_selected:
            border_color = "#FFD700"  # Gold for selected
            border_width = 2
        else:
            border_color = "#555555"
            border_width = 1

        opacity = 1.0 if self.is_visible else 0.4

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({r}, {g}, {b}, {opacity});
                border: {border_width}px solid {border_color};
                border-radius: 4px;
                color: white;
                text-align: left;
                padding-left: 10px;
                font-weight: {'bold' if self.is_selected else 'normal'};
            }}
            QPushButton:hover {{
                border-color: #888888;
            }}
        """)

        # Set text with visibility indicator
        visibility_icon = "👁" if self.is_visible else "○"
        self.setText(f"{visibility_icon}  {self.strand_name}")

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

    def _show_context_menu(self, pos):
        """Show right-click context menu"""
        menu = QMenu(self)

        # Toggle visibility
        if self.is_visible:
            visibility_action = menu.addAction("Hide")
        else:
            visibility_action = menu.addAction("Show")
        visibility_action.triggered.connect(lambda: self.set_visible(not self.is_visible))

        # Change color
        color_action = menu.addAction("Change Color...")
        color_action.triggered.connect(self._pick_color)

        menu.addSeparator()

        # Delete
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self._request_delete)

        menu.exec_(self.mapToGlobal(pos))

    def _pick_color(self):
        """Open color picker dialog"""
        r, g, b = [int(c * 255) for c in self.strand_color]
        current = QColor(r, g, b)

        color = QColorDialog.getColor(current, self, "Select Strand Color")
        if color.isValid():
            new_color = (color.redF(), color.greenF(), color.blueF())
            self.set_color(new_color)

    def _request_delete(self):
        """Request deletion of this strand"""
        # This would be connected to parent for actual deletion
        pass


class LayerPanel(QWidget):
    """Panel displaying all strand layers"""

    strand_selected = pyqtSignal(str)           # strand name
    strand_visibility_changed = pyqtSignal(str, bool)  # name, visible
    strand_color_changed = pyqtSignal(str, tuple)      # name, color
    strand_delete_requested = pyqtSignal(str)   # strand name

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layer_buttons = {}  # name -> LayerButton
        self.selected_strand = None

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
                background-color: #2a2a2a;
                border-radius: 4px;
            }
        """)
        layout.addWidget(header)

        # Info label
        self.info_label = QLabel("No strands - use Add Strand mode")
        self.info_label.setStyleSheet("color: #888888; padding: 10px;")
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
        buttons_layout = QHBoxLayout()

        self.btn_show_all = QPushButton("Show All")
        self.btn_show_all.clicked.connect(self._show_all)
        buttons_layout.addWidget(self.btn_show_all)

        self.btn_hide_all = QPushButton("Hide All")
        self.btn_hide_all.clicked.connect(self._hide_all)
        buttons_layout.addWidget(self.btn_hide_all)

        layout.addLayout(buttons_layout)

        # Apply dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)

    def add_strand(self, name: str, color=(0.9, 0.5, 0.1)):
        """Add a new strand layer button"""
        if name in self.layer_buttons:
            return

        # Hide info label when we have strands
        self.info_label.hide()

        # Create button
        button = LayerButton(name, color)
        button.clicked.connect(lambda checked, n=name: self._on_button_clicked(n))
        button.visibility_changed.connect(self.strand_visibility_changed.emit)
        button.color_changed.connect(self.strand_color_changed.emit)

        self.layer_buttons[name] = button

        # Insert before stretch
        self.layers_layout.insertWidget(self.layers_layout.count() - 1, button)

    def remove_strand(self, name: str):
        """Remove a strand layer button"""
        if name not in self.layer_buttons:
            return

        button = self.layer_buttons.pop(name)
        self.layers_layout.removeWidget(button)
        button.deleteLater()

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

    def _on_button_clicked(self, name: str):
        """Handle layer button click"""
        self.select_strand(name)
        self.strand_selected.emit(name)

    def _show_all(self):
        """Show all strands"""
        for button in self.layer_buttons.values():
            button.set_visible(True)

    def _hide_all(self):
        """Hide all strands"""
        for button in self.layer_buttons.values():
            button.set_visible(False)

    def clear(self):
        """Remove all layer buttons"""
        for name in list(self.layer_buttons.keys()):
            self.remove_strand(name)

    def get_strand_count(self):
        """Get number of strands"""
        return len(self.layer_buttons)
