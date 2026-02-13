"""
OpenStrandStudio 3D - Main Window
Contains the main application window with canvas and layer panel
"""

import ctypes
import sys

if sys.platform.startswith("win"):
    from ctypes import wintypes

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QToolBar, QAction, QStatusBar, QSplitter, QLabel,
    QMessageBox, QActionGroup, QPushButton, QCheckBox,
    QDialog, QDialogButtonBox, QApplication
)
from PyQt5.QtCore import Qt, QEvent, QPoint
from PyQt5.QtGui import QPixmap

from custom_title_bar import CustomTitleBar
from strand_drawing_canvas import StrandDrawingCanvas
from layer_panel import LayerPanel
from undo_redo_manager import UndoRedoManager
from strand_profile_dialog import StrandProfileDialog
from user_settings import get_settings
from save_project import SaveProjectMixin
from load_project import LoadProjectMixin
from load_points import LoadPointsMixin
from export_points import ExportPointsMixin

if sys.platform.startswith("win"):
    WM_NCHITTEST = 0x0084
    HTCLIENT = 1
    HTCAPTION = 2
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOM = 15
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17


class MainWindow(QMainWindow, SaveProjectMixin, LoadProjectMixin, LoadPointsMixin, ExportPointsMixin):
    """Main application window for OpenStrandStudio 3D"""

    def __init__(self):
        super().__init__()
        self._use_custom_title_bar = sys.platform.startswith("win")
        self._custom_title_bar = None
        self._resize_border_thickness = 8

        if self._use_custom_title_bar:
            self.setWindowFlags(
                Qt.Window |
                Qt.FramelessWindowHint |
                Qt.WindowSystemMenuHint |
                Qt.WindowMinMaxButtonsHint |
                Qt.WindowCloseButtonHint
            )

        self.setWindowTitle("OpenStrandStudio 3D")
        self.setMinimumSize(900, 600)
        app = QApplication.instance()
        if app and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())

        # Initialize components
        self.canvas = None
        self.layer_panel = None
        self.undo_redo_manager = None
        self.layer_state_manager = None

        self._setup_ui()
        self._setup_undo_redo()
        self._setup_layer_state_manager()
        self._setup_toolbar()
        self._setup_custom_title_bar()
        self._setup_statusbar()
        self._connect_signals()
        self._apply_dark_theme()
        self._load_user_settings()

    def _setup_custom_title_bar(self):
        """Install a custom title bar on Windows so title/icon can be larger."""
        if not self._use_custom_title_bar:
            return

        self._custom_title_bar = CustomTitleBar(self)
        self.setMenuWidget(self._custom_title_bar)
        self._update_custom_title_bar_state()

    def _update_custom_title_bar_state(self):
        if self._custom_title_bar:
            self._custom_title_bar.update_window_state(self.isMaximized())

    def showEvent(self, event):
        super().showEvent(event)
        self._update_custom_title_bar_state()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._update_custom_title_bar_state()

    def nativeEvent(self, eventType, message):
        """Windows hit-test handling for frameless drag and resize."""
        if not self._use_custom_title_bar:
            return super().nativeEvent(eventType, message)

        event_name = bytes(eventType)
        if event_name != b"windows_generic_MSG":
            return super().nativeEvent(eventType, message)

        msg = wintypes.MSG.from_address(int(message))
        if msg.message != WM_NCHITTEST:
            return super().nativeEvent(eventType, message)

        x_pos = ctypes.c_short(msg.lParam & 0xFFFF).value
        y_pos = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
        global_pos = QPoint(x_pos, y_pos)

        frame = self.frameGeometry()

        # Let Windows resize the frameless window from edges/corners.
        if not self.isMaximized():
            border = self._resize_border_thickness
            on_left = frame.left() <= x_pos < frame.left() + border
            on_right = frame.right() - border < x_pos <= frame.right()
            on_top = frame.top() <= y_pos < frame.top() + border
            on_bottom = frame.bottom() - border < y_pos <= frame.bottom()

            if on_top and on_left:
                return True, HTTOPLEFT
            if on_top and on_right:
                return True, HTTOPRIGHT
            if on_bottom and on_left:
                return True, HTBOTTOMLEFT
            if on_bottom and on_right:
                return True, HTBOTTOMRIGHT
            if on_left:
                return True, HTLEFT
            if on_right:
                return True, HTRIGHT
            if on_top:
                return True, HTTOP
            if on_bottom:
                return True, HTBOTTOM

        # Drag from the custom title bar (except window control buttons).
        if self._custom_title_bar and self._custom_title_bar.is_drag_region(global_pos):
            return True, HTCAPTION

        return True, HTCLIENT

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

    def _setup_layer_state_manager(self):
        """Setup the layer state manager after canvas and layer panel are created."""
        from layer_state_manager import LayerStateManager

        self.layer_state_manager = LayerStateManager(self.canvas)
        self.layer_state_manager.set_layer_panel(self.layer_panel)

        # Store reference on canvas for easy access from mode mixins
        self.canvas.layer_state_manager = self.layer_state_manager

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

        self.action_load_points = QAction("Load Points", self)
        self.action_load_points.setShortcut("Ctrl+Shift+O")
        self.action_load_points.triggered.connect(self._load_points)
        toolbar.addAction(self.action_load_points)

        self.action_export_points = QAction("Export Points", self)
        self.action_export_points.setShortcut("Ctrl+Shift+E")
        self.action_export_points.triggered.connect(self._export_points)
        toolbar.addAction(self.action_export_points)

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
        # View mode (camera navigation only, no editing)
        self.action_view = QAction("View", self)
        self.action_view.setCheckable(True)
        self.action_view.setChecked(True)  # Default mode
        self.action_view.triggered.connect(lambda: self._set_mode("view"))
        toolbar.addAction(self.action_view)

        # Select mode
        self.action_select = QAction("Select", self)
        self.action_select.setCheckable(True)
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

        toolbar.addSeparator()

        # State Layer Manager debug button
        self.action_state_viewer = QAction("State Layer Manager", self)
        self.action_state_viewer.triggered.connect(self._show_state_layer_manager_dialog)
        toolbar.addAction(self.action_state_viewer)

        toolbar.addSeparator()

        # Settings button
        self.action_settings = QAction("Settings", self)
        self.action_settings.triggered.connect(self._show_settings_dialog)
        toolbar.addAction(self.action_settings)

        # About button
        self.action_about = QAction("About", self)
        self.action_about.triggered.connect(self._show_about_dialog)
        toolbar.addAction(self.action_about)

        # Group actions for exclusive selection
        self.mode_actions = [
            self.action_view,
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
        self._last_load_strand_length = 0.5
        self._original_segment_lengths = []  # per-strand original lengths from loaded points

        # === Mode-specific toolbars (all on the same row to avoid layout pop) ===
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

        # === Attach mode options toolbar (same row) ===
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

        # === Stretch mode options toolbar (same row) ===
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

        # === Rotate mode options toolbar (same row) ===
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
        self.canvas.strand_deleted.connect(self._on_strand_deleted)

        # Layer panel signals
        self.layer_panel.strand_selected.connect(self.canvas.select_strand_by_name)
        self.layer_panel.strand_visibility_changed.connect(self.canvas.set_strand_visibility)
        self.layer_panel.strand_color_changed.connect(self.canvas.set_strand_color)
        self.layer_panel.strand_delete_requested.connect(self._on_strand_delete_requested)
        self.layer_panel.set_duplicate_requested.connect(self._on_set_duplicate_requested)
        self.layer_panel.set_rotate_requested.connect(self._on_set_rotate_requested)
        self.layer_panel.deselect_all_requested.connect(self.canvas.deselect_all)
        self.layer_panel.add_strand_requested.connect(self._enter_add_strand_mode)
        self.layer_panel.draw_names_requested.connect(self.canvas.toggle_name_drawing)

    def _apply_dark_theme(self):
        """Apply dark theme styling to the main window"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #252528;
            }
            #CustomTitleBar {
                background-color: #2D2D30;
                border-bottom: 1px solid #3E3E42;
            }
            #WindowTitleLabel {
                color: #E8E8E8;
                font-size: 15px;
                font-weight: 600;
            }
            QToolButton#WindowControlButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #E8E8E8;
            }
            QToolButton#WindowControlButton:hover {
                background-color: #454548;
            }
            QToolButton#WindowControlButton:pressed {
                background-color: #2A2A2D;
            }
            QToolButton#WindowCloseButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #E8E8E8;
            }
            QToolButton#WindowCloseButton:hover {
                background-color: #C42B1C;
                color: #FFFFFF;
            }
            QToolButton#WindowCloseButton:pressed {
                background-color: #A12316;
                color: #FFFFFF;
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
            QInputDialog {
                background-color: #2D2D30;
                color: #E8E8E8;
                min-width: 350px;
            }
            QInputDialog QLabel {
                color: #E8E8E8;
                font-size: 18px;
            }
            QInputDialog QPushButton {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 8px 22px;
                color: #E8E8E8;
                font-size: 15px;
                font-weight: 500;
                min-width: 98px;
            }
            QInputDialog QPushButton:hover {
                background-color: #454548;
                border-color: #5A5A5D;
            }
            QInputDialog QPushButton:pressed {
                background-color: #2A2A2D;
            }
            QInputDialog QDoubleSpinBox {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 6px 11px;
                color: #E8E8E8;
                font-size: 17px;
            }
            QInputDialog QDoubleSpinBox::up-button,
            QInputDialog QDoubleSpinBox::down-button {
                background-color: #454548;
                border: 1px solid #3E3E42;
                width: 22px;
            }
            QInputDialog QDoubleSpinBox::up-button:hover,
            QInputDialog QDoubleSpinBox::down-button:hover {
                background-color: #5A5A5D;
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

        # Load toolbar visibility and layout
        always_show = settings.get('always_show_move_attach_toolbars', False)
        self._apply_toolbar_layout(always_show)
        # Apply initial visibility (no mode active yet → view)
        self.move_toolbar.setVisible(always_show)
        self.attach_toolbar.setVisible(always_show)

    def _apply_toolbar_layout(self, always_show):
        """Insert or remove toolbar breaks depending on the always-show setting.

        always_show ON  → Move on row 1, Attach on row 2, Stretch/Rotate on row 3
        always_show OFF → all four share a single row (only one visible at a time)
        """
        if always_show:
            # Put attach and stretch on their own rows
            self.insertToolBarBreak(self.attach_toolbar)
            self.insertToolBarBreak(self.stretch_toolbar)
        else:
            # Collapse all onto the same row
            self.removeToolBarBreak(self.attach_toolbar)
            self.removeToolBarBreak(self.stretch_toolbar)

    def _set_mode(self, mode: str):
        """Set the current interaction mode"""
        # Update action states
        for action in self.mode_actions:
            action.setChecked(False)

        if mode == "select":
            self.action_select.setChecked(True)
        elif mode == "view":
            self.action_view.setChecked(True)
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

        # Freeze repaints so all toolbar show/hide happens in one frame (no flicker)
        self.setUpdatesEnabled(False)

        always_show = get_settings().get('always_show_move_attach_toolbars', False)
        self.move_toolbar.setVisible(mode == "move" or always_show)
        self.attach_toolbar.setVisible(mode == "attach" or always_show)
        self.stretch_toolbar.setVisible(mode == "stretch")
        self.rotate_toolbar.setVisible(mode == "rotate")

        self.setUpdatesEnabled(True)

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

    def _enter_add_strand_mode(self):
        """Save current mode and enter add_strand mode without hiding toolbars."""
        self._mode_before_add_strand = self.canvas.current_mode
        # Only change the canvas mode — keep toolbars as they are
        self.canvas.set_mode("add_strand")

    def _on_strand_created(self, strand_name: str):
        """Handle new strand creation"""
        # Find the strand to get its actual color
        strand = next((s for s in self.canvas.strands if s.name == strand_name), None)
        color = strand.color if strand else (0.667, 0.667, 1.0, 1.0)
        self.layer_panel.add_strand(strand_name, color=color)
        self.layer_panel.update_layer_button_states(self.canvas)
        self.statusbar.showMessage(f"Created strand: {strand_name}", 3000)

        # Restore the mode only if we came from the "New" button (add_strand mode).
        # Otherwise (e.g. attach mode created a strand), keep the current mode.
        prev = getattr(self, '_mode_before_add_strand', None)
        if prev is not None:
            self._mode_before_add_strand = None
            # Only change the canvas mode — toolbars were never hidden
            self.canvas.set_mode(prev)

    def _on_strand_deleted(self, strand_name: str):
        """Handle strand deletion"""
        self.layer_panel.remove_strand(strand_name)
        self.layer_panel.update_layer_button_states(self.canvas)

    def _on_strand_delete_requested(self, strand_name: str):
        """Handle delete request from layer panel context menu."""
        strand = next((s for s in self.canvas.strands if s.name == strand_name), None)
        if strand and strand.is_deletable():
            self.canvas.selected_strand = strand
            self.canvas._delete_selected_strand()

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

        self.layer_panel.update_layer_button_states(self.canvas)
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

        self.layer_panel.update_layer_button_states(self.canvas)

        # Update layer state manager
        if self.layer_state_manager:
            self.layer_state_manager.save_current_state()

    def _on_redo_performed(self):
        """Handle redo completion - sync layer panel"""
        self.layer_panel.clear()
        for strand in self.canvas.strands:
            self.layer_panel.add_strand(strand.name, color=strand.color)

        # Update selection in layer panel
        if self.canvas.selected_strand:
            self.layer_panel.select_strand(self.canvas.selected_strand.name)

        self.layer_panel.update_layer_button_states(self.canvas)

        # Update layer state manager
        if self.layer_state_manager:
            self.layer_state_manager.save_current_state()

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
        if self.layer_state_manager:
            self.layer_state_manager.save_current_state()
        self.current_project_file = None
        self.setWindowTitle("OpenStrandStudio 3D - New Project")
        self.statusbar.showMessage("New project created", 3000)

    # Save/Load/Points methods provided by mixins:
    # SaveProjectMixin (save_project.py), LoadProjectMixin (load_project.py),
    # LoadPointsMixin (load_points.py), ExportPointsMixin (export_points.py)

    def _show_state_layer_manager_dialog(self):
        """Show a dialog with all LayerStateManager state details."""
        from PyQt5.QtWidgets import QTextEdit
        from attached_strand import AttachedStrand

        dlg = QDialog(self)
        dlg.setWindowTitle("State Layer Manager - Full State View")
        dlg.setMinimumSize(700, 600)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(10, 10, 10, 10)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet(
            "QTextEdit { background: #1e1e2e; color: #cdd6f4; "
            "font-family: Consolas, monospace; font-size: 12px; }"
        )
        layout.addWidget(text_edit)

        # Refresh button + close button
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        close_btn = QPushButton("Close")
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        close_btn.clicked.connect(dlg.accept)

        def build_report():
            lines = []
            lsm = self.layer_state_manager
            canvas = self.canvas

            lines.append("=" * 60)
            lines.append("  STATE LAYER MANAGER - FULL REPORT")
            lines.append("=" * 60)

            # --- Overview ---
            lines.append("")
            lines.append("--- OVERVIEW ---")
            total = len(canvas.strands) if canvas else 0
            base_count = sum(1 for s in canvas.strands if not isinstance(s, AttachedStrand)) if canvas else 0
            attached_count = total - base_count
            lines.append(f"Total strands:      {total}")
            lines.append(f"  Base strands:     {base_count}")
            lines.append(f"  Attached strands: {attached_count}")
            lines.append(f"Movement in progress: {lsm.movement_in_progress if lsm else 'N/A'}")

            # --- Undo/Redo ---
            lines.append("")
            lines.append("--- UNDO / REDO ---")
            urm = self.undo_redo_manager
            if urm:
                lines.append(f"Undo stack size:  {len(urm.undo_stack)}")
                lines.append(f"Redo stack size:  {len(urm.redo_stack)}")
                lines.append(f"Can undo:         {urm.can_undo()}")
                lines.append(f"Can redo:         {urm.can_redo()}")
                lines.append(f"Max history:      {urm.max_history}")
                lines.append(f"Is restoring:     {urm._is_restoring}")
            else:
                lines.append("UndoRedoManager: not initialized")

            if not lsm:
                lines.append("\nLayerStateManager: not initialized")
                return "\n".join(lines)

            # Force a fresh state capture
            lsm.save_current_state()
            state = lsm.layer_state

            # --- Order (set numbers) ---
            lines.append("")
            lines.append("--- ORDER (set numbers) ---")
            order = state.get('order', [])
            lines.append(f"Sets: {order if order else '(none)'}")

            # --- Selected / Newest ---
            lines.append("")
            lines.append("--- SELECTION ---")
            lines.append(f"Selected strand:  {state.get('selected_strand', 'None')}")
            lines.append(f"Newest strand:    {state.get('newest_strand', 'None')}")
            lines.append(f"Newest layer:     {state.get('newest_layer', 'None')}")

            # --- Connections ---
            lines.append("")
            lines.append("--- CONNECTIONS ---")
            connections = state.get('connections', {})
            if connections:
                max_name = max(len(n) for n in connections) if connections else 0
                for name, conn in sorted(connections.items()):
                    start_c = conn[0] if isinstance(conn, list) and len(conn) > 0 else '?'
                    end_c = conn[1] if isinstance(conn, list) and len(conn) > 1 else '?'
                    lines.append(f"  {name:<{max_name}}  start: {start_c:<15} end: {end_c}")
            else:
                lines.append("  (no connections)")

            # --- Positions ---
            lines.append("")
            lines.append("--- POSITIONS ---")
            positions = state.get('positions', {})
            if positions:
                for name, pos in sorted(positions.items()):
                    if isinstance(pos, (list, tuple)) and len(pos) == 6:
                        sx, sy, sz, ex, ey, ez = pos
                        lines.append(
                            f"  {name}  start:({sx:+.3f}, {sy:+.3f}, {sz:+.3f})  "
                            f"end:({ex:+.3f}, {ey:+.3f}, {ez:+.3f})"
                        )
                    else:
                        lines.append(f"  {name}  {pos}")
            else:
                lines.append("  (no positions)")

            # --- Colors ---
            lines.append("")
            lines.append("--- COLORS ---")
            colors = state.get('colors', {})
            if colors:
                for name, color in sorted(colors.items()):
                    if isinstance(color, (list, tuple)) and len(color) >= 3:
                        r, g, b = color[0], color[1], color[2]
                        a = color[3] if len(color) > 3 else 1.0
                        lines.append(f"  {name}  RGBA({r:.3f}, {g:.3f}, {b:.3f}, {a:.3f})")
                    else:
                        lines.append(f"  {name}  {color}")
            else:
                lines.append("  (no colors)")

            # --- Per-Strand Details ---
            lines.append("")
            lines.append("--- PER-STRAND DETAILS ---")
            if canvas and canvas.strands:
                for strand in canvas.strands:
                    is_attached = isinstance(strand, AttachedStrand)
                    stype = "AttachedStrand" if is_attached else "Strand"
                    lines.append(f"")
                    lines.append(f"  [{strand.name}] ({stype})")
                    lines.append(f"    visible:    {strand.visible}")
                    lines.append(f"    width:      {strand.width:.4f}")
                    lines.append(f"    height_r:   {strand.height_ratio:.4f}")
                    lines.append(f"    shape:      {getattr(strand, 'cross_section_shape', 'ellipse')}")
                    lines.append(f"    corner_r:   {getattr(strand, 'corner_radius', 0.0):.4f}")
                    lines.append(f"    twist:      start={strand.start_twist:.1f}  end={strand.end_twist:.1f}  cp1={strand.cp1_twist:.1f}  cp2={strand.cp2_twist:.1f}")
                    if is_attached:
                        parent_name = strand.parent_strand.name if strand.parent_strand else "None"
                        lines.append(f"    parent:     {parent_name}")
                        lines.append(f"    attach_side: {strand.attachment_side}")
                    children = [c.name for c in strand.attached_strands] if strand.attached_strands else []
                    if children:
                        lines.append(f"    children:   {children}")
                    # Connection fields
                    sc = strand.start_connection
                    ec = strand.end_connection
                    sc_str = f"{sc['strand'].name}({sc['end']})" if sc else "None"
                    ec_str = f"{ec['strand'].name}({ec['end']})" if ec else "None"
                    lines.append(f"    start_conn: {sc_str}")
                    lines.append(f"    end_conn:   {ec_str}")
            else:
                lines.append("  (no strands)")

            # --- Cached Connections (movement) ---
            lines.append("")
            lines.append("--- CACHED CONNECTIONS (movement) ---")
            if lsm.cached_connections:
                for name, conn in sorted(lsm.cached_connections.items()):
                    lines.append(f"  {name}: {conn}")
            else:
                lines.append("  (none - no movement in progress)")

            lines.append("")
            lines.append("=" * 60)
            return "\n".join(lines)

        def refresh():
            text_edit.setPlainText(build_report())

        refresh_btn.clicked.connect(refresh)
        refresh()  # Initial load

        dlg.exec_()

    def _show_settings_dialog(self):
        """Show the Settings dialog"""
        settings = get_settings()
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setFixedWidth(400)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #7B68EE;")
        layout.addWidget(title)

        layout.addSpacing(4)

        # --- Toolbar visibility section ---
        section_label = QLabel("Toolbar Visibility")
        section_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #C0C0C0;")
        layout.addWidget(section_label)

        cb_always_show = QCheckBox("Always show Move / Attach toolbars")
        cb_always_show.setChecked(settings.get('always_show_move_attach_toolbars', False))
        cb_always_show.setStyleSheet("color: #E8E8E8; font-size: 12px;")
        cb_always_show.setToolTip(
            "When OFF, the Move and Attach option bars only appear\n"
            "when you activate Move or Attach mode.\n"
            "When ON, they are always visible in the main window."
        )
        layout.addWidget(cb_always_show)

        hint = QLabel(
            "When off, the Move/Attach option bars (XZ, Y, Depth, Along)\n"
            "only appear when you click the Move or Attach button."
        )
        hint.setStyleSheet("color: #808080; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)

        dialog_button_style = """
            QPushButton {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 4px 14px;
                color: #E8E8E8;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #454548;
                border-color: #5A5A5D;
            }
            QPushButton:pressed {
                background-color: #2A2A2D;
            }
        """
        for role in (QDialogButtonBox.Ok, QDialogButtonBox.Cancel):
            button = btn_box.button(role)
            if button:
                button.setStyleSheet(dialog_button_style)

        dlg.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #5A5A5D;
                border-radius: 3px;
                background-color: #353538;
            }
            QCheckBox::indicator:checked {
                background-color: #7B68EE;
                border-color: #7B68EE;
            }
        """)

        if dlg.exec_() == QDialog.Accepted:
            always_show = cb_always_show.isChecked()
            settings.set_and_save('always_show_move_attach_toolbars', always_show)

            # Apply layout (separate rows vs single row) and visibility
            self._apply_toolbar_layout(always_show)
            current_mode = getattr(self.canvas, 'current_mode', 'view')
            self.move_toolbar.setVisible(current_mode == "move" or always_show)
            self.attach_toolbar.setVisible(current_mode == "attach" or always_show)

    def _show_about_dialog(self):
        """Show the About dialog with version and credits"""
        import os
        dlg = QDialog(self)
        dlg.setWindowTitle("About OpenStrandStudio 3D")
        dlg.setFixedSize(520, 460)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(30, 25, 30, 20)
        layout.setSpacing(8)

        # Show the app icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "openstrandstudio3d_icon.png")
        if os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(icon_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
            layout.addWidget(icon_label)

        title = QLabel("OpenStrandStudio 3D")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #7B68EE;")
        layout.addWidget(title)

        version_label = QLabel("Version 1.00")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("font-size: 15px; color: #C0C0C0;")
        layout.addWidget(version_label)

        layout.addSpacing(6)

        info = QLabel()
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        info.setTextFormat(Qt.RichText)
        info.setText(
            '<p style="font-size:13px; color:#E8E8E8;">'
            'Based on the original <b>OpenStrand Studio</b>.'
            '</p>'
            '<p style="font-size:13px; color:#E8E8E8;">'
            'OpenStrand Studio was developed by <b>Yonatan Setbon</b>. '
            'The software is designed to create any knot in a diagrammatic way '
            'by using layers for each section of a strand and incorporating '
            'masked layers that allow for an "over-under effect."'
            '</p>'
            '<p style="font-size:13px; color:#E8E8E8;">'
            'Yonatan runs a YouTube channel dedicated to lanyards called '
            '<b><a href="https://www.youtube.com/@1anya7d" style="color:#7B68EE;">LanYarD</a></b>, '
            'where many tutorials feature diagrams of knots. This software was '
            'created to facilitate designing any knot, in order to demonstrate '
            'and explain how to make complex tutorials involving knot tying.'
            '</p>'
            '<p style="font-size:13px; color:#E8E8E8;">'
            'Contact: <a href="mailto:ysetbon@gmail.com" style="color:#7B68EE;">ysetbon@gmail.com</a>'
            ' &nbsp;|&nbsp; '
            '<a href="https://www.instagram.com/ysetbon/" style="color:#7B68EE;">Instagram</a>'
            ' &nbsp;|&nbsp; '
            '<a href="https://www.linkedin.com/in/yonatan-setbon-4a980986/" style="color:#7B68EE;">LinkedIn</a>'
            '</p>'
            '<p style="font-size:12px; color:#A0A0A0;">'
            '\u00a9 2026 OpenStrand Studio'
            '</p>'
        )
        layout.addWidget(info)

        layout.addStretch()

        ok_btn = QDialogButtonBox(QDialogButtonBox.Ok)
        ok_btn.accepted.connect(dlg.accept)
        layout.addWidget(ok_btn)

        dialog_button_style = """
            QPushButton {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 4px 14px;
                color: #E8E8E8;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #454548;
                border-color: #5A5A5D;
            }
            QPushButton:pressed {
                background-color: #2A2A2D;
            }
        """
        ok_button = ok_btn.button(QDialogButtonBox.Ok)
        if ok_button:
            ok_button.setStyleSheet(dialog_button_style)

        dlg.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
            }
            QLabel a {
                color: #7B68EE;
            }
        """)

        dlg.exec_()
