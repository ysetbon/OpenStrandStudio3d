"""
OpenStrandStudio 3D - Main Window
Contains the main application window with canvas and layer panel
"""

import json
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QToolBar, QAction, QStatusBar, QSplitter, QLabel,
    QFileDialog, QMessageBox, QActionGroup
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from strand_drawing_canvas import StrandDrawingCanvas
from layer_panel import LayerPanel
from undo_redo_manager import UndoRedoManager
from strand_profile_dialog import StrandProfileDialog
from user_settings import get_settings


class MainWindow(QMainWindow):
    """Main application window for OpenStrandStudio 3D"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenStrandStudio 3D")
        self.setMinimumSize(900, 600)

        # Initialize components
        self.canvas = None
        self.layer_panel = None
        self.undo_redo_manager = None

        self._setup_ui()
        self._setup_undo_redo()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()
        self._apply_dark_theme()
        self._apply_button_styles()
        self._load_user_settings()

    def _setup_ui(self):
        """Setup the main UI layout"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with splitter
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Create the 3D canvas
        self.canvas = StrandDrawingCanvas(self)

        # Create the layer panel
        self.layer_panel = LayerPanel(self)

        # Add to splitter
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.layer_panel)

        # Set stretch factors so layout adapts to any window size
        splitter.setStretchFactor(0, 3)  # Canvas gets 3/4 of space
        splitter.setStretchFactor(1, 1)  # Layer panel gets 1/4 of space

        main_layout.addWidget(splitter)

    def _setup_undo_redo(self):
        """Setup the undo/redo manager after canvas is created"""
        self.undo_redo_manager = UndoRedoManager(self.canvas)

        # Connect undo/redo signals
        self.undo_redo_manager.state_changed.connect(self._update_undo_redo_actions)
        self.undo_redo_manager.undo_performed.connect(self._on_undo_performed)
        self.undo_redo_manager.redo_performed.connect(self._on_redo_performed)

        # Store reference on canvas for easy access from canvas operations
        self.canvas.undo_redo_manager = self.undo_redo_manager

    def _setup_toolbar(self):
        """Setup the main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.main_toolbar = toolbar  # Store reference for styling

        # === File operations ===
        self.action_new = QAction("New", self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.triggered.connect(self._new_project)
        toolbar.addAction(self.action_new)

        self.action_save = QAction("Save", self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.triggered.connect(self._save_project)
        toolbar.addAction(self.action_save)

        self.action_load = QAction("Load", self)
        self.action_load.setShortcut("Ctrl+O")
        self.action_load.triggered.connect(self._load_project)
        toolbar.addAction(self.action_load)

        toolbar.addSeparator()

        # === Undo/Redo ===
        self.action_undo = QAction("Undo", self)
        self.action_undo.setShortcut("Ctrl+Z")
        self.action_undo.triggered.connect(self._undo)
        self.action_undo.setEnabled(False)
        toolbar.addAction(self.action_undo)

        self.action_redo = QAction("Redo", self)
        self.action_redo.setShortcut("Ctrl+Y")
        self.action_redo.triggered.connect(self._redo)
        self.action_redo.setEnabled(False)
        toolbar.addAction(self.action_redo)

        toolbar.addSeparator()

        # === Mode selection ===
        # Select mode
        self.action_select = QAction("Select", self)
        self.action_select.setCheckable(True)
        self.action_select.setChecked(True)
        self.action_select.triggered.connect(lambda: self._set_mode("select"))
        toolbar.addAction(self.action_select)

        # Add strand mode (hidden - accessed via layer panel + button)
        self.action_add_strand = QAction("Add Strand", self)
        self.action_add_strand.setCheckable(True)
        self.action_add_strand.triggered.connect(lambda: self._set_mode("add_strand"))
        # Not added to toolbar - use layer panel + button instead

        # Attach mode
        self.action_attach = QAction("Attach", self)
        self.action_attach.setCheckable(True)
        self.action_attach.triggered.connect(lambda: self._set_mode("attach"))
        toolbar.addAction(self.action_attach)

        # Move mode
        self.action_move = QAction("Move", self)
        self.action_move.setCheckable(True)
        self.action_move.triggered.connect(lambda: self._set_mode("move"))
        toolbar.addAction(self.action_move)

        # Stretch mode
        self.action_stretch = QAction("Stretch", self)
        self.action_stretch.setCheckable(True)
        self.action_stretch.triggered.connect(lambda: self._set_mode("stretch"))
        toolbar.addAction(self.action_stretch)

        # Rotate mode
        self.action_rotate = QAction("Rotate", self)
        self.action_rotate.setCheckable(True)
        self.action_rotate.triggered.connect(lambda: self._set_mode("rotate"))
        toolbar.addAction(self.action_rotate)

        # Angle Adjust mode
        self.action_angle_adjust = QAction("Adjust", self)
        self.action_angle_adjust.setCheckable(True)
        self.action_angle_adjust.triggered.connect(self._activate_angle_adjust)
        toolbar.addAction(self.action_angle_adjust)

        toolbar.addSeparator()

        # Rigid toggle (shows start/end point spheres)
        self.action_rigid = QAction("Rigid", self)
        self.action_rigid.setCheckable(True)
        self.action_rigid.setChecked(False)
        self.action_rigid.setShortcut("R")
        self.action_rigid.triggered.connect(self._toggle_rigid_points)
        toolbar.addAction(self.action_rigid)

        # Straight segment mode toggle (forces strands to be straight lines)
        self.action_straight = QAction("Straight", self)
        self.action_straight.setCheckable(True)
        self.action_straight.setChecked(False)
        self.action_straight.setShortcut("S")
        self.action_straight.triggered.connect(self._toggle_straight_mode)
        toolbar.addAction(self.action_straight)

        toolbar.addSeparator()

        # Reset camera
        self.action_reset_camera = QAction("Reset", self)
        self.action_reset_camera.triggered.connect(self._reset_camera)
        toolbar.addAction(self.action_reset_camera)

        # Toggle grid
        self.action_toggle_grid = QAction("Grid", self)
        self.action_toggle_grid.setCheckable(True)
        self.action_toggle_grid.setChecked(True)
        self.action_toggle_grid.setShortcut("G")
        self.action_toggle_grid.triggered.connect(self._toggle_grid)
        toolbar.addAction(self.action_toggle_grid)

        # Toggle axes
        self.action_toggle_axes = QAction("Axes", self)
        self.action_toggle_axes.setCheckable(True)
        self.action_toggle_axes.setChecked(True)
        self.action_toggle_axes.setShortcut("A")
        self.action_toggle_axes.triggered.connect(self._toggle_axes)
        toolbar.addAction(self.action_toggle_axes)

        toolbar.addSeparator()

        # Strand Profile Editor
        self.action_strand_profile = QAction("Profile", self)
        self.action_strand_profile.triggered.connect(self._open_strand_profile_editor)
        toolbar.addAction(self.action_strand_profile)

        # Group actions for exclusive selection
        self.mode_actions = [
            self.action_select,
            self.action_add_strand,
            self.action_attach,
            self.action_move,
            self.action_stretch,
            self.action_rotate,
            self.action_angle_adjust
        ]

        # Track current project file
        self.current_project_file = None

        # === Move mode options toolbar (new line) ===
        self.addToolBarBreak()
        self.move_toolbar = QToolBar("Move Options")
        self.move_toolbar.setMovable(False)
        self.addToolBar(self.move_toolbar)

        self.move_mode_group = QActionGroup(self)
        self.move_mode_group.setExclusive(True)

        self.action_move_xz = QAction("Move XZ (Normal)", self)
        self.action_move_xz.setCheckable(True)
        self.action_move_xz.setChecked(True)
        self.action_move_xz.triggered.connect(lambda: self._set_move_axis_mode("normal"))
        self.move_mode_group.addAction(self.action_move_xz)
        self.move_toolbar.addAction(self.action_move_xz)

        self.action_move_y = QAction("Move Y (Shift)", self)
        self.action_move_y.setCheckable(True)
        self.action_move_y.triggered.connect(lambda: self._set_move_axis_mode("vertical"))
        self.move_mode_group.addAction(self.action_move_y)
        self.move_toolbar.addAction(self.action_move_y)

        self.action_move_depth = QAction("Move Depth (Ctrl)", self)
        self.action_move_depth.setCheckable(True)
        self.action_move_depth.triggered.connect(lambda: self._set_move_axis_mode("depth"))
        self.move_mode_group.addAction(self.action_move_depth)
        self.move_toolbar.addAction(self.action_move_depth)

        self.action_move_along = QAction("Move Along (Other Point)", self)
        self.action_move_along.setCheckable(True)
        self.action_move_along.triggered.connect(lambda: self._set_move_axis_mode("along"))
        self.move_mode_group.addAction(self.action_move_along)
        self.move_toolbar.addAction(self.action_move_along)

        self.move_toolbar.addSeparator()

        # Link Control Points toggle - when ON, connected CPs sync for smooth spline
        self.action_link_cps = QAction("Link CPs", self)
        self.action_link_cps.setCheckable(True)
        self.action_link_cps.setChecked(False)  # Default OFF (independent mode)
        self.action_link_cps.triggered.connect(self._toggle_link_control_points)
        self.move_toolbar.addAction(self.action_link_cps)

        # Edit All toggle - when ON, show CPs for all strands and allow moving any
        self.action_edit_all = QAction("Edit All", self)
        self.action_edit_all.setCheckable(True)
        self.action_edit_all.setChecked(False)  # Default OFF
        self.action_edit_all.triggered.connect(self._toggle_edit_all)
        self.move_toolbar.addAction(self.action_edit_all)

        # === Attach mode options toolbar (new line) ===
        self.addToolBarBreak()
        self.attach_toolbar = QToolBar("Attach Options")
        self.attach_toolbar.setMovable(False)
        self.addToolBar(self.attach_toolbar)

        self.attach_mode_group = QActionGroup(self)
        self.attach_mode_group.setExclusive(True)

        self.action_attach_xz = QAction("Attach XZ (Normal)", self)
        self.action_attach_xz.setCheckable(True)
        self.action_attach_xz.setChecked(True)
        self.action_attach_xz.triggered.connect(lambda: self._set_attach_axis_mode("normal"))
        self.attach_mode_group.addAction(self.action_attach_xz)
        self.attach_toolbar.addAction(self.action_attach_xz)

        self.action_attach_y = QAction("Attach Y (Shift)", self)
        self.action_attach_y.setCheckable(True)
        self.action_attach_y.triggered.connect(lambda: self._set_attach_axis_mode("vertical"))
        self.attach_mode_group.addAction(self.action_attach_y)
        self.attach_toolbar.addAction(self.action_attach_y)

        self.action_attach_depth = QAction("Attach Depth (Ctrl)", self)
        self.action_attach_depth.setCheckable(True)
        self.action_attach_depth.triggered.connect(lambda: self._set_attach_axis_mode("depth"))
        self.attach_mode_group.addAction(self.action_attach_depth)
        self.attach_toolbar.addAction(self.action_attach_depth)

        self.action_attach_along = QAction("Attach Along (Other Point)", self)
        self.action_attach_along.setCheckable(True)
        self.action_attach_along.triggered.connect(lambda: self._set_attach_axis_mode("along"))
        self.attach_mode_group.addAction(self.action_attach_along)
        self.attach_toolbar.addAction(self.action_attach_along)

        # === Stretch mode options toolbar (new line) ===
        self.addToolBarBreak()
        self.stretch_toolbar = QToolBar("Stretch Options")
        self.stretch_toolbar.setMovable(False)
        self.addToolBar(self.stretch_toolbar)

        self.stretch_mode_group = QActionGroup(self)
        self.stretch_mode_group.setExclusive(True)

        self.action_stretch_xz = QAction("Stretch XZ (Normal)", self)
        self.action_stretch_xz.setCheckable(True)
        self.action_stretch_xz.setChecked(True)
        self.action_stretch_xz.triggered.connect(lambda: self._set_stretch_axis_mode("normal"))
        self.stretch_mode_group.addAction(self.action_stretch_xz)
        self.stretch_toolbar.addAction(self.action_stretch_xz)

        self.action_stretch_y = QAction("Stretch Y (Vertical)", self)
        self.action_stretch_y.setCheckable(True)
        self.action_stretch_y.triggered.connect(lambda: self._set_stretch_axis_mode("vertical"))
        self.stretch_mode_group.addAction(self.action_stretch_y)
        self.stretch_toolbar.addAction(self.action_stretch_y)

        self.action_stretch_depth = QAction("Stretch Depth", self)
        self.action_stretch_depth.setCheckable(True)
        self.action_stretch_depth.triggered.connect(lambda: self._set_stretch_axis_mode("depth"))
        self.stretch_mode_group.addAction(self.action_stretch_depth)
        self.stretch_toolbar.addAction(self.action_stretch_depth)

        self.stretch_toolbar.addSeparator()

        # Go button to execute the stretch
        self.action_stretch_go = QAction("Go!", self)
        self.action_stretch_go.triggered.connect(self._execute_stretch)
        self.stretch_toolbar.addAction(self.action_stretch_go)

        # Initially hide the stretch toolbar (only show when in stretch mode)
        self.stretch_toolbar.setVisible(False)

        # === Rotate mode options toolbar (new line) ===
        self.addToolBarBreak()
        self.rotate_toolbar = QToolBar("Rotate Options")
        self.rotate_toolbar.setMovable(False)
        self.addToolBar(self.rotate_toolbar)

        self.rotate_mode_group = QActionGroup(self)
        self.rotate_mode_group.setExclusive(True)

        self.action_rotate_xz = QAction("Rotate XZ (Normal)", self)
        self.action_rotate_xz.setCheckable(True)
        self.action_rotate_xz.setChecked(True)
        self.action_rotate_xz.triggered.connect(lambda: self._set_rotate_axis_mode("normal"))
        self.rotate_mode_group.addAction(self.action_rotate_xz)
        self.rotate_toolbar.addAction(self.action_rotate_xz)

        self.action_rotate_y = QAction("Rotate Y (Vertical)", self)
        self.action_rotate_y.setCheckable(True)
        self.action_rotate_y.triggered.connect(lambda: self._set_rotate_axis_mode("vertical"))
        self.rotate_mode_group.addAction(self.action_rotate_y)
        self.rotate_toolbar.addAction(self.action_rotate_y)

        self.rotate_toolbar.addSeparator()

        # Info label for rotate mode
        rotate_info = QLabel("  Click strand to select set, drag handle to set axis, click center to rotate")
        self.rotate_toolbar.addWidget(rotate_info)

        # Initially hide the rotate toolbar (only show when in rotate mode)
        self.rotate_toolbar.setVisible(False)

    def _setup_statusbar(self):
        """Setup the status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Mode label
        self.mode_label = QLabel("Mode: Select")
        self.statusbar.addWidget(self.mode_label)

        # Camera info label
        self.camera_label = QLabel("Camera: Ready")
        self.statusbar.addPermanentWidget(self.camera_label)

    def _connect_signals(self):
        """Connect signals between components"""
        # Canvas signals
        self.canvas.mode_changed.connect(self._on_mode_changed)
        self.canvas.camera_changed.connect(self._on_camera_changed)
        self.canvas.strand_created.connect(self._on_strand_created)
        self.canvas.strand_selected.connect(self._on_strand_selected)

        # Layer panel signals
        self.layer_panel.strand_selected.connect(self.canvas.select_strand_by_name)
        self.layer_panel.strand_visibility_changed.connect(self.canvas.set_strand_visibility)
        self.layer_panel.strand_color_changed.connect(self.canvas.set_strand_color)
        self.layer_panel.set_duplicate_requested.connect(self._on_set_duplicate_requested)
        self.layer_panel.set_rotate_requested.connect(self._on_set_rotate_requested)
        self.layer_panel.deselect_all_requested.connect(self.canvas.deselect_all)
        self.layer_panel.add_strand_requested.connect(lambda: self._set_mode("add_strand"))
        self.layer_panel.draw_names_requested.connect(self.canvas.toggle_name_drawing)

    def _apply_dark_theme(self):
        """Apply dark theme styling to the main window"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #252528;
            }
            QToolBar {
                background-color: #2D2D30;
                border: none;
                border-bottom: 1px solid #3E3E42;
                spacing: 2px;
                padding: 2px;
            }
            QToolBar::separator {
                background-color: #3E3E42;
                width: 1px;
                margin: 3px 4px;
            }
            QToolButton {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 3px 5px;
                color: #E8E8E8;
            }
            QToolButton:hover {
                background-color: #454548;
                border-color: #5A5A5D;
            }
            QToolButton:pressed {
                background-color: #2A2A2D;
            }
            QToolButton:checked {
                background-color: #3D3D50;
                border: 1px solid #7B68EE;
                color: #E8E8E8;
            }
            QToolButton:checked:hover {
                background-color: #4A4A60;
            }
            QStatusBar {
                background-color: #2D2D30;
                color: #A0A0A0;
                border-top: 1px solid #3E3E42;
            }
            QStatusBar QLabel {
                color: #A0A0A0;
                padding: 2px 8px;
            }
            QSplitter::handle {
                background-color: #3E3E42;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #7B68EE;
            }
            QMessageBox {
                background-color: #2D2D30;
                color: #E8E8E8;
            }
            QMessageBox QLabel {
                color: #E8E8E8;
            }
            QMessageBox QPushButton {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 6px 16px;
                color: #E8E8E8;
                min-width: 70px;
            }
            QMessageBox QPushButton:hover {
                background-color: #454548;
            }
            QMessageBox QPushButton:pressed {
                background-color: #2A2A2D;
            }
            QFileDialog {
                background-color: #2D2D30;
                color: #E8E8E8;
            }
        """)

    def _apply_button_styles(self):
        """Apply uniform Cool Teal elevated card style to all toolbar buttons"""

        bg = '#5B9EA6'          # Cool Teal
        text_color = '#FFFFFF'  # White text for contrast
        highlight = '#6BAEB6'   # Lighter teal (top/left edge)
        hover = '#65A8B0'       # Slightly brighter on hover
        shadow = '#3A7178'      # Darker teal (bottom/right edge)
        checked = '#4A8E96'     # Darker when checked/active
        pressed = '#3D7880'     # Darkest when pressed
        font = "Söhne, Inter, Segoe UI, sans-serif"

        style = f"""
            QToolButton {{
                background-color: {bg};
                border-top: 1px solid #6EB0B8;
                border-left: 1px solid #6EB0B8;
                border-right: 2px solid {shadow};
                border-bottom: 2px solid {shadow};
                border-radius: 6px;
                padding: 4px 6px;
                color: {text_color};
                font-family: {font};
                font-size: 11px;
                font-weight: 500;
            }}
            QToolButton:hover {{
                background-color: {hover};
                border-top: 1px solid #75B5BD;
                border-left: 1px solid #75B5BD;
                border-right: 2px solid {shadow};
                border-bottom: 2px solid {shadow};
            }}
            QToolButton:pressed {{
                background-color: {pressed};
                border-top: 2px solid {shadow};
                border-left: 2px solid {shadow};
                border-right: 1px solid #6EB0B8;
                border-bottom: 1px solid #6EB0B8;
                padding: 5px 5px 3px 7px;
            }}
            QToolButton:checked {{
                background-color: {checked};
                border-top: 2px solid {shadow};
                border-left: 2px solid {shadow};
                border-right: 1px solid #6EB0B8;
                border-bottom: 1px solid #6EB0B8;
                color: {text_color};
                padding: 5px 5px 3px 7px;
            }}
            QToolButton:checked:hover {{
                background-color: {hover};
            }}
        """

        # Apply to all toolbars
        for toolbar in [self.main_toolbar, self.move_toolbar, self.attach_toolbar,
                        self.stretch_toolbar, self.rotate_toolbar]:
            for action in toolbar.actions():
                widget = toolbar.widgetForAction(action)
                if widget:
                    widget.setStyleSheet(style)

    def _load_user_settings(self):
        """Load user settings and apply them to the UI"""
        settings = get_settings()

        # Load grid visibility
        show_grid = settings.get('show_grid', True)
        self.action_toggle_grid.setChecked(show_grid)
        self.canvas.set_grid_visible(show_grid)

        # Load axes visibility
        show_axes = settings.get('show_axes', True)
        self.action_toggle_axes.setChecked(show_axes)
        self.canvas.set_axes_visible(show_axes)

        # Load Link CPs setting
        link_cps = settings.get('link_control_points', False)
        self.action_link_cps.setChecked(link_cps)
        self.canvas.set_link_control_points(link_cps)

        # Load Edit All setting
        edit_all = settings.get('move_edit_all', False)
        self.action_edit_all.setChecked(edit_all)
        self.canvas.set_move_edit_all(edit_all)

    def _set_mode(self, mode: str):
        """Set the current interaction mode"""
        # Update action states
        for action in self.mode_actions:
            action.setChecked(False)

        if mode == "select":
            self.action_select.setChecked(True)
        elif mode == "add_strand":
            self.action_add_strand.setChecked(True)
        elif mode == "attach":
            self.action_attach.setChecked(True)
        elif mode == "move":
            self.action_move.setChecked(True)
        elif mode == "stretch":
            self.action_stretch.setChecked(True)
        elif mode == "rotate":
            self.action_rotate.setChecked(True)

        # Show/hide stretch toolbar based on mode
        self.stretch_toolbar.setVisible(mode == "stretch")

        # Show/hide rotate toolbar based on mode
        self.rotate_toolbar.setVisible(mode == "rotate")

        self.canvas.set_mode(mode)

    def _reset_camera(self):
        """Reset the camera to default position"""
        self.canvas.reset_camera()

    def _toggle_grid(self):
        """Toggle grid visibility"""
        visible = self.action_toggle_grid.isChecked()
        self.canvas.set_grid_visible(visible)
        # Save to user settings
        get_settings().set_and_save('show_grid', visible)

    def _toggle_axes(self):
        """Toggle axes visibility"""
        visible = self.action_toggle_axes.isChecked()
        self.canvas.set_axes_visible(visible)
        # Save to user settings
        get_settings().set_and_save('show_axes', visible)

    def _open_strand_profile_editor(self):
        """Open the strand profile editor dialog"""
        dialog = StrandProfileDialog(self.canvas, self)
        dialog.exec_()

    def _toggle_rigid_points(self):
        """Toggle rigid points (start/end spheres) visibility"""
        visible = self.action_rigid.isChecked()
        self.canvas.set_rigid_points_visible(visible)

    def _toggle_straight_mode(self):
        """Toggle straight segment mode (forces strands to be straight lines)"""
        enabled = self.action_straight.isChecked()
        self.canvas.set_straight_segment_mode(enabled)
        if enabled:
            self.statusbar.showMessage("Straight segment mode: ON - strands are now straight lines", 3000)
        else:
            self.statusbar.showMessage("Straight segment mode: OFF - curves restored", 3000)

    def _toggle_link_control_points(self):
        """Toggle linked control points at connections for smooth spline continuity"""
        enabled = self.action_link_cps.isChecked()
        self.canvas.set_link_control_points(enabled)
        # Save to user settings
        get_settings().set_and_save('link_control_points', enabled)
        if enabled:
            self.statusbar.showMessage("Link CPs: ON - connected control points sync for smooth spline", 3000)
        else:
            self.statusbar.showMessage("Link CPs: OFF - control points are independent", 3000)

    def _toggle_edit_all(self):
        """Toggle edit all mode - show and allow editing CPs for all strands"""
        enabled = self.action_edit_all.isChecked()
        self.canvas.set_move_edit_all(enabled)
        # Save to user settings
        get_settings().set_and_save('move_edit_all', enabled)
        if enabled:
            self.statusbar.showMessage("Edit All: ON - showing control points for all strands", 3000)
        else:
            self.statusbar.showMessage("Edit All: OFF - only selected strand's control points shown", 3000)

    def _activate_angle_adjust(self):
        """Activate angle/length adjust mode for the selected strand"""
        # Uncheck the button after click (it's a one-shot action, not a mode)
        self.action_angle_adjust.setChecked(False)

        # Check if a strand is selected
        if self.canvas.selected_strand is None:
            self.statusbar.showMessage("Please select a strand first", 3000)
            return

        # Activate angle adjust mode on the canvas
        self.canvas.activate_angle_adjust_mode(self.canvas.selected_strand)
        self.statusbar.showMessage("Adjusting angle and length...", 2000)

    def _set_move_axis_mode(self, mode: str):
        """Set the move axis mode and switch to move mode."""
        self.canvas.set_move_axis_mode(mode)
        self._set_mode("move")
        if mode == "normal":
            self.statusbar.showMessage("Move mode: XZ plane", 2000)
        elif mode == "vertical":
            self.statusbar.showMessage("Move mode: Y axis", 2000)
        elif mode == "depth":
            self.statusbar.showMessage("Move mode: Camera depth", 2000)
        elif mode == "along":
            self.statusbar.showMessage("Move mode: Along other point", 2000)

    def _set_attach_axis_mode(self, mode: str):
        """Set the attach axis mode and switch to attach mode."""
        self.canvas.set_attach_axis_mode(mode)
        self._set_mode("attach")
        if mode == "normal":
            self.statusbar.showMessage("Attach mode: XZ plane", 2000)
        elif mode == "vertical":
            self.statusbar.showMessage("Attach mode: Y axis", 2000)
        elif mode == "depth":
            self.statusbar.showMessage("Attach mode: Camera depth", 2000)
        elif mode == "along":
            self.statusbar.showMessage("Attach mode: Along other point", 2000)

    def _set_stretch_axis_mode(self, mode: str):
        """Set the stretch axis mode (for direction selection)."""
        self.canvas.set_stretch_axis_mode(mode)
        if mode == "normal":
            self.statusbar.showMessage("Stretch direction: XZ plane", 2000)
        elif mode == "vertical":
            self.statusbar.showMessage("Stretch direction: Y axis", 2000)
        elif mode == "depth":
            self.statusbar.showMessage("Stretch direction: Camera depth", 2000)

    def _execute_stretch(self):
        """Execute the stretch operation."""
        if self.canvas.execute_stretch():
            self.statusbar.showMessage("Stretch executed!", 2000)
        else:
            self.statusbar.showMessage("No endpoint/direction selected", 2000)

    def _set_rotate_axis_mode(self, mode: str):
        """Set the rotation axis mode (for axis direction selection)."""
        self.canvas.set_rotate_axis_mode(mode)
        if mode == "normal":
            self.statusbar.showMessage("Rotate axis: XZ plane (horizontal)", 2000)
        elif mode == "vertical":
            self.statusbar.showMessage("Rotate axis: Y axis (vertical)", 2000)

    def _on_mode_changed(self, mode: str):
        """Handle mode change from canvas"""
        self.mode_label.setText(f"Mode: {mode.replace('_', ' ').title()}")

    def _on_camera_changed(self, info: str):
        """Handle camera change updates"""
        self.camera_label.setText(f"Camera: {info}")

    def _on_strand_created(self, strand_name: str):
        """Handle new strand creation"""
        # Find the strand to get its actual color
        strand = next((s for s in self.canvas.strands if s.name == strand_name), None)
        color = strand.color if strand else (0.667, 0.667, 1.0, 1.0)
        self.layer_panel.add_strand(strand_name, color=color)
        self.statusbar.showMessage(f"Created strand: {strand_name}", 3000)

        # Automatically switch to attach mode after creating a new strand
        # This follows the pattern from OpenStrand 106
        self._set_mode("attach")

    def _on_strand_selected(self, strand_name: str):
        """Handle strand selection"""
        self.layer_panel.select_strand(strand_name)
        if strand_name:
            self.statusbar.showMessage(f"Selected: {strand_name}", 2000)

    def _on_set_duplicate_requested(self, set_number: str):
        """Handle duplication of a full strand set from the layer panel."""
        result = self.canvas.duplicate_set(set_number)
        if not result:
            return

        new_set_number, new_names = result
        for name in new_names:
            strand = next((s for s in self.canvas.strands if s.name == name), None)
            color = strand.color if strand else (0.667, 0.667, 1.0, 1.0)
            self.layer_panel.add_strand(name, color=color)

        self.statusbar.showMessage(
            f"Duplicated set {set_number} -> {new_set_number}",
            3000
        )

    def _on_set_rotate_requested(self, set_number: str):
        """Handle rotation of a full strand set from the layer panel."""
        # Switch to rotate mode and select the set
        self._set_mode("rotate")
        success = self.canvas.select_set_for_rotation(set_number)
        if success:
            self.statusbar.showMessage(
                f"Rotating set {set_number} - Drag handle to set axis, click center to rotate",
                5000
            )
        else:
            self.statusbar.showMessage(
                f"Could not select set {set_number} for rotation",
                3000
            )

    # ==================== Undo/Redo ====================

    def _undo(self):
        """Perform undo operation"""
        if self.undo_redo_manager.undo():
            self.statusbar.showMessage("Undo", 1500)

    def _redo(self):
        """Perform redo operation"""
        if self.undo_redo_manager.redo():
            self.statusbar.showMessage("Redo", 1500)

    def _update_undo_redo_actions(self):
        """Update undo/redo action enabled states"""
        self.action_undo.setEnabled(self.undo_redo_manager.can_undo())
        self.action_redo.setEnabled(self.undo_redo_manager.can_redo())

    def _on_undo_performed(self):
        """Handle undo completion - sync layer panel"""
        self.layer_panel.clear()
        for strand in self.canvas.strands:
            self.layer_panel.add_strand(strand.name, color=strand.color)

        # Update selection in layer panel
        if self.canvas.selected_strand:
            self.layer_panel.select_strand(self.canvas.selected_strand.name)

    def _on_redo_performed(self):
        """Handle redo completion - sync layer panel"""
        self.layer_panel.clear()
        for strand in self.canvas.strands:
            self.layer_panel.add_strand(strand.name, color=strand.color)

        # Update selection in layer panel
        if self.canvas.selected_strand:
            self.layer_panel.select_strand(self.canvas.selected_strand.name)

    # ==================== File Operations ====================

    def _new_project(self):
        """Create a new empty project"""
        # Ask for confirmation if there are strands
        if self.canvas.strands:
            reply = QMessageBox.question(
                self,
                "New Project",
                "This will clear the current project. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.canvas.clear_project()
        self.layer_panel.clear()
        self.undo_redo_manager.clear_history()
        self.current_project_file = None
        self.setWindowTitle("OpenStrandStudio 3D - New Project")
        self.statusbar.showMessage("New project created", 3000)

    def _save_project(self):
        """Save the project to a JSON file"""
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            self.current_project_file or "project.oss3d",
            "OpenStrandStudio 3D Files (*.oss3d);;JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Get project data from canvas
            project_data = self.canvas.get_project_data()

            # Write to file with nice formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2)

            self.current_project_file = file_path
            self.setWindowTitle(f"OpenStrandStudio 3D - {file_path.split('/')[-1].split(chr(92))[-1]}")
            self.statusbar.showMessage(f"Saved: {file_path}", 3000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save project:\n{str(e)}"
            )

    def _load_project(self):
        """Load a project from a JSON file"""
        # Ask for confirmation if there are strands
        if self.canvas.strands:
            reply = QMessageBox.question(
                self,
                "Load Project",
                "This will replace the current project. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project",
            "",
            "OpenStrandStudio 3D Files (*.oss3d);;JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Read project data
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Clear layer panel
            self.layer_panel.clear()

            # Load into canvas
            self.canvas.load_project_data(project_data)

            # Clear undo history (fresh start with loaded project)
            self.undo_redo_manager.clear_history()

            # Update layer panel with loaded strands
            for strand in self.canvas.strands:
                self.layer_panel.add_strand(strand.name, color=strand.color)

            self.current_project_file = file_path
            self.setWindowTitle(f"OpenStrandStudio 3D - {file_path.split('/')[-1].split(chr(92))[-1]}")
            self.statusbar.showMessage(f"Loaded: {file_path}", 3000)

        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Invalid JSON file:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load project:\n{str(e)}"
            )
