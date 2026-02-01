"""
OpenStrandStudio 3D - Rotate Mode
Handles rotation mode functionality with visual arrow indicator and editable axis.
Similar to stretch mode but for rotating strand groups around a defined axis.
"""

import math
import numpy as np
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *


class RotateModeMixin:
    """
    Mixin class providing rotation mode functionality with visual arrow.

    This class should be inherited by StrandDrawingCanvas along with other mixins.
    It provides methods for:
    - Selecting a strand group (set) to rotate
    - Drawing a gradient 1-unit arrow showing rotation axis
    - Editable arrow endpoint for adjusting axis direction
    - XZ and Y axis modes for rotation
    - Executing rotation by mouse drag
    """

    # Rotate mode visual settings
    ROTATE_ARROW_LENGTH = 1.0  # Length of the rotation axis arrow
    ROTATE_ARROW_START_COLOR = (0.2, 0.6, 1.0)  # Blue at base
    ROTATE_ARROW_END_COLOR = (1.0, 0.3, 0.8)  # Magenta at tip
    ROTATE_CENTER_COLOR = (1.0, 1.0, 0.0)  # Yellow for rotation center
    ROTATE_HANDLE_COLOR = (1.0, 0.5, 0.0)  # Orange for draggable handle
    ROTATE_DISK_COLOR = (0.3, 0.8, 0.4)  # Green for rotation disk
    ROTATE_DISK_ACTIVE_COLOR = (0.5, 1.0, 0.6)  # Bright green when rotating
    ROTATE_DISK_HOVER_COLOR = (0.4, 0.9, 0.5)  # Lighter green on hover
    ROTATE_HANDLE_HOVER_COLOR = (1.0, 0.75, 0.2)  # Bright orange-yellow on hover
    ROTATE_CENTER_RADIUS = 0.15
    ROTATE_HANDLE_RADIUS = 0.12
    ROTATE_DISK_RADIUS = 0.6  # Radius of the rotation disk
    ROTATE_DISK_SEGMENTS = 32  # Number of segments for the disk circle

    def _init_rotate_mode(self):
        """Initialize rotate mode state variables."""
        self.rotate_mode_active = False
        self.rotate_selected_set = None  # Set number being rotated
        self.rotate_center = None  # Center point of rotation (calculated from group)
        self.rotate_axis_end = None  # End point of the 1-unit axis arrow
        self.rotate_axis_direction = None  # Normalized axis direction
        self.rotate_axis_mode = "normal"  # 'normal' (XZ), 'vertical' (Y)
        self.is_editing_rotate_axis = False  # True while editing the axis arrow
        self.is_rotating = False  # True while performing rotation via disk drag
        self.rotate_initial_positions = {}  # Store original positions for rotation
        self.rotate_angle = 0.0  # Current rotation angle (in radians)
        self.rotate_total_angle = 0.0  # Total accumulated rotation angle for display
        self.rotate_last_screen_x = None  # For tracking horizontal drag on disk
        self.rotate_drag_start_x = None  # Starting X position of drag
        self.rotate_drag_start_screen_pos = None  # (x, y) screen position where drag started
        self.rotate_current_screen_x = None  # Current mouse X for UI drawing
        self.rotate_hover_handle = False  # True when mouse is over axis handle
        self.rotate_hover_disk = False  # True when mouse is over rotation disk

    def _enter_rotate_mode(self):
        """Called when entering rotate mode."""
        self._init_rotate_mode()

        # If a strand is already selected, immediately activate rotation for its set
        if self.selected_strand:
            parts = self.selected_strand.name.split('_')
            if len(parts) >= 1:
                set_number = parts[0]
                self.select_set_for_rotation(set_number)

        self.update()

    def _exit_rotate_mode(self):
        """Called when exiting rotate mode."""
        if hasattr(self, 'rotate_mode_active'):
            self.rotate_mode_active = False
            self.rotate_selected_set = None
            self.rotate_center = None
            self.rotate_axis_end = None
            self.rotate_axis_direction = None
            self.is_editing_rotate_axis = False
            self.is_rotating = False
            self.rotate_initial_positions = {}

    def select_set_for_rotation(self, set_number):
        """
        Select a strand set for rotation and initialize the axis arrow.

        Args:
            set_number: The set number to rotate (e.g., "1", "2")

        Returns:
            True if successful, False otherwise
        """
        set_number_str = str(set_number)
        set_prefix = f"{set_number_str}_"
        group_strands = [s for s in self.strands if s.name.startswith(set_prefix)]

        if not group_strands:
            print(f"Rotate: No strands found in set {set_number}")
            return False

        # Calculate center from start and end points only
        center = self._calculate_rotation_center(group_strands)

        # Initialize rotation state
        self.rotate_mode_active = True
        self.rotate_selected_set = set_number_str
        self.rotate_center = center

        # Calculate initial axis as the NORMAL (perpendicular) to the plane of the strands
        # This is the natural rotation axis - rotating around it keeps strands in their plane
        self.rotate_axis_direction = self._calculate_plane_normal(group_strands)

        # Set the axis arrow end point (1 unit from center)
        self.rotate_axis_end = center + self.rotate_axis_direction * self.ROTATE_ARROW_LENGTH

        print(f"Rotate: Initial axis (plane normal) = {self.rotate_axis_direction}")

        # Store initial positions for all strands in the group
        self.rotate_initial_positions = {}
        for strand in group_strands:
            self.rotate_initial_positions[strand.name] = {
                'start': strand.start.copy(),
                'end': strand.end.copy(),
                'cp1': strand.control_point1.copy(),
                'cp2': strand.control_point2.copy()
            }

        print(f"Rotate: Selected set {set_number} with center at {center}")
        self.update()
        return True

    def _calculate_rotation_center(self, strands):
        """Calculate the center of a group of strands using only start and end points."""
        if not strands:
            return np.array([0.0, 0.0, 0.0])

        points = []
        for strand in strands:
            points.append(strand.start)
            points.append(strand.end)

        center = np.mean(points, axis=0)
        return center

    def _calculate_plane_normal(self, strands):
        """
        Calculate the normal vector (perpendicular) to the plane formed by strand points.

        This uses the cross product of two vectors formed by the start/end points
        to find a vector perpendicular to the plane that best fits the points.

        Args:
            strands: List of strand objects

        Returns:
            Normalized normal vector, or default Y-up if calculation fails
        """
        if len(strands) < 1:
            return np.array([0.0, 1.0, 0.0])  # Default to Y-up

        # Collect all start and end points
        points = []
        for strand in strands:
            points.append(np.array(strand.start))
            points.append(np.array(strand.end))

        if len(points) < 3:
            # Not enough points, use strand direction cross with Y
            if len(strands) >= 1:
                strand_dir = strands[0].end - strands[0].start
                normal = np.cross(strand_dir, np.array([0.0, 1.0, 0.0]))
                norm_len = np.linalg.norm(normal)
                if norm_len > 1e-6:
                    return normal / norm_len
            return np.array([0.0, 1.0, 0.0])

        # Calculate center
        center = np.mean(points, axis=0)

        # Find two vectors from center to different points
        # Try to find vectors that are not collinear
        best_normal = None
        best_area = 0

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                v1 = points[i] - center
                v2 = points[j] - center

                # Cross product gives normal to the plane containing v1 and v2
                normal = np.cross(v1, v2)
                area = np.linalg.norm(normal)

                # Keep the cross product with largest area (most perpendicular vectors)
                if area > best_area:
                    best_area = area
                    best_normal = normal

        if best_normal is not None and best_area > 1e-6:
            # Normalize the normal vector
            best_normal = best_normal / best_area

            # Make sure normal points "up" (positive Y component) for consistency
            if best_normal[1] < 0:
                best_normal = -best_normal

            return best_normal

        # Fallback: use Y-up
        return np.array([0.0, 1.0, 0.0])

    def _draw_rotate_mode_indicators(self):
        """Draw visual indicators for rotate mode."""
        if self.current_mode != "rotate" or not self.rotate_mode_active:
            return

        if self.rotate_center is None or self.rotate_axis_end is None:
            return

        glDisable(GL_LIGHTING)

        # Draw rotation disk (perpendicular to axis) - draw first so it's behind
        self._draw_rotation_disk()

        # Draw center sphere (yellow)
        self._draw_rotate_center_sphere()

        # Draw gradient axis arrow
        self._draw_gradient_axis_arrow()

        # Draw draggable handle at arrow end
        self._draw_rotate_axis_handle()

        # Draw angle display
        self._draw_rotation_angle_display()

        # Draw drag UI overlay (2D) when rotating
        if self.is_rotating:
            self._draw_rotation_drag_ui()

        glEnable(GL_LIGHTING)

    def _draw_rotate_center_sphere(self):
        """Draw a sphere at the rotation center."""
        glPushMatrix()
        glTranslatef(self.rotate_center[0], self.rotate_center[1], self.rotate_center[2])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(*self.ROTATE_CENTER_COLOR, 0.8)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, self.ROTATE_CENTER_RADIUS, 16, 16)
        gluDeleteQuadric(quadric)

        glDisable(GL_BLEND)
        glPopMatrix()

    def _draw_gradient_axis_arrow(self):
        """Draw a gradient arrow from center to axis end point."""
        start = self.rotate_center
        end = self.rotate_axis_end

        # Draw gradient line using multiple segments
        num_segments = 20
        glLineWidth(4.0)
        glBegin(GL_LINE_STRIP)

        for i in range(num_segments + 1):
            t = i / num_segments
            # Interpolate position
            pos = start + t * (end - start)
            # Interpolate color (blue to magenta gradient)
            r = self.ROTATE_ARROW_START_COLOR[0] + t * (self.ROTATE_ARROW_END_COLOR[0] - self.ROTATE_ARROW_START_COLOR[0])
            g = self.ROTATE_ARROW_START_COLOR[1] + t * (self.ROTATE_ARROW_END_COLOR[1] - self.ROTATE_ARROW_START_COLOR[1])
            b = self.ROTATE_ARROW_START_COLOR[2] + t * (self.ROTATE_ARROW_END_COLOR[2] - self.ROTATE_ARROW_START_COLOR[2])
            glColor3f(r, g, b)
            glVertex3f(pos[0], pos[1], pos[2])

        glEnd()

        # Draw arrowhead at the end
        direction = end - start
        length = np.linalg.norm(direction)
        if length > 0.1:
            direction = direction / length
            arrow_size = 0.12

            # Find perpendicular vectors for arrowhead
            if abs(direction[1]) < 0.9:
                perp1 = np.cross(direction, np.array([0, 1, 0]))
            else:
                perp1 = np.cross(direction, np.array([1, 0, 0]))
            perp1 = perp1 / np.linalg.norm(perp1) * arrow_size

            perp2 = np.cross(direction, perp1)
            perp2 = perp2 / np.linalg.norm(perp2) * arrow_size

            arrow_base = end - direction * arrow_size * 2

            # Draw cone-like arrowhead
            glColor3f(*self.ROTATE_ARROW_END_COLOR)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(end[0], end[1], end[2])  # Tip

            num_cone_segments = 8
            for i in range(num_cone_segments + 1):
                angle = 2 * math.pi * i / num_cone_segments
                offset = perp1 * math.cos(angle) + perp2 * math.sin(angle)
                base_point = arrow_base + offset
                glVertex3f(base_point[0], base_point[1], base_point[2])

            glEnd()

        glLineWidth(1.0)

    def _draw_rotate_axis_handle(self):
        """Draw a draggable handle at the end of the axis arrow."""
        glPushMatrix()
        glTranslatef(self.rotate_axis_end[0], self.rotate_axis_end[1], self.rotate_axis_end[2])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Highlight when editing or hovering
        if self.is_editing_rotate_axis:
            glColor4f(1.0, 1.0, 0.0, 0.9)  # Bright yellow when dragging
            radius = 0.15
        elif self.rotate_hover_handle:
            glColor4f(*self.ROTATE_HANDLE_HOVER_COLOR, 0.9)  # Bright orange-yellow on hover
            radius = self.ROTATE_HANDLE_RADIUS * 1.2  # Slightly larger on hover
        else:
            glColor4f(*self.ROTATE_HANDLE_COLOR, 0.8)
            radius = self.ROTATE_HANDLE_RADIUS

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, radius, 16, 16)
        gluDeleteQuadric(quadric)

        glDisable(GL_BLEND)
        glPopMatrix()

    def _draw_rotation_disk(self):
        """
        Draw a circular disk/ring perpendicular to the rotation axis.
        This is the rotation gizmo that users can drag to rotate.
        """
        if self.rotate_axis_direction is None:
            return

        center = self.rotate_center
        axis = self.rotate_axis_direction

        # Find two perpendicular vectors to the axis for drawing the circle
        if abs(axis[1]) < 0.9:
            perp1 = np.cross(axis, np.array([0, 1, 0]))
        else:
            perp1 = np.cross(axis, np.array([1, 0, 0]))
        perp1 = perp1 / np.linalg.norm(perp1)

        perp2 = np.cross(axis, perp1)
        perp2 = perp2 / np.linalg.norm(perp2)

        # Choose color based on state: rotating > hovering > default
        if self.is_rotating:
            color = self.ROTATE_DISK_ACTIVE_COLOR
            line_width = 4.0
        elif self.rotate_hover_disk:
            color = self.ROTATE_DISK_HOVER_COLOR
            line_width = 3.5
        else:
            color = self.ROTATE_DISK_COLOR
            line_width = 3.0

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Draw the circular ring
        glLineWidth(line_width)
        glColor4f(*color, 0.8)
        glBegin(GL_LINE_LOOP)

        for i in range(self.ROTATE_DISK_SEGMENTS):
            angle = 2 * math.pi * i / self.ROTATE_DISK_SEGMENTS
            point = (center +
                     perp1 * math.cos(angle) * self.ROTATE_DISK_RADIUS +
                     perp2 * math.sin(angle) * self.ROTATE_DISK_RADIUS)
            glVertex3f(point[0], point[1], point[2])

        glEnd()

        # Draw a semi-transparent filled disk for better visibility
        glColor4f(*color, 0.15)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(center[0], center[1], center[2])  # Center

        for i in range(self.ROTATE_DISK_SEGMENTS + 1):
            angle = 2 * math.pi * i / self.ROTATE_DISK_SEGMENTS
            point = (center +
                     perp1 * math.cos(angle) * self.ROTATE_DISK_RADIUS +
                     perp2 * math.sin(angle) * self.ROTATE_DISK_RADIUS)
            glVertex3f(point[0], point[1], point[2])

        glEnd()

        # Draw small tick marks around the disk for visual feedback
        glColor4f(*color, 0.6)
        glLineWidth(2.0)
        glBegin(GL_LINES)

        for i in range(0, self.ROTATE_DISK_SEGMENTS, 4):  # Every 4th segment
            angle = 2 * math.pi * i / self.ROTATE_DISK_SEGMENTS
            inner_point = (center +
                          perp1 * math.cos(angle) * (self.ROTATE_DISK_RADIUS * 0.85) +
                          perp2 * math.sin(angle) * (self.ROTATE_DISK_RADIUS * 0.85))
            outer_point = (center +
                          perp1 * math.cos(angle) * self.ROTATE_DISK_RADIUS +
                          perp2 * math.sin(angle) * self.ROTATE_DISK_RADIUS)
            glVertex3f(inner_point[0], inner_point[1], inner_point[2])
            glVertex3f(outer_point[0], outer_point[1], outer_point[2])

        glEnd()

        glLineWidth(1.0)
        glDisable(GL_BLEND)

    def _draw_rotation_angle_display(self):
        """Draw the current rotation angle as text near the center."""
        if not self.is_rotating and abs(self.rotate_total_angle) < 0.01:
            return

        # Convert radians to degrees for display
        angle_degrees = math.degrees(self.rotate_total_angle)

        # Draw angle arc to show rotation amount
        if abs(self.rotate_total_angle) > 0.01:
            self._draw_angle_arc(angle_degrees)

    def _draw_angle_arc(self, angle_degrees):
        """Draw an arc showing the rotation angle."""
        if self.rotate_axis_direction is None:
            return

        center = self.rotate_center
        axis = self.rotate_axis_direction

        # Find perpendicular vectors
        if abs(axis[1]) < 0.9:
            perp1 = np.cross(axis, np.array([0, 1, 0]))
        else:
            perp1 = np.cross(axis, np.array([1, 0, 0]))
        perp1 = perp1 / np.linalg.norm(perp1)

        perp2 = np.cross(axis, perp1)
        perp2 = perp2 / np.linalg.norm(perp2)

        # Draw arc showing rotation amount
        arc_radius = self.ROTATE_DISK_RADIUS * 0.5
        angle_radians = math.radians(angle_degrees)

        # Determine arc direction and color
        if angle_degrees >= 0:
            glColor4f(0.2, 1.0, 0.2, 0.8)  # Green for positive
        else:
            glColor4f(1.0, 0.2, 0.2, 0.8)  # Red for negative

        glLineWidth(4.0)
        glBegin(GL_LINE_STRIP)

        # Draw arc from 0 to current angle
        num_arc_segments = max(3, int(abs(angle_degrees) / 5))
        for i in range(num_arc_segments + 1):
            t = i / num_arc_segments
            current_angle = t * angle_radians
            point = (center +
                     perp1 * math.cos(current_angle) * arc_radius +
                     perp2 * math.sin(current_angle) * arc_radius)
            glVertex3f(point[0], point[1], point[2])

        glEnd()

        # Draw line from center to arc start (reference line)
        glColor4f(1.0, 1.0, 1.0, 0.5)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        start_point = center + perp1 * arc_radius
        glVertex3f(center[0], center[1], center[2])
        glVertex3f(start_point[0], start_point[1], start_point[2])
        glEnd()

        glLineWidth(1.0)

    def _draw_rotation_drag_ui(self):
        """
        Draw 2D overlay UI showing drag direction when rotating.
        Shows: ← angle ● angle → with color coding
        """
        if not self.is_rotating or self.rotate_drag_start_screen_pos is None:
            return

        start_x, start_y = self.rotate_drag_start_screen_pos
        current_x = self.rotate_current_screen_x or start_x

        # Switch to 2D orthographic projection for screen-space drawing
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        width = self.width()
        height = self.height()
        glOrtho(0, width, height, 0, -1, 1)  # Y flipped for screen coords

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Line parameters
        line_length = 150  # pixels on each side
        line_y = start_y
        arrow_size = 12

        # Calculate angle for display
        angle_degrees = math.degrees(self.rotate_total_angle)

        # Draw left side (negative/red) ←
        glLineWidth(3.0)
        glColor4f(1.0, 0.3, 0.3, 0.9)  # Red
        glBegin(GL_LINES)
        glVertex2f(start_x, line_y)
        glVertex2f(start_x - line_length, line_y)
        glEnd()

        # Left arrow head
        glBegin(GL_TRIANGLES)
        glVertex2f(start_x - line_length, line_y)
        glVertex2f(start_x - line_length + arrow_size, line_y - arrow_size * 0.6)
        glVertex2f(start_x - line_length + arrow_size, line_y + arrow_size * 0.6)
        glEnd()

        # Draw right side (positive/green) →
        glColor4f(0.3, 1.0, 0.3, 0.9)  # Green
        glBegin(GL_LINES)
        glVertex2f(start_x, line_y)
        glVertex2f(start_x + line_length, line_y)
        glEnd()

        # Right arrow head
        glBegin(GL_TRIANGLES)
        glVertex2f(start_x + line_length, line_y)
        glVertex2f(start_x + line_length - arrow_size, line_y - arrow_size * 0.6)
        glVertex2f(start_x + line_length - arrow_size, line_y + arrow_size * 0.6)
        glEnd()

        # Draw center point (white circle)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glPointSize(10.0)
        glBegin(GL_POINTS)
        glVertex2f(start_x, line_y)
        glEnd()

        # Draw current position indicator (follows mouse)
        drag_offset = current_x - start_x
        if abs(drag_offset) > 5:
            # Color based on direction
            if drag_offset > 0:
                glColor4f(0.3, 1.0, 0.3, 1.0)  # Green for positive
            else:
                glColor4f(1.0, 0.3, 0.3, 1.0)  # Red for negative

            # Draw line from start to current
            glLineWidth(4.0)
            glBegin(GL_LINES)
            glVertex2f(start_x, line_y)
            glVertex2f(current_x, line_y)
            glEnd()

            # Draw current position marker
            glPointSize(14.0)
            glBegin(GL_POINTS)
            glVertex2f(current_x, line_y)
            glEnd()

        # Draw angle text background and text
        # Position text above the line
        text_y = line_y - 25

        # Draw angle value as a simple indicator bar
        angle_bar_width = min(abs(angle_degrees) * 2, 100)  # Scale angle to pixels
        if angle_degrees != 0:
            if angle_degrees > 0:
                glColor4f(0.3, 1.0, 0.3, 0.7)
                glBegin(GL_QUADS)
                glVertex2f(start_x, text_y - 8)
                glVertex2f(start_x + angle_bar_width, text_y - 8)
                glVertex2f(start_x + angle_bar_width, text_y + 8)
                glVertex2f(start_x, text_y + 8)
                glEnd()
            else:
                glColor4f(1.0, 0.3, 0.3, 0.7)
                glBegin(GL_QUADS)
                glVertex2f(start_x, text_y - 8)
                glVertex2f(start_x - angle_bar_width, text_y - 8)
                glVertex2f(start_x - angle_bar_width, text_y + 8)
                glVertex2f(start_x, text_y + 8)
                glEnd()

        glLineWidth(1.0)
        glPointSize(1.0)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

        # Restore matrices
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def _is_clicking_rotation_disk(self, screen_x, screen_y):
        """
        Check if clicking on or near the rotation disk.

        Projects the two disk axes (perp1, perp2) to screen space and checks
        if mouse is inside the resulting ellipse.
        """
        if self.rotate_center is None:
            return False

        # Project center to screen
        center_screen = self._project_point_to_screen(self.rotate_center)
        if center_screen is None:
            return False

        if self.rotate_axis_direction is None:
            # Fallback
            dx = screen_x - center_screen[0]
            dy = screen_y - center_screen[1]
            return math.sqrt(dx * dx + dy * dy) < 80

        axis = self.rotate_axis_direction

        # Find two perpendicular vectors to the axis (same as rendering)
        if abs(axis[1]) < 0.9:
            perp1 = np.cross(axis, np.array([0, 1, 0]))
        else:
            perp1 = np.cross(axis, np.array([1, 0, 0]))
        perp1 = perp1 / np.linalg.norm(perp1)

        perp2 = np.cross(axis, perp1)
        perp2 = perp2 / np.linalg.norm(perp2)

        # Project the two axis endpoints to screen (same axes used in drawing)
        axis1_3d = self.rotate_center + perp1 * self.ROTATE_DISK_RADIUS
        axis2_3d = self.rotate_center + perp2 * self.ROTATE_DISK_RADIUS

        axis1_screen = self._project_point_to_screen(axis1_3d)
        axis2_screen = self._project_point_to_screen(axis2_3d)

        if not axis1_screen or not axis2_screen:
            return False

        # Get screen-space axis vectors from center
        ax1 = np.array([axis1_screen[0] - center_screen[0],
                        axis1_screen[1] - center_screen[1]])
        ax2 = np.array([axis2_screen[0] - center_screen[0],
                        axis2_screen[1] - center_screen[1]])

        # Mouse offset from center
        mouse_offset = np.array([screen_x - center_screen[0],
                                 screen_y - center_screen[1]])

        # Solve for parametric coordinates (u, v) where:
        # mouse_offset = u * ax1 + v * ax2
        # If u² + v² <= 1, mouse is inside the disk

        # Build matrix [ax1 | ax2] and solve
        det = ax1[0] * ax2[1] - ax1[1] * ax2[0]

        if abs(det) < 0.001:
            # Axes are nearly parallel (disk viewed edge-on)
            # Fall back to distance check along the visible axis
            ax1_len = np.linalg.norm(ax1)
            ax2_len = np.linalg.norm(ax2)
            if ax1_len > ax2_len and ax1_len > 1:
                # Project mouse onto ax1
                proj = np.dot(mouse_offset, ax1) / (ax1_len * ax1_len)
                perp_dist = np.linalg.norm(mouse_offset - proj * ax1)
                return abs(proj) <= 1.3 and perp_dist < 15
            elif ax2_len > 1:
                proj = np.dot(mouse_offset, ax2) / (ax2_len * ax2_len)
                perp_dist = np.linalg.norm(mouse_offset - proj * ax2)
                return abs(proj) <= 1.3 and perp_dist < 15
            return False

        # Inverse of [ax1 | ax2] matrix
        inv_det = 1.0 / det
        u = inv_det * (ax2[1] * mouse_offset[0] - ax2[0] * mouse_offset[1])
        v = inv_det * (-ax1[1] * mouse_offset[0] + ax1[0] * mouse_offset[1])

        # Check if inside ellipse (with 30% tolerance for easier clicking)
        dist_squared = u * u + v * v
        return dist_squared <= 1.3 * 1.3  # 1.3 = 30% larger than visual

    def _rotate_mode_mouse_press(self, event):
        """Handle mouse press in rotate mode."""
        screen_x = event.x()
        screen_y = event.y()

        # If no set is selected yet, try to select one by clicking on a strand
        if not self.rotate_mode_active:
            clicked_strand = self._get_strand_at_screen_pos(screen_x, screen_y)
            if clicked_strand:
                # Extract set number from strand name
                parts = clicked_strand.name.split('_')
                if len(parts) >= 1:
                    set_number = parts[0]
                    self.select_set_for_rotation(set_number)
                    return True
            return False

        # Check if clicking on the axis handle to edit it (FIRST priority)
        if self._is_clicking_rotate_handle(screen_x, screen_y):
            self.is_editing_rotate_axis = True
            self.is_rotating = False  # Make sure we're not in rotation mode
            self.rotate_hover_handle = False
            self.rotate_hover_disk = False
            self.setCursor(Qt.ClosedHandCursor)
            print("Rotate: Editing axis direction")
            self.update()
            return True

        # Check if clicking on the rotation disk to start rotation (SECOND priority)
        if self._is_clicking_rotation_disk(screen_x, screen_y):
            self.rotate_hover_handle = False
            self.rotate_hover_disk = False
            self.setCursor(Qt.ClosedHandCursor)
            self._start_disk_rotation(screen_x, screen_y)
            return True

        # Click elsewhere - deselect
        self.rotate_mode_active = False
        self.rotate_selected_set = None
        self.rotate_center = None
        self.rotate_axis_end = None
        self.rotate_total_angle = 0.0
        self.update()
        return False

    def _start_disk_rotation(self, screen_x, screen_y=None):
        """Start rotation via disk drag."""
        if not self.rotate_mode_active or self.rotate_selected_set is None:
            return

        # Save state for undo
        if hasattr(self, 'undo_redo_manager') and self.undo_redo_manager:
            self.undo_redo_manager.save_state()

        self.is_rotating = True
        self.is_editing_rotate_axis = False  # Make sure we're not editing axis
        self.rotate_angle = 0.0
        self.rotate_last_screen_x = screen_x
        self.rotate_drag_start_x = screen_x
        self.rotate_current_screen_x = screen_x

        # Store screen position for UI overlay
        if screen_y is not None:
            self.rotate_drag_start_screen_pos = (screen_x, screen_y)
        else:
            # Get Y from center projection if not provided
            center_screen = self._project_point_to_screen(self.rotate_center)
            if center_screen:
                self.rotate_drag_start_screen_pos = (screen_x, center_screen[1])
            else:
                self.rotate_drag_start_screen_pos = (screen_x, self.height() // 2)

        # Reset frame timer for 30 FPS limiting
        if hasattr(self, '_last_rotate_frame_time'):
            self._last_rotate_frame_time = 0.0

        print("Rotate: Started disk rotation - drag left/right to rotate (30 FPS, low-res mesh)")

    def _is_clicking_rotate_handle(self, screen_x, screen_y):
        """Check if clicking on the axis arrow handle."""
        if self.rotate_axis_end is None:
            return False

        screen_pos = self._project_point_to_screen(self.rotate_axis_end)
        if screen_pos is None:
            return False

        dx = screen_pos[0] - screen_x
        dy = screen_pos[1] - screen_y
        dist = math.sqrt(dx * dx + dy * dy)

        return dist < 25  # 25 pixel threshold

    def _is_clicking_rotate_center(self, screen_x, screen_y):
        """Check if clicking on the rotation center."""
        if self.rotate_center is None:
            return False

        screen_pos = self._project_point_to_screen(self.rotate_center)
        if screen_pos is None:
            return False

        dx = screen_pos[0] - screen_x
        dy = screen_pos[1] - screen_y
        dist = math.sqrt(dx * dx + dy * dy)

        return dist < 25  # 25 pixel threshold

    def _start_rotation(self, screen_y):
        """Start the rotation operation."""
        if not self.rotate_mode_active or self.rotate_selected_set is None:
            return

        # Save state for undo
        if hasattr(self, 'undo_redo_manager') and self.undo_redo_manager:
            self.undo_redo_manager.save_state()

        self.is_rotating = True
        self.rotate_angle = 0.0
        self.rotate_last_screen_y = screen_y
        print("Rotate: Started rotation - drag up/down to rotate")

    def _rotate_mode_mouse_move(self, event):
        """Handle mouse move in rotate mode."""
        screen_x = event.x()
        screen_y = event.y()

        # IMPORTANT: These are mutually exclusive operations
        # Once you start one, you can't switch to the other until mouse release

        if self.is_editing_rotate_axis:
            # Update axis direction based on mouse position
            self._update_rotate_axis(screen_x, screen_y)
            return True

        if self.is_rotating:
            # Perform rotation based on horizontal (left/right) mouse movement
            self._update_disk_rotation(screen_x)
            return True

        # Hover detection when not actively dragging
        if self.rotate_mode_active:
            prev_hover_handle = self.rotate_hover_handle
            prev_hover_disk = self.rotate_hover_disk

            # Check handle first (higher priority)
            self.rotate_hover_handle = self._is_clicking_rotate_handle(screen_x, screen_y)

            # Check disk only if not hovering handle
            if not self.rotate_hover_handle:
                self.rotate_hover_disk = self._is_clicking_rotation_disk(screen_x, screen_y)
            else:
                self.rotate_hover_disk = False

            # Update cursor based on hover state
            if self.rotate_hover_handle or self.rotate_hover_disk:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

            # Redraw if hover state changed
            if (prev_hover_handle != self.rotate_hover_handle or
                    prev_hover_disk != self.rotate_hover_disk):
                self.update()

            return self.rotate_hover_handle or self.rotate_hover_disk

        return False

    def _update_disk_rotation(self, screen_x):
        """Update rotation based on horizontal mouse movement (dragging left/right on disk)."""
        # Always track current X for UI drawing
        self.rotate_current_screen_x = screen_x

        # FPS limiting - skip if too soon since last frame (30 FPS)
        if hasattr(self, '_should_process_rotate_frame') and not self._should_process_rotate_frame():
            self.update()  # Still update to redraw UI
            return

        if self.rotate_last_screen_x is None:
            self.rotate_last_screen_x = screen_x
            return

        screen_dx = screen_x - self.rotate_last_screen_x
        self.rotate_last_screen_x = screen_x

        # Convert horizontal screen movement to angle
        # Dragging right = positive rotation, left = negative
        angle_speed = 0.01  # Radians per pixel
        angle_delta = screen_dx * angle_speed

        self.rotate_angle += angle_delta
        self.rotate_total_angle += angle_delta

        # Apply rotation to all strands in the group
        self._apply_rotation()
        self.update()

    def _update_rotate_axis(self, screen_x, screen_y):
        """
        Update the rotation axis based on mouse position.

        In XZ mode: Move the handle on the XZ plane (horizontal), keeping current Y
        In Y mode: Move the handle vertically (Y axis), keeping current XZ position

        This allows building up the 3D position incrementally:
        1. First set XZ position in XZ mode
        2. Then switch to Y mode to adjust height while keeping XZ
        """
        if self.rotate_center is None or self.rotate_axis_end is None:
            return

        # Make a copy of current axis end to preserve components
        current_end = self.rotate_axis_end.copy()

        if self.rotate_axis_mode == "vertical":
            # Y axis movement - move axis end vertically, KEEP current X and Z
            new_pos = self._screen_to_vertical_plane(screen_x, screen_y, self.rotate_axis_end)
            if new_pos:
                new_pos = np.array(new_pos)
                # Only update Y, preserve X and Z from current position
                self.rotate_axis_end = np.array([
                    current_end[0],  # Keep X
                    new_pos[1],      # Update Y
                    current_end[2]   # Keep Z
                ])
        else:
            # XZ plane movement - KEEP current Y
            new_pos = self._screen_to_ground(screen_x, screen_y, ground_y=current_end[1])
            if new_pos:
                new_pos = np.array(new_pos)
                # Only update X and Z, preserve Y from current position
                self.rotate_axis_end = np.array([
                    new_pos[0],      # Update X
                    current_end[1],  # Keep Y
                    new_pos[2]       # Update Z
                ])

        # Update direction (normalized) and normalize to ARROW_LENGTH
        direction = self.rotate_axis_end - self.rotate_center
        dir_length = np.linalg.norm(direction)
        if dir_length > 0.01:
            self.rotate_axis_direction = direction / dir_length
            self.rotate_axis_end = self.rotate_center + self.rotate_axis_direction * self.ROTATE_ARROW_LENGTH

        self.update()

    def _update_rotation(self, screen_y):
        """Update the rotation angle based on mouse Y movement."""
        if self.rotate_last_screen_y is None:
            self.rotate_last_screen_y = screen_y
            return

        screen_dy = screen_y - self.rotate_last_screen_y
        self.rotate_last_screen_y = screen_y

        # Convert screen movement to angle
        angle_speed = 0.01  # Radians per pixel
        angle_delta = -screen_dy * angle_speed

        self.rotate_angle += angle_delta

        # Apply rotation to all strands in the group
        self._apply_rotation()
        self.update()

    def _apply_rotation(self):
        """Apply the current rotation to all strands in the selected set."""
        if not self.rotate_selected_set or self.rotate_axis_direction is None:
            return

        set_prefix = f"{self.rotate_selected_set}_"
        group_strands = [s for s in self.strands if s.name.startswith(set_prefix)]

        for strand in group_strands:
            if strand.name not in self.rotate_initial_positions:
                continue

            initial = self.rotate_initial_positions[strand.name]

            # Rotate each point around the axis
            strand.start = self._rotate_point_around_axis(
                initial['start'],
                self.rotate_center,
                self.rotate_axis_direction,
                self.rotate_angle
            )

            strand.end = self._rotate_point_around_axis(
                initial['end'],
                self.rotate_center,
                self.rotate_axis_direction,
                self.rotate_angle
            )

            strand.control_point1 = self._rotate_point_around_axis(
                initial['cp1'],
                self.rotate_center,
                self.rotate_axis_direction,
                self.rotate_angle
            )

            strand.control_point2 = self._rotate_point_around_axis(
                initial['cp2'],
                self.rotate_center,
                self.rotate_axis_direction,
                self.rotate_angle
            )

            strand._mark_geometry_dirty()

    def _rotate_point_around_axis(self, point, center, axis, angle):
        """
        Rotate a point around an axis using Rodrigues' rotation formula.

        Args:
            point: Point to rotate [x, y, z]
            center: Center of rotation [x, y, z]
            axis: Normalized rotation axis [x, y, z]
            angle: Rotation angle in radians

        Returns:
            Rotated point [x, y, z]
        """
        # Translate point to origin
        p = np.array(point) - np.array(center)

        # Rodrigues' formula
        cos_angle = np.cos(angle)
        sin_angle = np.sin(angle)
        k = np.array(axis)

        term1 = p * cos_angle
        term2 = np.cross(k, p) * sin_angle
        term3 = k * np.dot(k, p) * (1 - cos_angle)

        p_rotated = term1 + term2 + term3

        # Translate back
        return p_rotated + np.array(center)

    def _rotate_mode_mouse_release(self, event):
        """Handle mouse release in rotate mode."""
        if self.is_editing_rotate_axis:
            self.is_editing_rotate_axis = False
            self.setCursor(Qt.ArrowCursor)
            print("Rotate: Axis editing stopped")
            self.update()
            return True

        if self.is_rotating:
            self.is_rotating = False
            self.rotate_last_screen_x = None
            self.rotate_drag_start_x = None
            self.rotate_drag_start_screen_pos = None  # Clear drag UI
            self.rotate_current_screen_x = None
            # Reset initial positions for next rotation (keep current positions as new base)
            if self.rotate_selected_set:
                set_prefix = f"{self.rotate_selected_set}_"
                group_strands = [s for s in self.strands if s.name.startswith(set_prefix)]
                for strand in group_strands:
                    self.rotate_initial_positions[strand.name] = {
                        'start': strand.start.copy(),
                        'end': strand.end.copy(),
                        'cp1': strand.control_point1.copy(),
                        'cp2': strand.control_point2.copy()
                    }
            self.rotate_angle = 0.0
            self.setCursor(Qt.ArrowCursor)
            angle_degrees = math.degrees(self.rotate_total_angle)
            print(f"Rotate: Rotation completed (total: {angle_degrees:.1f}°)")
            self.update()
            return True

        return False

    def _rotate_mode_wheel(self, event):
        """
        Handle mouse wheel for rotation.
        Scroll up = rotate positive, scroll down = rotate negative.
        """
        if not self.rotate_mode_active or self.rotate_selected_set is None:
            return False

        # Check if mouse is over the rotation area (center or disk)
        screen_x = event.x()
        screen_y = event.y()

        is_over_disk = self._is_clicking_rotation_disk(screen_x, screen_y)
        is_over_center = self._is_clicking_rotate_center(screen_x, screen_y)

        if not is_over_disk and not is_over_center:
            return False  # Let normal wheel handling occur

        # Don't allow wheel rotation while dragging axis
        if self.is_editing_rotate_axis:
            return False

        # Save state for undo (only on first wheel movement of a sequence)
        if hasattr(self, 'undo_redo_manager') and self.undo_redo_manager:
            # Only save state if we haven't saved recently
            if not hasattr(self, '_wheel_undo_saved') or not self._wheel_undo_saved:
                self.undo_redo_manager.save_state()
                self._wheel_undo_saved = True

        # Get wheel delta
        delta = event.angleDelta().y()

        # Convert wheel delta to rotation angle
        # Typical delta is 120 per notch, we want small increments
        angle_per_notch = math.radians(5)  # 5 degrees per notch
        angle_delta = (delta / 120.0) * angle_per_notch

        self.rotate_angle += angle_delta
        self.rotate_total_angle += angle_delta

        # Apply rotation
        self._apply_rotation()

        # Update initial positions after wheel rotation
        if self.rotate_selected_set:
            set_prefix = f"{self.rotate_selected_set}_"
            group_strands = [s for s in self.strands if s.name.startswith(set_prefix)]
            for strand in group_strands:
                self.rotate_initial_positions[strand.name] = {
                    'start': strand.start.copy(),
                    'end': strand.end.copy(),
                    'cp1': strand.control_point1.copy(),
                    'cp2': strand.control_point2.copy()
                }
        self.rotate_angle = 0.0

        self.update()
        return True

    def _rotate_mode_wheel_end(self):
        """Called when wheel scrolling stops (for undo state management)."""
        if hasattr(self, '_wheel_undo_saved'):
            self._wheel_undo_saved = False

    def _get_strand_at_screen_pos(self, screen_x, screen_y):
        """Find a strand near the given screen position."""
        min_dist = float('inf')
        closest = None
        threshold = 30  # Screen pixels

        for strand in self.strands:
            if not strand.visible:
                continue

            # Check distance to strand center
            center = (strand.start + strand.end) / 2
            screen_pos = self._project_point_to_screen(center)
            if screen_pos is None:
                continue

            dx = screen_pos[0] - screen_x
            dy = screen_pos[1] - screen_y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < threshold and dist < min_dist:
                min_dist = dist
                closest = strand

        return closest

    def set_rotate_axis_mode(self, mode):
        """
        Set the rotation axis mode (normal/vertical).

        This changes which axis mouse movement controls, but does NOT reset
        the current axis position. This allows:
        1. Set XZ position in XZ mode
        2. Switch to Y mode to adjust height while keeping XZ position
        """
        self.rotate_axis_mode = mode
        print(f"Rotate axis mode: {mode} (preserving current axis position)")

    def _screen_to_vertical_plane(self, screen_x, screen_y, reference_point):
        """Convert screen coordinates to a point on a vertical plane through reference_point."""
        self.makeCurrent()

        # Account for device pixel ratio
        dpr = int(self.devicePixelRatioF())
        screen_x = screen_x * dpr
        screen_y = screen_y * dpr

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        width = self.width() * dpr
        height = (self.height() * dpr) if self.height() > 0 else 1
        aspect = width / height
        gluPerspective(45.0, aspect, 0.1, 1000.0)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        azimuth_rad = math.radians(self.camera_azimuth)
        elevation_rad = math.radians(self.camera_elevation)

        camera_x = self.camera_target[0] + self.camera_distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
        camera_y = self.camera_target[1] + self.camera_distance * math.sin(elevation_rad)
        camera_z = self.camera_target[2] + self.camera_distance * math.cos(elevation_rad) * math.cos(azimuth_rad)

        gluLookAt(
            camera_x, camera_y, camera_z,
            self.camera_target[0], self.camera_target[1], self.camera_target[2],
            0.0, 1.0, 0.0
        )

        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)

        win_y = viewport[3] - screen_y

        result = None
        try:
            near_point = gluUnProject(screen_x, win_y, 0.0, modelview, projection, viewport)
            far_point = gluUnProject(screen_x, win_y, 1.0, modelview, projection, viewport)

            ray_dir = np.array(far_point) - np.array(near_point)
            ray_origin = np.array(near_point)

            # Create vertical plane through reference point, facing camera
            plane_normal = np.array([
                math.sin(azimuth_rad),
                0,
                math.cos(azimuth_rad)
            ])

            # Ray-plane intersection
            denom = np.dot(ray_dir, plane_normal)
            if abs(denom) > 1e-6:
                t = np.dot(np.array(reference_point) - ray_origin, plane_normal) / denom
                if t >= 0:
                    result = tuple(ray_origin + t * ray_dir)

        except Exception as e:
            print(f"Error in _screen_to_vertical_plane: {e}")

        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        return result
