"""
OpenStrandStudio 3D - Move Mode
Handles all move mode functionality for the canvas
"""

import math
import numpy as np
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *


class MoveModeMixin:
    """
    Mixin class providing move mode functionality.

    This class should be inherited by StrandDrawingCanvas along with other mixins.
    It provides methods for:
    - Drawing control point indicators (sphere for CP1, cone for CP2)
    - Drawing tube dashes connecting endpoints to control points
    - Hover detection for control points
    - Moving strands and control points
    - Propagating movement to connected strands
    """

    # Control point visual settings
    CP_SPHERE_RADIUS = 0.12      # Radius of CP1 sphere
    CP_CONE_RADIUS = 0.12        # Base radius of CP2 cone
    CP_CONE_HEIGHT = 0.25        # Height of CP2 cone
    CP_COLOR = (0.0, 0.85, 0.0)  # Green color for control points
    DASH_RADIUS = 0.03           # Radius of tube dashes
    DASH_LENGTH = 0.15           # Length of each dash segment
    DASH_GAP = 0.1               # Gap between dashes

    def _draw_control_points(self):
        """
        Draw control points for strands.

        Normal mode: Show CPs for ALL visible strands (green sphere/cone + dashes, no boxes)
        Move mode: Show CPs only for SELECTED strand (with red/yellow boxes)
        """
        if self.current_mode == "move":
            # Move mode: only selected strand with boxes
            if self.selected_strand is not None and self.selected_strand.visible:
                self._draw_strand_control_points(self.selected_strand, show_boxes=True)
        else:
            # Normal mode: all visible strands without boxes
            for strand in self.strands:
                if strand.visible:
                    self._draw_strand_control_points(strand, show_boxes=False)

    def _draw_strand_control_points(self, strand, show_boxes=False):
        """
        Draw control points for a single strand.

        Args:
            strand: The strand to draw control points for
            show_boxes: If True, draw selection boxes (for move mode)
        """
        # Skip if in straight segment mode (no control points to show)
        if self.straight_segment_mode:
            if show_boxes:
                # Still show start/end boxes in move mode even for straight segments
                self._draw_move_mode_boxes(strand, straight_mode=True)
            return

        glEnable(GL_LIGHTING)

        # Draw green sphere at CP1 (near start)
        self._draw_cp_sphere(strand.control_point1)

        # Draw green cone at CP2 (near end), pointing toward end
        self._draw_cp_cone(strand.control_point2, strand.end)

        # Draw green tube dashes
        self._draw_tube_dashes(strand.start, strand.control_point1)
        self._draw_tube_dashes(strand.end, strand.control_point2)

        # Draw selection boxes in move mode
        if show_boxes:
            self._draw_move_mode_boxes(strand, straight_mode=False)

    def _draw_cp_sphere(self, position):
        """Draw a green sphere at the given position for CP1"""
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])
        glColor3f(*self.CP_COLOR)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, self.CP_SPHERE_RADIUS, 16, 16)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _draw_cp_cone(self, position, target):
        """
        Draw a green cone at the given position for CP2.
        The cone points toward the target (end point).
        """
        glPushMatrix()
        glTranslatef(position[0], position[1], position[2])

        # Calculate rotation to point cone toward target
        direction = np.array(target) - np.array(position)
        length = np.linalg.norm(direction)

        if length > 1e-6:
            direction = direction / length

            # Default cone points along +Z, we need to rotate to point at target
            # Calculate rotation axis and angle
            z_axis = np.array([0.0, 0.0, 1.0])
            dot = np.dot(z_axis, direction)
            dot = max(-1.0, min(1.0, dot))  # Clamp for numerical stability

            if dot < -0.9999:
                # Nearly opposite direction - rotate 180 around any perpendicular axis
                glRotatef(180.0, 1.0, 0.0, 0.0)
            elif dot < 0.9999:
                # Calculate rotation axis and angle
                axis = np.cross(z_axis, direction)
                axis_len = np.linalg.norm(axis)
                if axis_len > 1e-6:
                    axis = axis / axis_len
                    angle = math.degrees(math.acos(dot))
                    glRotatef(angle, axis[0], axis[1], axis[2])

        glColor3f(*self.CP_COLOR)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        # Draw cone pointing in the rotated direction
        gluCylinder(quadric, self.CP_CONE_RADIUS, 0.0, self.CP_CONE_HEIGHT, 16, 1)
        # Draw base cap
        gluDisk(quadric, 0.0, self.CP_CONE_RADIUS, 16, 1)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _draw_tube_dashes(self, start_pos, end_pos):
        """
        Draw green tube dashes between two points.
        Uses small cylinders with gaps to create dashed line effect.
        """
        start = np.array(start_pos)
        end = np.array(end_pos)
        direction = end - start
        total_length = np.linalg.norm(direction)

        if total_length < 1e-6:
            return

        direction = direction / total_length

        # Calculate rotation to align cylinder with direction
        z_axis = np.array([0.0, 0.0, 1.0])
        dot = np.dot(z_axis, direction)
        dot = max(-1.0, min(1.0, dot))

        # Prepare rotation
        rotation_angle = 0.0
        rotation_axis = np.array([1.0, 0.0, 0.0])

        if dot < -0.9999:
            rotation_angle = 180.0
            rotation_axis = np.array([1.0, 0.0, 0.0])
        elif dot < 0.9999:
            axis = np.cross(z_axis, direction)
            axis_len = np.linalg.norm(axis)
            if axis_len > 1e-6:
                rotation_axis = axis / axis_len
                rotation_angle = math.degrees(math.acos(dot))

        # Draw dashes along the line
        current_dist = 0.0
        dash_on = True

        glColor3f(*self.CP_COLOR)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)

        while current_dist < total_length:
            if dash_on:
                # Calculate dash length (may be shorter at end)
                dash_len = min(self.DASH_LENGTH, total_length - current_dist)

                # Position for this dash
                dash_start = start + direction * current_dist

                glPushMatrix()
                glTranslatef(dash_start[0], dash_start[1], dash_start[2])

                if abs(rotation_angle) > 0.01:
                    glRotatef(rotation_angle, rotation_axis[0], rotation_axis[1], rotation_axis[2])

                gluCylinder(quadric, self.DASH_RADIUS, self.DASH_RADIUS, dash_len, 8, 1)
                glPopMatrix()

                current_dist += self.DASH_LENGTH
            else:
                current_dist += self.DASH_GAP

            dash_on = not dash_on

        gluDeleteQuadric(quadric)

    def _draw_move_mode_boxes(self, strand, straight_mode=False):
        """
        Draw selection boxes for move mode.

        Colors:
        - Red semi-transparent: idle (not hovering, not dragging)
        - Yellow semi-transparent: hovering or dragging
        """
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        box_size = self.control_point_box_size
        is_dragging = self.moving_strand is not None

        # Define colors
        RED_IDLE = (0.9, 0.2, 0.2, 0.4)      # Semi-transparent red
        YELLOW_ACTIVE = (1.0, 1.0, 0.0, 0.5)  # Semi-transparent yellow

        # Start point box
        if self.hovered_control_point == 'start' or (is_dragging and self.moving_control_point == 'start'):
            self._draw_box(strand.start, box_size, YELLOW_ACTIVE)
        else:
            self._draw_box(strand.start, box_size, RED_IDLE)

        # End point box
        if self.hovered_control_point == 'end' or (is_dragging and self.moving_control_point == 'end'):
            self._draw_box(strand.end, box_size, YELLOW_ACTIVE)
        else:
            self._draw_box(strand.end, box_size, RED_IDLE)

        # Control point boxes (only if NOT in straight mode)
        if not straight_mode:
            cp_box_size = box_size * 0.8

            # CP1 box
            if self.hovered_control_point == 'cp1' or (is_dragging and self.moving_control_point == 'cp1'):
                self._draw_box(strand.control_point1, cp_box_size, YELLOW_ACTIVE)
            else:
                self._draw_box(strand.control_point1, cp_box_size, RED_IDLE)

            # CP2 box
            if self.hovered_control_point == 'cp2' or (is_dragging and self.moving_control_point == 'cp2'):
                self._draw_box(strand.control_point2, cp_box_size, YELLOW_ACTIVE)
            else:
                self._draw_box(strand.control_point2, cp_box_size, RED_IDLE)

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def _draw_box(self, position, size, color):
        """Draw a 3D box at the given position with given color (RGBA)"""
        glColor4f(*color)

        half = size / 2.0
        x, y, z = position

        # Draw filled faces
        glBegin(GL_QUADS)

        # Front face
        glVertex3f(x - half, y - half, z + half)
        glVertex3f(x + half, y - half, z + half)
        glVertex3f(x + half, y + half, z + half)
        glVertex3f(x - half, y + half, z + half)

        # Back face
        glVertex3f(x - half, y - half, z - half)
        glVertex3f(x - half, y + half, z - half)
        glVertex3f(x + half, y + half, z - half)
        glVertex3f(x + half, y - half, z - half)

        # Top face
        glVertex3f(x - half, y + half, z - half)
        glVertex3f(x - half, y + half, z + half)
        glVertex3f(x + half, y + half, z + half)
        glVertex3f(x + half, y + half, z - half)

        # Bottom face
        glVertex3f(x - half, y - half, z - half)
        glVertex3f(x + half, y - half, z - half)
        glVertex3f(x + half, y - half, z + half)
        glVertex3f(x - half, y - half, z + half)

        # Right face
        glVertex3f(x + half, y - half, z - half)
        glVertex3f(x + half, y + half, z - half)
        glVertex3f(x + half, y + half, z + half)
        glVertex3f(x + half, y - half, z + half)

        # Left face
        glVertex3f(x - half, y - half, z - half)
        glVertex3f(x - half, y - half, z + half)
        glVertex3f(x - half, y + half, z + half)
        glVertex3f(x - half, y + half, z - half)

        glEnd()

        # Draw wireframe edges for better visibility
        glColor4f(0.0, 0.0, 0.0, 1.0)  # Black edges
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex3f(x - half, y - half, z + half)
        glVertex3f(x + half, y - half, z + half)
        glVertex3f(x + half, y + half, z + half)
        glVertex3f(x - half, y + half, z + half)
        glEnd()

        glBegin(GL_LINE_LOOP)
        glVertex3f(x - half, y - half, z - half)
        glVertex3f(x + half, y - half, z - half)
        glVertex3f(x + half, y + half, z - half)
        glVertex3f(x - half, y + half, z - half)
        glEnd()

        glBegin(GL_LINES)
        glVertex3f(x - half, y - half, z - half)
        glVertex3f(x - half, y - half, z + half)
        glVertex3f(x + half, y - half, z - half)
        glVertex3f(x + half, y - half, z + half)
        glVertex3f(x + half, y + half, z - half)
        glVertex3f(x + half, y + half, z + half)
        glVertex3f(x - half, y + half, z - half)
        glVertex3f(x - half, y + half, z + half)
        glEnd()

        glLineWidth(1.0)

    def _update_control_point_hover(self, screen_x, screen_y):
        """Update which control point is being hovered"""
        if not self.selected_strand:
            self.hovered_control_point = None
            self.setCursor(Qt.ArrowCursor)
            return

        strand = self.selected_strand

        # Check each control point box using screen-space distance
        # In straight mode, only allow hovering over start/end (not cp1/cp2)
        if self.straight_segment_mode:
            control_points = {
                'start': strand.start,
                'end': strand.end
            }
        else:
            control_points = {
                'start': strand.start,
                'end': strand.end,
                'cp1': strand.control_point1,
                'cp2': strand.control_point2
            }

        # Screen pixel threshold for hover detection
        hover_threshold = 25  # pixels

        closest_cp = None
        closest_dist = float('inf')

        for cp_name, cp_pos in control_points.items():
            screen_dist = self._get_point_screen_distance(cp_pos, screen_x, screen_y)
            if screen_dist < hover_threshold and screen_dist < closest_dist:
                closest_dist = screen_dist
                closest_cp = cp_name

        self.hovered_control_point = closest_cp

        # Update cursor based on hover state
        if self.hovered_control_point:
            self.setCursor(Qt.SizeAllCursor)  # Move cursor when hovering over control point
        else:
            self.setCursor(Qt.ArrowCursor)

    def _start_move(self, screen_x, screen_y):
        """Start moving strand or control point - only works when clicking on a control point box"""
        if not self.selected_strand:
            # Try to select a strand first
            self._try_select_strand(screen_x, screen_y)
            if not self.selected_strand:
                return

        strand = self.selected_strand

        # Only allow movement if clicking on a control point box
        if not self.hovered_control_point:
            # Not hovering over any control point box - don't start moving
            return

        # Get the position of the hovered control point
        if self.hovered_control_point == 'start':
            cp_pos = strand.start
        elif self.hovered_control_point == 'end':
            cp_pos = strand.end
        elif self.hovered_control_point == 'cp1':
            cp_pos = strand.control_point1
        else:
            cp_pos = strand.control_point2

        # Get 3D position at the control point's Y level
        pos_3d = self._screen_to_ground(screen_x, screen_y, ground_y=cp_pos[1])
        if pos_3d:
            self.moving_strand = strand
            self.moving_control_point = self.hovered_control_point
            self.move_start_pos = np.array(pos_3d)
            # Reset directional movement tracking for this drag
            self._reset_directional_movement("_move_along")
            if hasattr(self, "_move_along_direction"):
                delattr(self, "_move_along_direction")
            print(f"Moving {self.hovered_control_point.upper()} of {strand.name}")

    def _update_move(self, screen_x, screen_y, axis_mode="normal", shift_held=False, ctrl_held=False):
        """
        Update position during move.

        Movement modes:
        - Normal drag: Move on XZ plane (horizontal ground plane)
        - Shift + drag: Move on vertical plane facing camera (Y axis movement)
        - Ctrl + drag: Move towards/away from camera (depth movement)
        - Along: Move towards/away from the other point on the strand
        """
        if not self.moving_strand or self.move_start_pos is None:
            return

        strand = self.moving_strand

        # Get current position of what we're moving
        if self.moving_control_point == 'start':
            current_point = strand.start.copy()
        elif self.moving_control_point == 'end':
            current_point = strand.end.copy()
        elif self.moving_control_point == 'cp1':
            current_point = strand.control_point1.copy()
        elif self.moving_control_point == 'cp2':
            current_point = strand.control_point2.copy()
        else:
            current_point = ((strand.start + strand.end) / 2).copy()

        if axis_mode not in {"normal", "vertical", "depth", "along"}:
            if ctrl_held:
                axis_mode = "depth"
            elif shift_held:
                axis_mode = "vertical"
            else:
                axis_mode = "normal"

        if axis_mode == "depth":
            # CTRL held: Move towards/away from camera (depth movement)
            delta = self._calculate_depth_movement(screen_x, screen_y, current_point)
            if delta is None:
                return
        elif axis_mode == "vertical":
            # SHIFT held: Move on vertical plane facing camera
            # This makes the box follow the mouse exactly in screen space for Y movement
            new_pos = self._screen_to_vertical_plane(screen_x, screen_y, current_point)
            if new_pos is None:
                return

            new_pos = np.array(new_pos)
            # Only take the Y component change, keep X and Z from current position
            delta = np.array([0.0, new_pos[1] - current_point[1], 0.0])
        elif axis_mode == "along":
            direction = getattr(self, "_move_along_direction", None)
            if direction is None:
                if self.moving_control_point == 'start':
                    other_point = strand.end.copy()
                    direction = current_point - other_point
                elif self.moving_control_point == 'end':
                    other_point = strand.start.copy()
                    direction = current_point - other_point
                elif self.moving_control_point == 'cp1':
                    other_point = strand.start.copy()
                    direction = current_point - other_point
                elif self.moving_control_point == 'cp2':
                    other_point = strand.end.copy()
                    direction = current_point - other_point
                else:
                    direction = strand.end - strand.start
                self._move_along_direction = np.array(direction, dtype=float)

            delta = self._calculate_directional_movement(screen_y, direction, "_move_along")
            if delta is None:
                return
        else:
            # Normal: Move on XZ plane at current Y height
            current_pos = self._screen_to_ground(screen_x, screen_y, ground_y=current_point[1])
            if not current_pos:
                return

            current_pos = np.array(current_pos)
            delta = current_pos - self.move_start_pos

            # Update move_start_pos for next frame
            self.move_start_pos = current_pos

        # Apply delta to the appropriate point and propagate to connected strands
        if self.moving_control_point == 'start':
            strand.set_start(strand.start + delta)
            # Propagate to connected strand at start
            self._move_connected_strands(strand, 'start', delta)
            # In straight mode, re-straighten the strand after movement
            if self.straight_segment_mode:
                strand.make_straight()
        elif self.moving_control_point == 'end':
            strand.set_end(strand.end + delta)
            # Propagate to connected strand at end
            self._move_connected_strands(strand, 'end', delta)
            # In straight mode, re-straighten the strand after movement
            if self.straight_segment_mode:
                strand.make_straight()
        elif self.moving_control_point == 'cp1':
            # Use setter to trigger C1 continuity sync with parent and children
            strand.set_control_point1(strand.control_point1 + delta)
            # If this is an AttachedStrand, also sync parent's control point
            if hasattr(strand, 'sync_parent_cp_with_our_cp1'):
                strand.sync_parent_cp_with_our_cp1()
        elif self.moving_control_point == 'cp2':
            # Use setter to trigger C1 continuity sync with attached strands
            strand.set_control_point2(strand.control_point2 + delta)
        else:
            # Move whole strand
            strand.move(delta)

    def _move_connected_strands(self, strand, endpoint, delta):
        """
        Move strands that are connected to the given endpoint.

        Based on layer_state_manager connection logic:
        - If this is an AttachedStrand and we're moving its START, move the parent's connected endpoint
        - If this strand has attached_strands at this endpoint, move their START points
        - Connections are bidirectional: moving one end moves the connected end

        Args:
            strand: The strand being moved
            endpoint: 'start' or 'end'
            delta: The movement delta to apply
        """
        from attached_strand import AttachedStrand

        if endpoint == 'start':
            # If this is an AttachedStrand, its start is connected to parent
            if isinstance(strand, AttachedStrand):
                parent = strand.parent_strand
                attachment_side = strand.attachment_side

                # Move the parent's connected endpoint
                if attachment_side == 0:
                    # Connected to parent's start
                    parent.set_start(parent.start + delta)
                    # In straight mode, re-straighten parent
                    if self.straight_segment_mode:
                        parent.make_straight()
                    # Also propagate to anything else connected to parent's start
                    self._propagate_to_attached_strands(parent, 0, delta, exclude=strand)
                else:
                    # Connected to parent's end
                    parent.set_end(parent.end + delta)
                    # In straight mode, re-straighten parent
                    if self.straight_segment_mode:
                        parent.make_straight()
                    # Also propagate to anything else connected to parent's end
                    self._propagate_to_attached_strands(parent, 1, delta, exclude=strand)
            else:
                # Regular strand - check if any attached strands are connected to start (side=0)
                self._propagate_to_attached_strands(strand, 0, delta, exclude=None)

        elif endpoint == 'end':
            # Check if any attached strands are connected to this strand's end (side=1)
            self._propagate_to_attached_strands(strand, 1, delta, exclude=None)

            # If this is an AttachedStrand and something is attached to its end
            # that case is handled by _propagate_to_attached_strands above

    def _propagate_to_attached_strands(self, parent_strand, side, delta, exclude=None):
        """
        Move all attached strands connected to the given side of parent_strand.

        Args:
            parent_strand: The parent strand
            side: 0 for start, 1 for end
            delta: Movement delta
            exclude: Strand to exclude (to prevent infinite recursion)
        """
        for attached in parent_strand.attached_strands:
            if attached == exclude:
                continue

            if hasattr(attached, 'attachment_side') and attached.attachment_side == side:
                # This attached strand is connected at this side
                # Move its start point (attached strands connect via their start)
                attached.start = attached.start + delta
                attached.control_point1 = attached.control_point1 + delta

                # Also move its end and cp2 to maintain shape (whole strand moves)
                attached.end = attached.end + delta
                attached.control_point2 = attached.control_point2 + delta

                # In straight mode, re-straighten the attached strand
                if self.straight_segment_mode:
                    attached.make_straight()

    def _screen_to_vertical_plane(self, screen_x, screen_y, point_on_plane):
        """
        Convert screen coordinates to 3D point on a vertical plane passing through point_on_plane.
        The plane faces the camera (perpendicular to camera's XZ direction).
        This allows the point to follow the mouse exactly for vertical movement.
        """
        self.makeCurrent()

        # Setup matrices
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        width = self.width()
        height = self.height() if self.height() > 0 else 1
        aspect = width / height
        gluPerspective(45.0, aspect, 0.1, 1000.0)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Setup camera
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
            # Get ray from camera through screen point
            near_point = gluUnProject(screen_x, win_y, 0.0, modelview, projection, viewport)
            far_point = gluUnProject(screen_x, win_y, 1.0, modelview, projection, viewport)

            ray_origin = np.array(near_point)
            ray_dir = np.array(far_point) - ray_origin
            ray_dir_len = np.linalg.norm(ray_dir)
            if ray_dir_len > 1e-6:
                ray_dir /= ray_dir_len

            # Create vertical plane facing camera
            # Plane normal is horizontal, pointing from point toward camera (in XZ plane)
            camera_pos = np.array([camera_x, camera_y, camera_z])
            to_camera = camera_pos - point_on_plane
            to_camera[1] = 0  # Make horizontal
            to_camera_len = np.linalg.norm(to_camera)
            if to_camera_len > 1e-6:
                plane_normal = to_camera / to_camera_len
            else:
                plane_normal = np.array([0.0, 0.0, 1.0])

            # Plane equation: dot(normal, (P - point_on_plane)) = 0
            # Ray: P = ray_origin + t * ray_dir
            # Solve for t: dot(normal, ray_origin + t * ray_dir - point_on_plane) = 0
            denom = np.dot(plane_normal, ray_dir)
            if abs(denom) > 1e-6:
                t = np.dot(plane_normal, point_on_plane - ray_origin) / denom
                if t >= 0:
                    intersection = ray_origin + t * ray_dir
                    result = tuple(intersection)
        except Exception as e:
            print(f"Error in _screen_to_vertical_plane: {e}")

        # Restore matrices
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        return result

    def _calculate_depth_movement(self, screen_x, screen_y, current_point):
        """
        Calculate movement towards/away from camera based on mouse drag.
        Uses vertical mouse movement to control depth along camera view axis.
        Dragging up moves away from camera, dragging down moves towards camera.

        Distance limits:
        - Minimum: 5.0 (invisible camera wall - object stops when hitting this)
        - Maximum: 50.0 (reasonable far limit)
        """
        self.makeCurrent()

        # Distance limits from camera (invisible walls)
        CAMERA_WALL_THICKNESS = 5.0  # Invisible wall in front of camera
        MAX_DEPTH = 50.0             # Maximum distance from camera

        # Calculate camera position
        azimuth_rad = math.radians(self.camera_azimuth)
        elevation_rad = math.radians(self.camera_elevation)

        camera_x = self.camera_target[0] + self.camera_distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
        camera_y = self.camera_target[1] + self.camera_distance * math.sin(elevation_rad)
        camera_z = self.camera_target[2] + self.camera_distance * math.cos(elevation_rad) * math.cos(azimuth_rad)

        camera_pos = np.array([camera_x, camera_y, camera_z])

        # Calculate view direction from camera to the specific point being moved
        # This ensures depth movement is always directly towards/away from camera
        view_dir = current_point - camera_pos
        view_dir_len = np.linalg.norm(view_dir)
        if view_dir_len < 1e-6:
            return None
        view_dir = view_dir / view_dir_len

        # Get screen delta from last position
        if not hasattr(self, '_last_depth_screen_y'):
            self._last_depth_screen_y = screen_y
            return np.array([0.0, 0.0, 0.0])

        screen_dy = screen_y - self._last_depth_screen_y
        self._last_depth_screen_y = screen_y

        # Scale factor based on camera distance for consistent feel
        depth_speed = self.camera_distance * 0.005

        # Positive screen_dy (dragging down) = move towards camera (negative depth)
        # Negative screen_dy (dragging up) = move away from camera (positive depth)
        depth_delta = -screen_dy * depth_speed

        # Calculate current signed distance from camera along view direction
        to_point = current_point - camera_pos
        current_depth = np.dot(to_point, view_dir)

        # Calculate new depth and clamp it (stop at invisible camera wall)
        new_depth = current_depth + depth_delta
        clamped_depth = max(CAMERA_WALL_THICKNESS, min(MAX_DEPTH, new_depth))

        # Adjust delta based on clamping
        actual_delta = clamped_depth - current_depth

        # Calculate movement along view direction
        delta = view_dir * actual_delta

        return delta

    def _end_move(self):
        """End move operation"""
        if self.moving_strand:
            print(f"Finished moving {self.moving_strand.name}")
        self.moving_strand = None
        self.moving_control_point = None
        self.move_start_pos = None
        self._reset_directional_movement("_move_along")
        if hasattr(self, "_move_along_direction"):
            delattr(self, "_move_along_direction")
        # Reset depth tracking for next drag
        if hasattr(self, '_last_depth_screen_y'):
            delattr(self, '_last_depth_screen_y')
