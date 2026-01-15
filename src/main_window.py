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


class MainWindow(QMainWindow):
    """Main application window for OpenStrandStudio 3D"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenStrandStudio 3D")
        self.setMinimumSize(1200, 800)

        # Initialize components
        self.canvas = None
        self.layer_panel = None

        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

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

        # Set initial sizes (canvas gets more space)
        splitter.setSizes([900, 300])

        main_layout.addWidget(splitter)

    def _setup_toolbar(self):
        """Setup the main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

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

        # === Mode selection ===
        # Select mode
        self.action_select = QAction("Select", self)
        self.action_select.setCheckable(True)
        self.action_select.setChecked(True)
        self.action_select.triggered.connect(lambda: self._set_mode("select"))
        toolbar.addAction(self.action_select)

        # Add strand mode
        self.action_add_strand = QAction("Add Strand", self)
        self.action_add_strand.setCheckable(True)
        self.action_add_strand.triggered.connect(lambda: self._set_mode("add_strand"))
        toolbar.addAction(self.action_add_strand)

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
        self.action_reset_camera = QAction("Reset Camera", self)
        self.action_reset_camera.triggered.connect(self._reset_camera)
        toolbar.addAction(self.action_reset_camera)

        # Toggle grid/axes
        self.action_toggle_grid = QAction("Grid/Axes", self)
        self.action_toggle_grid.setCheckable(True)
        self.action_toggle_grid.setChecked(True)
        self.action_toggle_grid.setShortcut("G")
        self.action_toggle_grid.triggered.connect(self._toggle_grid_axes)
        toolbar.addAction(self.action_toggle_grid)

        # Group actions for exclusive selection
        self.mode_actions = [
            self.action_select,
            self.action_add_strand,
            self.action_attach,
            self.action_move
        ]

        # Track current project file
        self.current_project_file = None

        # === Move mode options toolbar (new line) ===
        self.addToolBarBreak()
        move_toolbar = QToolBar("Move Options")
        move_toolbar.setMovable(False)
        self.addToolBar(move_toolbar)

        self.move_mode_group = QActionGroup(self)
        self.move_mode_group.setExclusive(True)

        self.action_move_xz = QAction("Move XZ (Normal)", self)
        self.action_move_xz.setCheckable(True)
        self.action_move_xz.setChecked(True)
        self.action_move_xz.triggered.connect(lambda: self._set_move_axis_mode("normal"))
        self.move_mode_group.addAction(self.action_move_xz)
        move_toolbar.addAction(self.action_move_xz)

        self.action_move_y = QAction("Move Y (Shift)", self)
        self.action_move_y.setCheckable(True)
        self.action_move_y.triggered.connect(lambda: self._set_move_axis_mode("vertical"))
        self.move_mode_group.addAction(self.action_move_y)
        move_toolbar.addAction(self.action_move_y)

        self.action_move_depth = QAction("Move Depth (Ctrl)", self)
        self.action_move_depth.setCheckable(True)
        self.action_move_depth.triggered.connect(lambda: self._set_move_axis_mode("depth"))
        self.move_mode_group.addAction(self.action_move_depth)
        move_toolbar.addAction(self.action_move_depth)

        # === Attach mode options toolbar (new line) ===
        self.addToolBarBreak()
        attach_toolbar = QToolBar("Attach Options")
        attach_toolbar.setMovable(False)
        self.addToolBar(attach_toolbar)

        self.attach_mode_group = QActionGroup(self)
        self.attach_mode_group.setExclusive(True)

        self.action_attach_xz = QAction("Attach XZ (Normal)", self)
        self.action_attach_xz.setCheckable(True)
        self.action_attach_xz.setChecked(True)
        self.action_attach_xz.triggered.connect(lambda: self._set_attach_axis_mode("normal"))
        self.attach_mode_group.addAction(self.action_attach_xz)
        attach_toolbar.addAction(self.action_attach_xz)

        self.action_attach_y = QAction("Attach Y (Shift)", self)
        self.action_attach_y.setCheckable(True)
        self.action_attach_y.triggered.connect(lambda: self._set_attach_axis_mode("vertical"))
        self.attach_mode_group.addAction(self.action_attach_y)
        attach_toolbar.addAction(self.action_attach_y)

        self.action_attach_depth = QAction("Attach Depth (Ctrl)", self)
        self.action_attach_depth.setCheckable(True)
        self.action_attach_depth.triggered.connect(lambda: self._set_attach_axis_mode("depth"))
        self.attach_mode_group.addAction(self.action_attach_depth)
        attach_toolbar.addAction(self.action_attach_depth)

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
        self.layer_panel.deselect_all_requested.connect(self.canvas.deselect_all)

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

        self.canvas.set_mode(mode)

    def _reset_camera(self):
        """Reset the camera to default position"""
        self.canvas.reset_camera()

    def _toggle_grid_axes(self):
        """Toggle grid and axes visibility"""
        visible = self.action_toggle_grid.isChecked()
        self.canvas.set_grid_axes_visible(visible)

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

    def _on_mode_changed(self, mode: str):
        """Handle mode change from canvas"""
        self.mode_label.setText(f"Mode: {mode.replace('_', ' ').title()}")

    def _on_camera_changed(self, info: str):
        """Handle camera change updates"""
        self.camera_label.setText(f"Camera: {info}")

    def _on_strand_created(self, strand_name: str):
        """Handle new strand creation"""
        self.layer_panel.add_strand(strand_name)
        self.statusbar.showMessage(f"Created strand: {strand_name}", 3000)

    def _on_strand_selected(self, strand_name: str):
        """Handle strand selection"""
        self.layer_panel.select_strand(strand_name)
        if strand_name:
            self.statusbar.showMessage(f"Selected: {strand_name}", 2000)

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

            # Update layer panel with loaded strands
            for strand in self.canvas.strands:
                self.layer_panel.add_strand(strand.name)

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
