"""
OpenStrandStudio 3D - Angle Adjust Mode
Handles angle and length adjustment for strands using spherical coordinates
(azimuth, elevation, length)
"""

import math
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSlider, QDoubleSpinBox,
    QPushButton, QLabel, QGroupBox
)


class AngleAdjustModeMixin:
    """
    Mixin class providing angle/length adjustment functionality.

    This class should be inherited by StrandDrawingCanvas along with other mixins.
    It provides methods for:
    - Adjusting strand orientation using spherical coordinates (azimuth, elevation)
    - Adjusting strand length
    - Rotating control points with the strand
    - Updating attached strands
    """

    def _init_angle_adjust_mode(self):
        """Initialize angle adjust mode state variables"""
        self.angle_adjust_active = False
        self.angle_adjust_strand = None

        # Initial state storage for cancel
        self.aa_initial_start = None
        self.aa_initial_end = None
        self.aa_initial_cp1 = None
        self.aa_initial_cp2 = None

        # Initial spherical coordinates
        self.aa_initial_azimuth = 0.0
        self.aa_initial_elevation = 0.0
        self.aa_initial_length = 0.0

        # Current values
        self.aa_current_azimuth = 0.0
        self.aa_current_elevation = 0.0
        self.aa_current_length = 0.0

        # Control point vectors (relative to start)
        self.aa_initial_cp1_vector = None
        self.aa_initial_cp2_vector = None
        self.aa_length_scale = 1.0

    def activate_angle_adjust_mode(self, strand):
        """
        Activate angle adjust mode for the given strand.

        Args:
            strand: The strand to adjust
        """
        if strand is None:
            return

        self.angle_adjust_active = True
        self.angle_adjust_strand = strand

        # Store initial positions for cancel
        self.aa_initial_start = strand.start.copy()
        self.aa_initial_end = strand.end.copy()
        self.aa_initial_cp1 = strand.control_point1.copy()
        self.aa_initial_cp2 = strand.control_point2.copy()

        # Calculate initial spherical coordinates
        self.aa_initial_azimuth, self.aa_initial_elevation, self.aa_initial_length = \
            self._cartesian_to_spherical(strand.start, strand.end)

        self.aa_current_azimuth = self.aa_initial_azimuth
        self.aa_current_elevation = self.aa_initial_elevation
        self.aa_current_length = self.aa_initial_length

        # Store control point vectors relative to start
        self.aa_initial_cp1_vector = strand.control_point1 - strand.start
        self.aa_initial_cp2_vector = strand.control_point2 - strand.start
        self.aa_length_scale = 1.0

        # Find attached strands and store their initial state
        self._aa_store_attached_strands_state(strand)

        # Show the adjustment dialog
        self._show_angle_adjust_dialog()

    def _cartesian_to_spherical(self, start, end):
        """
        Convert from Cartesian coordinates to spherical (azimuth, elevation, length).

        Args:
            start: Start point (numpy array)
            end: End point (numpy array)

        Returns:
            tuple: (azimuth in degrees, elevation in degrees, length)
        """
        delta = end - start
        length = np.linalg.norm(delta)

        if length < 1e-6:
            return 0.0, 0.0, 0.0

        # Azimuth: angle on XZ plane from positive X axis
        # atan2(z, x) gives angle from X axis towards Z axis
        azimuth = math.degrees(math.atan2(delta[2], delta[0]))

        # Elevation: angle from XZ plane (horizontal)
        # Positive = upward, negative = downward
        horizontal_dist = math.sqrt(delta[0]**2 + delta[2]**2)
        elevation = math.degrees(math.atan2(delta[1], horizontal_dist))

        return azimuth, elevation, length

    def _spherical_to_cartesian(self, start, azimuth, elevation, length):
        """
        Convert from spherical coordinates to Cartesian end point.

        Args:
            start: Start point (numpy array)
            azimuth: Horizontal angle in degrees (0 = +X, 90 = +Z)
            elevation: Vertical angle in degrees (-90 to +90)
            length: Distance from start to end

        Returns:
            numpy array: End point position
        """
        azimuth_rad = math.radians(azimuth)
        elevation_rad = math.radians(elevation)

        # Calculate delta from spherical coordinates
        horizontal_dist = length * math.cos(elevation_rad)
        dx = horizontal_dist * math.cos(azimuth_rad)
        dy = length * math.sin(elevation_rad)
        dz = horizontal_dist * math.sin(azimuth_rad)

        return start + np.array([dx, dy, dz])

    def _show_angle_adjust_dialog(self):
        """Show the angle/length adjustment dialog"""
        if not self.angle_adjust_strand:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Adjust Angle and Length")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Azimuth adjustment (horizontal angle)
        azimuth_group = QGroupBox("Azimuth (Horizontal Angle)")
        azimuth_layout = QHBoxLayout()

        azimuth_slider = QSlider(Qt.Horizontal)
        azimuth_slider.setRange(-180, 180)
        azimuth_slider.setValue(int(self.aa_current_azimuth))

        azimuth_spinbox = QDoubleSpinBox()
        azimuth_spinbox.setRange(-180, 180)
        azimuth_spinbox.setValue(self.aa_current_azimuth)
        azimuth_spinbox.setSingleStep(1)
        azimuth_spinbox.setSuffix("°")

        azimuth_layout.addWidget(QLabel("Angle:"))
        azimuth_layout.addWidget(azimuth_slider, 1)
        azimuth_layout.addWidget(azimuth_spinbox)
        azimuth_group.setLayout(azimuth_layout)
        layout.addWidget(azimuth_group)

        # Elevation adjustment (vertical angle)
        elevation_group = QGroupBox("Elevation (Vertical Angle)")
        elevation_layout = QHBoxLayout()

        elevation_slider = QSlider(Qt.Horizontal)
        elevation_slider.setRange(-90, 90)
        elevation_slider.setValue(int(self.aa_current_elevation))

        elevation_spinbox = QDoubleSpinBox()
        elevation_spinbox.setRange(-90, 90)
        elevation_spinbox.setValue(self.aa_current_elevation)
        elevation_spinbox.setSingleStep(1)
        elevation_spinbox.setSuffix("°")

        elevation_layout.addWidget(QLabel("Angle:"))
        elevation_layout.addWidget(elevation_slider, 1)
        elevation_layout.addWidget(elevation_spinbox)
        elevation_group.setLayout(elevation_layout)
        layout.addWidget(elevation_group)

        # Length adjustment
        length_group = QGroupBox("Length")
        length_layout = QHBoxLayout()

        max_length = max(10, int(self.aa_initial_length * 3))

        length_slider = QSlider(Qt.Horizontal)
        length_slider.setRange(1, max_length * 10)  # Use 0.1 precision
        length_slider.setValue(int(self.aa_current_length * 10))

        length_spinbox = QDoubleSpinBox()
        length_spinbox.setRange(0.1, max_length)
        length_spinbox.setValue(self.aa_current_length)
        length_spinbox.setSingleStep(0.1)
        length_spinbox.setDecimals(1)

        length_layout.addWidget(QLabel("Length:"))
        length_layout.addWidget(length_slider, 1)
        length_layout.addWidget(length_spinbox)
        length_group.setLayout(length_layout)
        layout.addWidget(length_group)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        # Connect signals
        def update_azimuth(value):
            if isinstance(value, int):
                azimuth_spinbox.setValue(value)
            else:
                azimuth_slider.setValue(int(value))
            self._aa_update_strand(azimuth=value)

        def update_elevation(value):
            if isinstance(value, int):
                elevation_spinbox.setValue(value)
            else:
                elevation_slider.setValue(int(value))
            self._aa_update_strand(elevation=value)

        def update_length(value):
            if isinstance(value, int):
                length_spinbox.setValue(value / 10.0)
            else:
                length_slider.setValue(int(value * 10))
            self._aa_update_strand(length=value if not isinstance(value, int) else value / 10.0)

        azimuth_slider.valueChanged.connect(update_azimuth)
        azimuth_spinbox.valueChanged.connect(update_azimuth)
        elevation_slider.valueChanged.connect(update_elevation)
        elevation_spinbox.valueChanged.connect(update_elevation)
        length_slider.valueChanged.connect(update_length)
        length_spinbox.valueChanged.connect(update_length)

        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        result = dialog.exec_()

        if result == QDialog.Accepted:
            self._aa_confirm_adjustment()
        else:
            self._aa_cancel_adjustment()

    def _aa_update_strand(self, azimuth=None, elevation=None, length=None):
        """
        Update the strand based on new spherical coordinates.

        Args:
            azimuth: New azimuth angle in degrees (optional)
            elevation: New elevation angle in degrees (optional)
            length: New length (optional)
        """
        if not self.angle_adjust_strand:
            return

        strand = self.angle_adjust_strand
        old_end = strand.end.copy()

        # Update current values
        if azimuth is not None:
            self.aa_current_azimuth = azimuth
        if elevation is not None:
            self.aa_current_elevation = elevation
        if length is not None:
            self.aa_current_length = length
            # Update length scale for control point scaling
            if self.aa_initial_length > 0:
                self.aa_length_scale = self.aa_current_length / self.aa_initial_length

        # Calculate new end position
        new_end = self._spherical_to_cartesian(
            strand.start,
            self.aa_current_azimuth,
            self.aa_current_elevation,
            self.aa_current_length
        )

        # Update strand end
        strand.end = new_end

        # Update control points with rotation and scaling
        self._aa_update_control_points()

        strand._mark_geometry_dirty()

        # Update attached strands
        self._aa_update_attached_strands(old_end, new_end)

        self.update()

    def _aa_update_control_points(self):
        """Update control points based on rotation and length scaling"""
        if not self.angle_adjust_strand:
            return

        strand = self.angle_adjust_strand

        # Calculate angle differences from initial
        azimuth_diff = self.aa_current_azimuth - self.aa_initial_azimuth
        elevation_diff = self.aa_current_elevation - self.aa_initial_elevation

        # Scale the initial control point vectors
        scaled_cp1_vec = self.aa_initial_cp1_vector * self.aa_length_scale
        scaled_cp2_vec = self.aa_initial_cp2_vector * self.aa_length_scale

        # Rotate the scaled vectors
        rotated_cp1_vec = self._aa_rotate_vector(scaled_cp1_vec, azimuth_diff, elevation_diff)
        rotated_cp2_vec = self._aa_rotate_vector(scaled_cp2_vec, azimuth_diff, elevation_diff)

        # Apply to strand
        strand.control_point1 = strand.start + rotated_cp1_vec
        strand.control_point2 = strand.start + rotated_cp2_vec

    def _aa_rotate_vector(self, vec, azimuth_diff, elevation_diff):
        """
        Rotate a vector by the given azimuth and elevation differences.

        Args:
            vec: Vector to rotate (numpy array)
            azimuth_diff: Azimuth rotation in degrees
            elevation_diff: Elevation rotation in degrees

        Returns:
            numpy array: Rotated vector
        """
        # First rotate around Y axis (azimuth)
        azimuth_rad = math.radians(azimuth_diff)
        cos_a = math.cos(azimuth_rad)
        sin_a = math.sin(azimuth_rad)

        # Y-axis rotation matrix
        rotated = np.array([
            vec[0] * cos_a + vec[2] * sin_a,
            vec[1],
            -vec[0] * sin_a + vec[2] * cos_a
        ])

        # Then rotate around the horizontal axis perpendicular to current direction (elevation)
        # This is rotation in the vertical plane containing the strand
        current_azimuth_rad = math.radians(self.aa_current_azimuth)

        # The axis of rotation is perpendicular to the azimuth direction in the XZ plane
        # This is (-sin(azimuth), 0, cos(azimuth))
        axis = np.array([-math.sin(current_azimuth_rad), 0, math.cos(current_azimuth_rad)])

        # Rodrigues' rotation formula
        elevation_rad = math.radians(elevation_diff)
        cos_e = math.cos(elevation_rad)
        sin_e = math.sin(elevation_rad)

        rotated = (rotated * cos_e +
                   np.cross(axis, rotated) * sin_e +
                   axis * np.dot(axis, rotated) * (1 - cos_e))

        return rotated

    def _aa_store_attached_strands_state(self, strand):
        """Store initial state of attached strands for restoration on cancel"""
        self.aa_attached_strands_state = []

        for attached in strand.attached_strands:
            state = {
                'strand': attached,
                'start': attached.start.copy(),
                'end': attached.end.copy(),
                'cp1': attached.control_point1.copy(),
                'cp2': attached.control_point2.copy()
            }
            self.aa_attached_strands_state.append(state)

            # Recursively store state for strands attached to this one
            self._aa_store_attached_strands_state_recursive(attached)

    def _aa_store_attached_strands_state_recursive(self, strand):
        """Recursively store attached strand states"""
        for attached in strand.attached_strands:
            state = {
                'strand': attached,
                'start': attached.start.copy(),
                'end': attached.end.copy(),
                'cp1': attached.control_point1.copy(),
                'cp2': attached.control_point2.copy()
            }
            self.aa_attached_strands_state.append(state)
            self._aa_store_attached_strands_state_recursive(attached)

    def _aa_update_attached_strands(self, old_end, new_end):
        """
        Update attached strands when the active strand's end moves.
        (2D-style: only move connection point, keep end fixed)

        Args:
            old_end: Previous end position
            new_end: New end position
        """
        if not self.angle_adjust_strand:
            return

        for attached in self.angle_adjust_strand.attached_strands:
            # Check if this attached strand starts at the active strand's end
            if np.allclose(attached.start, old_end, atol=0.1):
                # Store the control point vectors relative to old start
                cp1_vector = attached.control_point1 - attached.start
                cp2_vector = attached.control_point2 - attached.start

                # Store the original end point (keep it fixed - 2D style)
                original_end = attached.end.copy()

                # Update the start point to match new end
                attached.start = new_end.copy()

                # Keep end fixed (2D style behavior)
                attached.end = original_end

                # Update control points relative to new start
                attached.control_point1 = attached.start + cp1_vector
                attached.control_point2 = attached.start + cp2_vector

                attached._mark_geometry_dirty()

                # Recursively update strands attached to this one
                self._aa_update_attached_strands_recursive(attached)

    def _aa_update_attached_strands_recursive(self, strand):
        """Recursively update strands attached to the given strand"""
        old_end = strand.end.copy()

        for attached in strand.attached_strands:
            # Check if attached at end
            if np.allclose(attached.start, old_end, atol=0.1):
                # Store control point vectors
                cp1_vector = attached.control_point1 - attached.start
                cp2_vector = attached.control_point2 - attached.start

                # Store original end
                original_end = attached.end.copy()

                # Update start to match parent's end
                attached.start = strand.end.copy()

                # Keep end fixed
                attached.end = original_end

                # Update control points
                attached.control_point1 = attached.start + cp1_vector
                attached.control_point2 = attached.start + cp2_vector

                attached._mark_geometry_dirty()

                # Continue recursively
                self._aa_update_attached_strands_recursive(attached)

    def _aa_confirm_adjustment(self):
        """Confirm the angle/length adjustment"""
        self.angle_adjust_active = False
        self.angle_adjust_strand = None
        self.aa_attached_strands_state = []
        self.update()

    def _aa_cancel_adjustment(self):
        """Cancel the adjustment and restore original state"""
        if self.angle_adjust_strand:
            strand = self.angle_adjust_strand

            # Restore strand to initial state
            strand.start = self.aa_initial_start
            strand.end = self.aa_initial_end
            strand.control_point1 = self.aa_initial_cp1
            strand.control_point2 = self.aa_initial_cp2
            strand._mark_geometry_dirty()

            # Restore attached strands
            for state in getattr(self, 'aa_attached_strands_state', []):
                attached = state['strand']
                attached.start = state['start']
                attached.end = state['end']
                attached.control_point1 = state['cp1']
                attached.control_point2 = state['cp2']
                attached._mark_geometry_dirty()

        self.angle_adjust_active = False
        self.angle_adjust_strand = None
        self.aa_attached_strands_state = []
        self.update()

    def _aa_handle_key_press(self, event):
        """
        Handle keyboard input for angle adjust mode.

        Arrow keys for quick adjustment:
        - Left/Right: Adjust azimuth
        - Up/Down: Adjust elevation (or length with Shift)
        """
        if not self.angle_adjust_active or not self.angle_adjust_strand:
            return False

        key = event.key()
        shift = event.modifiers() & Qt.ShiftModifier

        step_angle = 5  # Degrees per key press
        step_length = 0.1  # Length units per key press

        if key == Qt.Key_Left:
            self._aa_update_strand(azimuth=self.aa_current_azimuth - step_angle)
            return True
        elif key == Qt.Key_Right:
            self._aa_update_strand(azimuth=self.aa_current_azimuth + step_angle)
            return True
        elif key == Qt.Key_Up:
            if shift:
                self._aa_update_strand(length=self.aa_current_length + step_length)
            else:
                self._aa_update_strand(elevation=min(90, self.aa_current_elevation + step_angle))
            return True
        elif key == Qt.Key_Down:
            if shift:
                self._aa_update_strand(length=max(0.1, self.aa_current_length - step_length))
            else:
                self._aa_update_strand(elevation=max(-90, self.aa_current_elevation - step_angle))
            return True
        elif key == Qt.Key_Escape:
            self._aa_cancel_adjustment()
            return True
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            self._aa_confirm_adjustment()
            return True

        return False
