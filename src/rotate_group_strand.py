"""
OpenStrandStudio 3D - Rotate Group Strand
Handles rotation of strand groups around a defined axis
"""

import math
import numpy as np
from PyQt5.QtCore import Qt


class RotateGroupStrandMixin:
    """
    Mixin class providing group strand rotation functionality.

    This class should be inherited by StrandDrawingCanvas along with other mixins.
    It provides methods for:
    - Calculating group center from start/end points only
    - Defining rotation axis from center to a user-specified point
    - Rotating all control points (start, end, CP1, CP2) around the axis
    - Using vertical mouse drag to control rotation angle
    """

    def _init_rotate_group_strand_mode(self):
        """Initialize rotation group strand mode state"""
        self.rotating_group = False
        self.rotation_set_number = None
        self.rotation_center = None
        self.rotation_axis = None
        self.rotation_angle = 0.0
        self.rotation_initial_positions = {}  # Store original positions
        self.rotation_last_screen_y = None
        self.rotation_axis_mode = "normal"  # "normal" (XZ), "vertical" (Y)

    def start_rotate_group_strand(self, set_number):
        """
        Start rotation mode for a strand group.

        Args:
            set_number: The set number to rotate (e.g., "1", "2")
        """
        # Get all strands in the set
        set_number_str = str(set_number)
        set_prefix = f"{set_number_str}_"
        group_strands = [s for s in self.strands if s.name.startswith(set_prefix)]

        if not group_strands:
            print(f"No strands found in set {set_number}")
            return False

        # Calculate center from ONLY start and end points
        center = self._calculate_group_center_from_endpoints(group_strands)

        # Save state for undo
        if hasattr(self, 'undo_redo_manager') and self.undo_redo_manager:
            self.undo_redo_manager.save_state()

        # Initialize rotation state
        self.rotating_group = True
        self.rotation_set_number = set_number_str
        self.rotation_center = center
        self.rotation_axis = None  # Will be set on first mouse move
        self.rotation_angle = 0.0
        self.rotation_last_screen_y = None

        # Store initial positions of all points for all strands
        self.rotation_initial_positions = {}
        for strand in group_strands:
            self.rotation_initial_positions[strand.name] = {
                'start': strand.start.copy(),
                'end': strand.end.copy(),
                'cp1': strand.control_point1.copy(),
                'cp2': strand.control_point2.copy()
            }

        print(f"Started rotation for set {set_number} around center {center}")
        return True

    def _calculate_group_center_from_endpoints(self, strands):
        """
        Calculate the center of a group of strands using ONLY start and end points.
        Control points are ignored.

        Args:
            strands: List of Strand objects

        Returns:
            numpy array [x, y, z] - the center point
        """
        if not strands:
            return np.array([0.0, 0.0, 0.0])

        # Collect all start and end points (ignore control points)
        points = []
        for strand in strands:
            points.append(strand.start)
            points.append(strand.end)

        # Calculate average position
        center = np.mean(points, axis=0)
        return center

    def update_rotate_group_strand(self, screen_x, screen_y, axis_mode="normal"):
        """
        Update rotation based on mouse movement.

        Args:
            screen_x: Mouse X position
            screen_y: Mouse Y position
            axis_mode: "normal" (XZ plane) or "vertical" (Y axis)
        """
        if not self.rotating_group:
            return

        # Define rotation axis on first move
        if self.rotation_axis is None:
            self.rotation_axis = self._define_rotation_axis(screen_x, screen_y, axis_mode)
            self.rotation_last_screen_y = screen_y
            self.rotation_axis_mode = axis_mode
            print(f"Rotation axis defined: {self.rotation_axis} (mode: {axis_mode})")
            return

        # Calculate rotation angle from vertical mouse movement
        if self.rotation_last_screen_y is None:
            self.rotation_last_screen_y = screen_y
            return

        screen_dy = screen_y - self.rotation_last_screen_y
        self.rotation_last_screen_y = screen_y

        # Convert screen movement to angle (pixels to radians)
        # Adjust sensitivity based on camera distance
        angle_speed = 0.01  # Radians per pixel
        angle_delta = -screen_dy * angle_speed  # Negative for intuitive direction

        self.rotation_angle += angle_delta

        # Apply rotation to all strands in the group
        self._apply_rotation_to_group()

    def _define_rotation_axis(self, screen_x, screen_y, axis_mode):
        """
        Define the rotation axis based on mouse position and mode.

        Args:
            screen_x: Mouse X position
            screen_y: Mouse Y position
            axis_mode: "normal" (XZ plane) or "vertical" (Y axis)

        Returns:
            Normalized axis vector [x, y, z]
        """
        if axis_mode == "vertical":
            # Rotation axis is vertical (Y axis)
            return np.array([0.0, 1.0, 0.0])
        else:
            # axis_mode == "normal"
            # Project mouse to XZ plane and create axis from center to that point
            point_3d = self._screen_to_ground(screen_x, screen_y, ground_y=self.rotation_center[1])

            if point_3d is None:
                # Fallback to Y axis if projection fails
                return np.array([0.0, 1.0, 0.0])

            # Create axis from center to projected point
            axis = np.array(point_3d) - self.rotation_center

            # Zero out Y component to keep axis horizontal (in XZ plane)
            axis[1] = 0.0

            axis_len = np.linalg.norm(axis)
            if axis_len < 1e-6:
                # Too close to center, use a default axis
                return np.array([1.0, 0.0, 0.0])

            # Normalize the axis
            return axis / axis_len

    def _apply_rotation_to_group(self):
        """
        Apply the current rotation to all strands in the group.
        Uses Rodrigues' rotation formula to rotate all control points around the axis.
        """
        if not self.rotating_group or self.rotation_axis is None:
            return

        set_prefix = f"{self.rotation_set_number}_"
        group_strands = [s for s in self.strands if s.name.startswith(set_prefix)]

        for strand in group_strands:
            if strand.name not in self.rotation_initial_positions:
                continue

            initial = self.rotation_initial_positions[strand.name]

            # Rotate each control point around the axis
            strand.start = self._rotate_point_around_axis(
                initial['start'],
                self.rotation_center,
                self.rotation_axis,
                self.rotation_angle
            )

            strand.end = self._rotate_point_around_axis(
                initial['end'],
                self.rotation_center,
                self.rotation_axis,
                self.rotation_angle
            )

            strand.control_point1 = self._rotate_point_around_axis(
                initial['cp1'],
                self.rotation_center,
                self.rotation_axis,
                self.rotation_angle
            )

            strand.control_point2 = self._rotate_point_around_axis(
                initial['cp2'],
                self.rotation_center,
                self.rotation_axis,
                self.rotation_angle
            )

            # Mark geometry as dirty to trigger re-render
            strand._mark_geometry_dirty()

    def _rotate_point_around_axis(self, point, center, axis, angle):
        """
        Rotate a point around an axis passing through a center point.
        Uses Rodrigues' rotation formula.

        Args:
            point: Point to rotate [x, y, z]
            center: Center of rotation [x, y, z]
            axis: Normalized rotation axis [x, y, z]
            angle: Rotation angle in radians

        Returns:
            Rotated point [x, y, z]
        """
        # Translate point to origin (relative to center)
        p = np.array(point) - np.array(center)

        # Apply Rodrigues' rotation formula
        # v_rot = v*cos(θ) + (k × v)*sin(θ) + k*(k·v)*(1-cos(θ))
        # where k is the unit axis vector
        cos_angle = np.cos(angle)
        sin_angle = np.sin(angle)

        k = np.array(axis)  # Should already be normalized

        # Calculate the three terms
        term1 = p * cos_angle
        term2 = np.cross(k, p) * sin_angle
        term3 = k * np.dot(k, p) * (1 - cos_angle)

        # Combine terms
        p_rotated = term1 + term2 + term3

        # Translate back to world space
        return p_rotated + np.array(center)

    def end_rotate_group_strand(self):
        """End rotation mode"""
        if self.rotating_group:
            print(f"Finished rotating set {self.rotation_set_number} by {math.degrees(self.rotation_angle):.1f} degrees")

        self.rotating_group = False
        self.rotation_set_number = None
        self.rotation_center = None
        self.rotation_axis = None
        self.rotation_angle = 0.0
        self.rotation_initial_positions = {}
        self.rotation_last_screen_y = None

    def is_rotating_group(self):
        """Check if currently rotating a group"""
        return self.rotating_group
