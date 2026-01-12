"""
OpenStrandStudio 3D - Main Window
Contains the main application window with canvas and layer panel
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QToolBar, QAction, QStatusBar, QSplitter, QLabel
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

        # Reset camera
        self.action_reset_camera = QAction("Reset Camera", self)
        self.action_reset_camera.triggered.connect(self._reset_camera)
        toolbar.addAction(self.action_reset_camera)

        # Group actions for exclusive selection
        self.mode_actions = [
            self.action_select,
            self.action_add_strand,
            self.action_attach,
            self.action_move
        ]

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
