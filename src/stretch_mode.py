"""
OpenStrandStudio 3D - Stretch Mode
Handles stretch mode functionality for auto-stretching endpoints until collision.
"""

import math
import numpy as np
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *


class StretchModeMixin:
    """
    Mixin class providing stretch mode functionality.

    This class should be inherited by StrandDrawingCanvas along with other mixins.
    It provides methods for:
    - Drawing free endpoint indicators
    - Selecting endpoints for stretching
    - Setting stretch direction via drag
    - Auto-stretching until collision with 2x thickness margin
    """

    # Stretch mode visual settings
    FREE_ENDPOINT_RADIUS = 0.2  # Radius of free endpoint spheres
    FREE_ENDPOINT_COLOR = (0.2, 0.8, 0.2)  # Green for available endpoints
    SELECTED_ENDPOINT_COLOR = (1.0, 1.0, 0.0)  # Yellow for selected
    DIRECTION_LINE_COLOR = (1.0, 0.5, 0.0)  # Orange for direction indicator

    # Collision settings
    COLLISION_THICKNESS_MULTIPLIER = 2.0  # Treat strands as 2x thicker for collision
    STRETCH_STEP = 0.02  # How much to move per iteration
    MAX_STRETCH_ITERATIONS = 10000  # Safety limit

    def _init_stretch_mode(self):
        """Initialize stretch mode state variables."""
        self.stretch_selected_endpoint = None  # (strand, 'start' or 'end')
        self.stretch_direction = None  # Direction vector for stretching (normalized)
        self.stretch_vector_end = None  # End point of the editable 1-unit vector
        self.stretch_drag_start = None  # Starting position of drag
        self.stretch_axis_mode = "normal"  # 'normal' (XZ), 'vertical' (Y), 'depth'
        self.is_editing_vector = False  # True while editing the direction vector
        self.free_endpoints = []  # List of (strand, endpoint_type, position)
        self.VECTOR_LENGTH = 1.0  # Length of the direction vector

    def _enter_stretch_mode(self):
        """Called when entering stretch mode."""
        self._init_stretch_mode()
        self._find_free_endpoints()
        self.update()

    def _exit_stretch_mode(self):
        """Called when exiting stretch mode."""
        # Only reset if stretch mode was initialized
        if hasattr(self, 'stretch_selected_endpoint'):
            self.stretch_selected_endpoint = None
            self.stretch_direction = None
            self.stretch_drag_start = None
            self.is_stretching = False
            self.free_endpoints = []

    def _find_free_endpoints(self):
        """Find all free endpoints (ends that are not attached to anything)."""
        self.free_endpoints = []

        for strand in self.strands:
            if not strand.visible:
                continue

            # Check if this strand's END is free
            end_is_free = True

            # Check if any strand is attached to this strand's end
            for other in self.strands:
                if hasattr(other, 'parent_strand') and other.parent_strand == strand:
                    if hasattr(other, 'attachment_side') and other.attachment_side == 1:
                        end_is_free = False
                        break

            # Also check the end_attached flag
            if hasattr(strand, 'end_attached') and strand.end_attached:
                end_is_free = False

            if end_is_free:
                self.free_endpoints.append((strand, 'end', strand.end.copy()))

            # For regular strands (not attached), also check START
            if not hasattr(strand, 'parent_strand'):
                start_is_free = True

                # Check if any strand is attached to this strand's start
                for other in self.strands:
                    if hasattr(other, 'parent_strand') and other.parent_strand == strand:
                        if hasattr(other, 'attachment_side') and other.attachment_side == 0:
                            start_is_free = False
                            break

                if start_is_free:
                    self.free_endpoints.append((strand, 'start', strand.start.copy()))

    def _draw_stretch_mode_indicators(self):
        """Draw visual indicators for stretch mode."""
        if self.current_mode != "stretch":
            return

        # Safety check - make sure stretch mode is initialized
        if not hasattr(self, 'free_endpoints'):
            return

        glDisable(GL_LIGHTING)

        # Draw free endpoint spheres
        for strand, endpoint_type, position in self.free_endpoints:
            # Check if this is the selected endpoint
            is_selected = (
                self.stretch_selected_endpoint is not None and
                self.stretch_selected_endpoint[0] == strand and
                self.stretch_selected_endpoint[1] == endpoint_type
            )

            if is_selected:
                color = self.SELECTED_ENDPOINT_COLOR
                radius = self.FREE_ENDPOINT_RADIUS * 1.3
            else:
                color = self.FREE_ENDPOINT_COLOR
                radius = self.FREE_ENDPOINT_RADIUS

            # Get current position (may have moved)
            if endpoint_type == 'end':
                pos = strand.end
            else:
                pos = strand.start

            self._draw_endpoint_sphere(pos, radius, color)

        # Draw editable direction vector if endpoint is selected
        if self.stretch_selected_endpoint and self.stretch_vector_end is not None:
            strand, endpoint_type = self.stretch_selected_endpoint
            if endpoint_type == 'end':
                start_pos = strand.end
            else:
                start_pos = strand.start

            # Draw the direction vector line
            self._draw_direction_line(start_pos, self.stretch_vector_end)

            # Draw draggable sphere at vector end
            self._draw_vector_end_handle(self.stretch_vector_end)

        glEnable(GL_LIGHTING)

    def _draw_vector_end_handle(self, position):
        """Draw a draggable handle at the end of the direction vector."""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])

        # Orange sphere for the handle
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Highlight if being dragged
        if self.is_editing_vector:
            glColor4f(1.0, 1.0, 0.0, 0.9)  # Bright yellow when dragging
            radius = 0.15
        else:
            glColor4f(1.0, 0.5, 0.0, 0.8)  # Orange normally
            radius = 0.12

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, radius, 16, 16)
        gluDeleteQuadric(quadric)

        glDisable(GL_BLEND)
        glPopMatrix()

    def _draw_endpoint_sphere(self, position, radius, color):
        """Draw a sphere at the given position."""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])

        # Semi-transparent
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(color[0], color[1], color[2], 0.7)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, radius, 16, 16)
        gluDeleteQuadric(quadric)

        glDisable(GL_BLEND)
        glPopMatrix()

    def _draw_direction_line(self, start, end):
        """Draw a line indicating stretch direction."""
        glColor3f(*self.DIRECTION_LINE_COLOR)
        glLineWidth(3.0)

        glBegin(GL_LINES)
        glVertex3f(start[0], start[1], start[2])
        glVertex3f(end[0], end[1], end[2])
        glEnd()

        # Draw arrowhead
        direction = end - start
        length = np.linalg.norm(direction)
        if length > 0.1:
            direction = direction / length
            # Simple arrowhead
            arrow_size = 0.15
            perp = np.array([-direction[2], 0, direction[0]])
            if np.linalg.norm(perp) < 0.01:
                perp = np.array([0, 1, 0])
            perp = perp / np.linalg.norm(perp) * arrow_size

            arrow_base = end - direction * arrow_size * 2

            glBegin(GL_TRIANGLES)
            glVertex3f(end[0], end[1], end[2])
            glVertex3f(arrow_base[0] + perp[0], arrow_base[1] + perp[1], arrow_base[2] + perp[2])
            glVertex3f(arrow_base[0] - perp[0], arrow_base[1] - perp[1], arrow_base[2] - perp[2])
            glEnd()

        glLineWidth(1.0)

    def _stretch_mode_mouse_press(self, event):
        """Handle mouse press in stretch mode."""
        screen_x = event.x()
        screen_y = event.y()

        # First, check if clicking on the vector end handle (if a vector exists)
        if self.stretch_selected_endpoint and self.stretch_vector_end is not None:
            if self._is_clicking_vector_handle(screen_x, screen_y):
                # Start editing the vector
                self.is_editing_vector = True
                print("Stretch: Editing direction vector")
                self.update()
                return True

        # Check if clicking on a free endpoint to select it
        clicked_endpoint = self._get_clicked_endpoint(screen_x, screen_y)

        if clicked_endpoint:
            strand, endpoint_type = clicked_endpoint

            # Get the endpoint position
            if endpoint_type == 'end':
                endpoint_pos = strand.end.copy()
            else:
                endpoint_pos = strand.start.copy()

            # If clicking on already selected endpoint, deselect it
            if (self.stretch_selected_endpoint and
                self.stretch_selected_endpoint[0] == strand and
                self.stretch_selected_endpoint[1] == endpoint_type):
                self.stretch_selected_endpoint = None
                self.stretch_vector_end = None
                self.stretch_direction = None
                print(f"Stretch: Deselected {strand.name} {endpoint_type}")
            else:
                # Select this endpoint and create default direction vector
                self.stretch_selected_endpoint = (strand, endpoint_type)

                # Default direction: along the strand direction (outward)
                if endpoint_type == 'end':
                    direction = strand.end - strand.start
                else:
                    direction = strand.start - strand.end

                dir_len = np.linalg.norm(direction)
                if dir_len > 1e-6:
                    direction = direction / dir_len
                else:
                    direction = np.array([0.0, 1.0, 0.0])  # Default up

                self.stretch_direction = direction
                self.stretch_vector_end = endpoint_pos + direction * self.VECTOR_LENGTH
                print(f"Stretch: Selected {strand.name} {endpoint_type}")

            self.update()
            return True

        return False

    def _is_clicking_vector_handle(self, screen_x, screen_y):
        """Check if clicking on the vector end handle."""
        if self.stretch_vector_end is None:
            return False

        screen_pos = self._project_point_to_screen(self.stretch_vector_end)
        if screen_pos is None:
            return False

        dx = screen_pos[0] - screen_x
        dy = screen_pos[1] - screen_y
        dist = math.sqrt(dx * dx + dy * dy)

        return dist < 20  # 20 pixel threshold

    def _stretch_mode_mouse_move(self, event):
        """Handle mouse move in stretch mode (during vector editing)."""
        if not self.is_editing_vector or not self.stretch_selected_endpoint:
            return False

        screen_x = event.x()
        screen_y = event.y()

        strand, endpoint_type = self.stretch_selected_endpoint

        # Get the endpoint position (vector start)
        if endpoint_type == 'end':
            endpoint_pos = strand.end
        else:
            endpoint_pos = strand.start

        # Calculate new vector end position based on axis mode
        if self.stretch_axis_mode == "vertical":
            # Y axis movement - move vector end vertically
            new_pos = self._screen_to_vertical_plane(screen_x, screen_y, self.stretch_vector_end)
            if new_pos:
                new_pos = np.array(new_pos)
                # Keep X and Z from current vector end, only change Y
                self.stretch_vector_end[1] = new_pos[1]
        elif self.stretch_axis_mode == "depth":
            # Depth movement (toward/away from camera)
            if not hasattr(self, '_stretch_last_screen_y'):
                self._stretch_last_screen_y = screen_y

            delta_y = screen_y - self._stretch_last_screen_y
            self._stretch_last_screen_y = screen_y

            # Get camera direction (horizontal only)
            azimuth_rad = math.radians(self.camera_azimuth)
            depth_dir = np.array([
                math.sin(azimuth_rad),
                0,
                math.cos(azimuth_rad)
            ])
            self.stretch_vector_end = self.stretch_vector_end + depth_dir * delta_y * 0.02
        else:
            # Normal XZ plane movement
            new_pos = self._screen_to_ground(screen_x, screen_y, ground_y=self.stretch_vector_end[1])
            if new_pos:
                new_pos = np.array(new_pos)
                # Keep Y from current vector end, only change X and Z
                self.stretch_vector_end[0] = new_pos[0]
                self.stretch_vector_end[2] = new_pos[2]

        # Update direction (normalized) based on new vector end
        direction = self.stretch_vector_end - endpoint_pos
        dir_length = np.linalg.norm(direction)
        if dir_length > 0.01:
            self.stretch_direction = direction / dir_length
            # Normalize vector to VECTOR_LENGTH
            self.stretch_vector_end = endpoint_pos + self.stretch_direction * self.VECTOR_LENGTH

        self.update()
        return True

    def _stretch_mode_mouse_release(self, event):
        """Handle mouse release in stretch mode - stops editing vector."""
        if not self.is_editing_vector:
            return False

        # Clean up depth tracking
        if hasattr(self, '_stretch_last_screen_y'):
            delattr(self, '_stretch_last_screen_y')

        # Stop editing, but keep the vector visible
        self.is_editing_vector = False
        print("Stretch: Vector editing stopped. Click 'Go!' to execute stretch.")
        self.update()
        return True

    def execute_stretch(self):
        """Execute the auto-stretch with the current direction vector."""
        if not self.stretch_selected_endpoint or self.stretch_direction is None:
            print("Stretch: No endpoint selected or no direction set")
            return False

        # Save state for undo
        if hasattr(self, 'undo_redo_manager') and self.undo_redo_manager:
            self.undo_redo_manager.save_state()

        # Perform auto-stretch
        self._perform_auto_stretch()

        # Clear selection after stretching
        self.stretch_selected_endpoint = None
        self.stretch_vector_end = None
        self.stretch_direction = None

        # Refresh free endpoints list
        self._find_free_endpoints()

        self.update()
        return True

    def _get_clicked_endpoint(self, screen_x, screen_y):
        """Check if a free endpoint was clicked."""
        min_dist = float('inf')
        closest = None
        threshold = 25  # Screen pixels

        for strand, endpoint_type, _ in self.free_endpoints:
            # Get current position
            if endpoint_type == 'end':
                pos = strand.end
            else:
                pos = strand.start

            # Project to screen
            screen_pos = self._project_point_to_screen(pos)
            if screen_pos is None:
                continue

            # Check distance
            dx = screen_pos[0] - screen_x
            dy = screen_pos[1] - screen_y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < threshold and dist < min_dist:
                min_dist = dist
                closest = (strand, endpoint_type)

        return closest

    def _perform_auto_stretch(self):
        """Auto-stretch the selected endpoint until near-collision."""
        if not self.stretch_selected_endpoint or self.stretch_direction is None:
            return

        strand, endpoint_type = self.stretch_selected_endpoint
        direction = self.stretch_direction

        print(f"Stretch: Auto-stretching {strand.name} {endpoint_type} in direction {direction}")

        # Get collision radius (2x thickness)
        tube_radius = strand.width if hasattr(strand, 'width') else 0.15
        collision_radius = tube_radius * self.COLLISION_THICKNESS_MULTIPLIER

        # Iteratively move until collision
        for iteration in range(self.MAX_STRETCH_ITERATIONS):
            # Check if moving would cause collision
            if self._would_collide_after_move(strand, endpoint_type, direction, self.STRETCH_STEP, collision_radius):
                print(f"Stretch: Stopped at iteration {iteration} (collision detected)")
                break

            # Move the endpoint
            self._move_endpoint(strand, endpoint_type, direction * self.STRETCH_STEP)
        else:
            print(f"Stretch: Reached max iterations ({self.MAX_STRETCH_ITERATIONS})")

        # Refresh free endpoints list
        self._find_free_endpoints()

    def _move_endpoint(self, strand, endpoint_type, delta):
        """Move a strand's endpoint by delta, adjusting control points."""
        if endpoint_type == 'end':
            strand.end = strand.end + delta
            strand.control_point2 = strand.control_point2 + delta
        else:
            strand.start = strand.start + delta
            strand.control_point1 = strand.control_point1 + delta

        strand._mark_geometry_dirty()

    def _would_collide_after_move(self, moving_strand, endpoint_type, direction, step, collision_radius):
        """Check if moving would cause a collision with ANY other strand."""
        # Calculate new position after move
        if endpoint_type == 'end':
            new_pos = moving_strand.end + direction * step
        else:
            new_pos = moving_strand.start + direction * step

        # Sample points along the moving strand (with new position)
        moving_points = self._sample_strand_curve(moving_strand, endpoint_type, new_pos)

        # Check against ALL other strands (not just different chains)
        for other_strand in self.strands:
            if not other_strand.visible:
                continue

            # Skip the moving strand itself (but NOT other strands in same chain)
            if other_strand == moving_strand:
                continue

            # Sample other strand
            other_points = self._sample_strand_curve(other_strand)

            # Check segment distances between all segment pairs
            for i in range(len(moving_points) - 1):
                for j in range(len(other_points) - 1):
                    dist = self._segment_distance(
                        moving_points[i], moving_points[i + 1],
                        other_points[j], other_points[j + 1]
                    )

                    # Collision if distance less than combined radii (2x each for safety margin)
                    if dist < collision_radius * 2:
                        return True

        return False

    def _sample_strand_curve(self, strand, modified_endpoint=None, new_position=None, num_samples=15):
        """Sample points along a strand's Bezier curve."""
        p0 = strand.start.copy()
        p1 = strand.control_point1.copy()
        p2 = strand.control_point2.copy()
        p3 = strand.end.copy()

        # Apply modification if specified
        if modified_endpoint == 'end' and new_position is not None:
            delta = new_position - p3
            p3 = new_position
            p2 = p2 + delta
        elif modified_endpoint == 'start' and new_position is not None:
            delta = new_position - p0
            p0 = new_position
            p1 = p1 + delta

        points = []
        for i in range(num_samples + 1):
            t = i / num_samples
            # Cubic Bezier
            point = (
                (1 - t) ** 3 * p0 +
                3 * (1 - t) ** 2 * t * p1 +
                3 * (1 - t) * t ** 2 * p2 +
                t ** 3 * p3
            )
            points.append(point)

        return points

    def _segment_distance(self, p1, p2, q1, q2):
        """Compute minimum distance between two line segments."""
        d1 = p2 - p1
        d2 = q2 - q1
        r = p1 - q1

        a = np.dot(d1, d1)
        b = np.dot(d1, d2)
        c = np.dot(d2, d2)
        d = np.dot(d1, r)
        e = np.dot(d2, r)

        denom = a * c - b * b

        if denom < 1e-10:
            s = 0.0
            t = d / b if abs(b) > 1e-10 else 0.0
        else:
            s = (b * e - c * d) / denom
            t = (a * e - b * d) / denom

        s = max(0.0, min(1.0, s))
        t = max(0.0, min(1.0, t))

        closest1 = p1 + s * d1
        closest2 = q1 + t * d2

        return np.linalg.norm(closest1 - closest2)

    def set_stretch_axis_mode(self, mode):
        """Set the stretch axis mode (normal/vertical/depth)."""
        self.stretch_axis_mode = mode
        print(f"Stretch axis mode: {mode}")
