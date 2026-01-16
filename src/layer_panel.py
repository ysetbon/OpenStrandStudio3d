"""
OpenStrandStudio 3D - Layer Panel
UI panel for managing strand layers (no hierarchy in 3D)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QFrame, QColorDialog, QMenu,
    QWidgetAction
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette


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
                    background-color: #4a90d9;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    color: white;
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
        """Show right-click context menu with hover effects"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555555;
                padding: 4px;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555555;
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

        # Delete - with hover label
        delete_label = HoverLabel("Delete", self)
        delete_action = QWidgetAction(self)
        delete_action.setDefaultWidget(delete_label)
        delete_action.triggered.connect(self._request_delete)
        menu.addAction(delete_action)

        menu.exec_(self.mapToGlobal(pos))

    def _pick_color(self):
        """Open color picker dialog"""
        r, g, b = [int(c * 255) for c in self.strand_color]
        current = QColor(r, g, b)

        # Create dialog explicitly to style it properly
        color_dialog = QColorDialog(current, self)
        color_dialog.setWindowTitle("Select Strand Color")
        color_dialog.setOption(QColorDialog.DontUseNativeDialog)

        # Style the dialog with neutral button colors
        color_dialog.setStyleSheet("""
            QColorDialog {
                background-color: #2a2a2a;
            }
            QColorDialog QWidget {
                background-color: #2a2a2a;
                color: white;
            }
            QColorDialog QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 70px;
            }
            QColorDialog QPushButton:hover {
                background-color: #5a5a5a;
            }
            QColorDialog QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QColorDialog QLineEdit {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555555;
                padding: 4px;
            }
            QColorDialog QSpinBox {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555555;
            }
            QColorDialog QLabel {
                color: white;
            }
        """)

        if color_dialog.exec_() == QColorDialog.Accepted:
            color = color_dialog.currentColor()
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
    deselect_all_requested = pyqtSignal()       # deselect all strands

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
                background-color: #d9dbdf;
                color: #2b2b2b;
                border-radius: 4px;
            }
        """)
        layout.addWidget(header)

        # Info label
        self.info_label = QLabel("No strands - use Add Strand mode")
        self.info_label.setStyleSheet("color: #6b6f75; padding: 10px;")
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

        # Bottom buttons - row 1
        buttons_layout1 = QHBoxLayout()

        self.btn_show_all = QPushButton("Show All")
        self.btn_show_all.clicked.connect(self._show_all)
        buttons_layout1.addWidget(self.btn_show_all)

        self.btn_hide_all = QPushButton("Hide All")
        self.btn_hide_all.clicked.connect(self._hide_all)
        buttons_layout1.addWidget(self.btn_hide_all)

        layout.addLayout(buttons_layout1)

        # Bottom buttons - row 2
        buttons_layout2 = QHBoxLayout()

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        buttons_layout2.addWidget(self.btn_deselect_all)

        layout.addLayout(buttons_layout2)

        # Apply light theme
        self.setStyleSheet("""
            QWidget {
                background-color: #e4e5e7;
                color: #2b2b2b;
            }
            QPushButton {
                background-color: #f2f3f4;
                border: 1px solid #b7bbc0;
                border-radius: 4px;
                padding: 5px 10px;
                color: #2b2b2b;
            }
            QPushButton:hover {
                background-color: #e6e8ea;
            }
            QPushButton:pressed {
                background-color: #d8dade;
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
        # Connect color change to our handler that propagates to all strands in set
        button.color_changed.connect(self._on_strand_color_changed)

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

    def _deselect_all(self):
        """Deselect all strands in panel and canvas"""
        # Deselect in panel
        if self.selected_strand and self.selected_strand in self.layer_buttons:
            self.layer_buttons[self.selected_strand].set_selected(False)
        self.selected_strand = None

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

    def clear(self):
        """Remove all layer buttons"""
        for name in list(self.layer_buttons.keys()):
            self.remove_strand(name)

    def get_strand_count(self):
        """Get number of strands"""
        return len(self.layer_buttons)
