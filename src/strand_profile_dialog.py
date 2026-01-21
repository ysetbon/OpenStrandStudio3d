"""
OpenStrandStudio 3D - Strand Profile Dialog
Dialog for editing strand cross-section shape and dimensions
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QDoubleSpinBox, QGroupBox,
    QPushButton, QWidget, QSlider, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath


class CrossSectionPreview(QWidget):
    """Widget to preview the cross-section shape"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.setMaximumSize(200, 200)

        # Shape parameters (use strand_ prefix to avoid Qt method conflicts)
        self.shape = "ellipse"
        self.strand_width = 1.0
        self.height_ratio = 0.4
        self.corner_radius = 0.0

    def set_shape(self, shape):
        self.shape = shape
        self.update()

    def set_width(self, width):
        self.strand_width = width
        self.update()

    def set_height_ratio(self, ratio):
        self.height_ratio = ratio
        self.update()

    def set_corner_radius(self, radius):
        self.corner_radius = radius
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(50, 50, 55))

        # Draw simple 2x2 grid
        painter.setPen(QPen(QColor(70, 70, 75), 1))
        widget_w, widget_h = self.width(), self.height()
        cx, cy = widget_w // 2, widget_h // 2
        # Vertical center line
        painter.drawLine(cx, 0, cx, widget_h)
        # Horizontal center line
        painter.drawLine(0, cy, widget_w, cy)

        # Calculate shape dimensions in pixels
        # Scale to fill most of the preview area (use 60% of widget size)
        max_dim = min(widget_w, widget_h) * 0.6
        w = max_dim
        h = max_dim * self.height_ratio

        # Draw the cross-section shape
        painter.setPen(QPen(QColor(255, 180, 100), 2))
        painter.setBrush(QBrush(QColor(230, 140, 50, 180)))

        if self.shape == "ellipse":
            painter.drawEllipse(int(cx - w/2), int(cy - h/2), int(w), int(h))

        elif self.shape == "rectangle":
            # Rectangle with optional rounded corners
            corner = self.corner_radius * min(w, h) / 2
            path = QPainterPath()
            path.addRoundedRect(cx - w/2, cy - h/2, w, h, corner, corner)
            painter.drawPath(path)

        elif self.shape == "circle":
            # Circle uses the smaller dimension
            diameter = min(w, h)
            painter.drawEllipse(int(cx - diameter/2), int(cy - diameter/2),
                              int(diameter), int(diameter))

        elif self.shape == "diamond":
            # Diamond/rhombus shape
            path = QPainterPath()
            path.moveTo(cx, cy - h/2)  # Top
            path.lineTo(cx + w/2, cy)  # Right
            path.lineTo(cx, cy + h/2)  # Bottom
            path.lineTo(cx - w/2, cy)  # Left
            path.closeSubpath()
            painter.drawPath(path)

        elif self.shape == "hexagon":
            # Hexagonal cross-section
            import math
            path = QPainterPath()
            for i in range(6):
                angle = math.pi / 6 + i * math.pi / 3
                x = cx + w/2 * math.cos(angle)
                y = cy + h/2 * math.sin(angle)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)

        # Draw dimension lines
        painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
        # Width line
        painter.drawLine(int(cx - w/2), int(cy + h/2 + 15),
                        int(cx + w/2), int(cy + h/2 + 15))
        painter.drawLine(int(cx - w/2), int(cy + h/2 + 10),
                        int(cx - w/2), int(cy + h/2 + 20))
        painter.drawLine(int(cx + w/2), int(cy + h/2 + 10),
                        int(cx + w/2), int(cy + h/2 + 20))

        # Height line
        painter.drawLine(int(cx + w/2 + 15), int(cy - h/2),
                        int(cx + w/2 + 15), int(cy + h/2))
        painter.drawLine(int(cx + w/2 + 10), int(cy - h/2),
                        int(cx + w/2 + 20), int(cy - h/2))
        painter.drawLine(int(cx + w/2 + 10), int(cy + h/2),
                        int(cx + w/2 + 20), int(cy + h/2))


class StrandProfileDialog(QDialog):
    """Dialog for editing strand cross-section profile"""

    # Signal emitted when settings change (for live preview)
    settings_changed = pyqtSignal()

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle("Strand Profile Editor")
        self.setMinimumWidth(400)

        # Store original values for cancel
        self._store_original_values()

        self._setup_ui()
        self._connect_signals()
        self._load_current_values()

    def _store_original_values(self):
        """Store original values to restore on cancel"""
        # Get from first strand or use canvas defaults (which come from user settings)
        if self.canvas.strands:
            strand = self.canvas.strands[0]
            self.original_shape = getattr(strand, 'cross_section_shape', 'ellipse')
            self.original_width = strand.width
            self.original_height_ratio = strand.height_ratio
            self.original_corner_radius = getattr(strand, 'corner_radius', 0.0)
        else:
            # Use canvas defaults (loaded from user settings file)
            self.original_shape = self.canvas.default_cross_section_shape
            self.original_width = self.canvas.default_strand_width
            self.original_height_ratio = self.canvas.default_height_ratio
            self.original_corner_radius = self.canvas.default_corner_radius

    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Preview section
        preview_group = QGroupBox("Cross-Section Preview")
        preview_layout = QHBoxLayout(preview_group)

        self.preview = CrossSectionPreview()
        preview_layout.addWidget(self.preview)
        preview_layout.addStretch()

        layout.addWidget(preview_group)

        # Shape selection
        shape_group = QGroupBox("Shape")
        shape_layout = QGridLayout(shape_group)

        shape_layout.addWidget(QLabel("Cross-Section Shape:"), 0, 0)
        self.shape_combo = QComboBox()
        self.shape_combo.addItems([
            "Ellipse (Flat/Lenticular)",
            "Rectangle",
            "Circle",
            "Diamond",
            "Hexagon"
        ])
        shape_layout.addWidget(self.shape_combo, 0, 1)

        layout.addWidget(shape_group)

        # Dimensions section
        dims_group = QGroupBox("Dimensions")
        dims_layout = QGridLayout(dims_group)

        # Width
        dims_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.01, 2.0)
        self.width_spin.setSingleStep(0.01)
        self.width_spin.setDecimals(3)
        self.width_spin.setValue(0.15)
        dims_layout.addWidget(self.width_spin, 0, 1)

        # Height ratio
        dims_layout.addWidget(QLabel("Height Ratio:"), 1, 0)
        self.height_ratio_spin = QDoubleSpinBox()
        self.height_ratio_spin.setRange(0.1, 2.0)
        self.height_ratio_spin.setSingleStep(0.05)
        self.height_ratio_spin.setDecimals(2)
        self.height_ratio_spin.setValue(0.4)
        self.height_ratio_spin.setToolTip("Height as a fraction of width (0.4 = flat, 1.0 = circular)")
        dims_layout.addWidget(self.height_ratio_spin, 1, 1)

        # Height ratio slider for easier adjustment
        self.height_ratio_slider = QSlider(Qt.Horizontal)
        self.height_ratio_slider.setRange(10, 200)
        self.height_ratio_slider.setValue(40)
        dims_layout.addWidget(self.height_ratio_slider, 2, 0, 1, 2)

        # Corner radius (for rectangle)
        dims_layout.addWidget(QLabel("Corner Radius:"), 3, 0)
        self.corner_radius_spin = QDoubleSpinBox()
        self.corner_radius_spin.setRange(0.0, 1.0)
        self.corner_radius_spin.setSingleStep(0.05)
        self.corner_radius_spin.setDecimals(2)
        self.corner_radius_spin.setValue(0.0)
        self.corner_radius_spin.setToolTip("0 = sharp corners, 1 = fully rounded")
        self.corner_radius_spin.setEnabled(False)  # Only for rectangle
        dims_layout.addWidget(self.corner_radius_spin, 3, 1)

        layout.addWidget(dims_group)

        # Options section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.apply_to_all_cb = QCheckBox("Apply to all existing strands")
        self.apply_to_all_cb.setChecked(True)
        options_layout.addWidget(self.apply_to_all_cb)

        self.apply_to_new_cb = QCheckBox("Apply to new strands (set as default)")
        self.apply_to_new_cb.setChecked(True)
        options_layout.addWidget(self.apply_to_new_cb)

        self.live_preview_cb = QCheckBox("Live preview")
        self.live_preview_cb.setChecked(True)
        options_layout.addWidget(self.live_preview_cb)

        layout.addWidget(options_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Reset to Default")
        button_layout.addWidget(self.reset_btn)

        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setDefault(True)
        button_layout.addWidget(self.apply_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect UI signals"""
        self.shape_combo.currentIndexChanged.connect(self._on_shape_changed)
        self.width_spin.valueChanged.connect(self._on_value_changed)
        self.height_ratio_spin.valueChanged.connect(self._on_height_ratio_spin_changed)
        self.height_ratio_slider.valueChanged.connect(self._on_height_ratio_slider_changed)
        self.corner_radius_spin.valueChanged.connect(self._on_value_changed)

        self.reset_btn.clicked.connect(self._reset_to_default)
        self.cancel_btn.clicked.connect(self._cancel)
        self.apply_btn.clicked.connect(self._apply)

    def _load_current_values(self):
        """Load current values from canvas/strands"""
        # Get values from first strand or defaults
        shape = self.original_shape
        width = self.original_width
        height_ratio = self.original_height_ratio
        corner_radius = self.original_corner_radius

        # Set shape combo
        shape_map = {
            'ellipse': 0,
            'rectangle': 1,
            'circle': 2,
            'diamond': 3,
            'hexagon': 4
        }
        self.shape_combo.setCurrentIndex(shape_map.get(shape, 0))

        # Set dimension values
        self.width_spin.setValue(width)
        self.height_ratio_spin.setValue(height_ratio)
        self.height_ratio_slider.setValue(int(height_ratio * 100))
        self.corner_radius_spin.setValue(corner_radius)

        # Update preview
        self._update_preview()

    def _get_shape_name(self):
        """Get the shape name from combo selection"""
        shapes = ['ellipse', 'rectangle', 'circle', 'diamond', 'hexagon']
        return shapes[self.shape_combo.currentIndex()]

    def _on_shape_changed(self, index):
        """Handle shape selection change"""
        shape = self._get_shape_name()

        # Enable/disable corner radius for rectangle only
        self.corner_radius_spin.setEnabled(shape == 'rectangle')

        # For circle, lock height ratio to 1.0
        if shape == 'circle':
            self.height_ratio_spin.setValue(1.0)
            self.height_ratio_slider.setValue(100)
            self.height_ratio_spin.setEnabled(False)
            self.height_ratio_slider.setEnabled(False)
        else:
            self.height_ratio_spin.setEnabled(True)
            self.height_ratio_slider.setEnabled(True)

        self._update_preview()
        self._apply_live_preview()

    def _on_value_changed(self):
        """Handle any value change"""
        self._update_preview()
        self._apply_live_preview()

    def _on_height_ratio_spin_changed(self, value):
        """Sync slider when spin box changes"""
        self.height_ratio_slider.blockSignals(True)
        self.height_ratio_slider.setValue(int(value * 100))
        self.height_ratio_slider.blockSignals(False)
        self._update_preview()
        self._apply_live_preview()

    def _on_height_ratio_slider_changed(self, value):
        """Sync spin box when slider changes"""
        self.height_ratio_spin.blockSignals(True)
        self.height_ratio_spin.setValue(value / 100.0)
        self.height_ratio_spin.blockSignals(False)
        self._update_preview()
        self._apply_live_preview()

    def _update_preview(self):
        """Update the preview widget"""
        self.preview.set_shape(self._get_shape_name())
        self.preview.set_width(self.width_spin.value())
        self.preview.set_height_ratio(self.height_ratio_spin.value())
        self.preview.set_corner_radius(self.corner_radius_spin.value())

    def _apply_live_preview(self):
        """Apply changes for live preview if enabled"""
        if not self.live_preview_cb.isChecked():
            return

        self._apply_to_strands()

    def _apply_to_strands(self, save_to_file=False):
        """Apply current settings to strands"""
        shape = self._get_shape_name()
        width = self.width_spin.value()
        height_ratio = self.height_ratio_spin.value()
        corner_radius = self.corner_radius_spin.value()

        # Apply to existing strands
        if self.apply_to_all_cb.isChecked():
            for strand in self.canvas.strands:
                strand.cross_section_shape = shape
                strand.width = width
                strand.height_ratio = height_ratio
                strand.corner_radius = corner_radius
                strand._mark_geometry_dirty()

        # Set defaults for new strands
        if self.apply_to_new_cb.isChecked():
            self.canvas.default_strand_width = width
            self.canvas.default_height_ratio = height_ratio
            self.canvas.default_cross_section_shape = shape
            self.canvas.default_corner_radius = corner_radius

            # Save to user settings file if requested
            if save_to_file:
                from user_settings import get_settings
                settings = get_settings()
                settings.update_and_save({
                    'default_strand_width': width,
                    'default_height_ratio': height_ratio,
                    'default_cross_section_shape': shape,
                    'default_corner_radius': corner_radius,
                })

        # Trigger canvas redraw
        self.canvas.update()
        self.settings_changed.emit()

    def _reset_to_default(self):
        """Reset to default values"""
        self.shape_combo.setCurrentIndex(0)  # Ellipse
        self.width_spin.setValue(0.15)
        self.height_ratio_spin.setValue(0.4)
        self.height_ratio_slider.setValue(40)
        self.corner_radius_spin.setValue(0.0)
        self._update_preview()
        self._apply_live_preview()

    def _cancel(self):
        """Cancel and restore original values"""
        # Restore original values
        for strand in self.canvas.strands:
            strand.cross_section_shape = self.original_shape
            strand.width = self.original_width
            strand.height_ratio = self.original_height_ratio
            strand.corner_radius = self.original_corner_radius
            strand._mark_geometry_dirty()

        self.canvas.update()
        self.reject()

    def _apply(self):
        """Apply changes and close, saving defaults to settings file"""
        self._apply_to_strands(save_to_file=True)
        self.accept()
