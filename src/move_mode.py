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
    CP_CONE_RADIUS = 0.12        # Base half-size of CP2 pyramid
    CP_CONE_HEIGHT = 0.25        # Height of CP2 pyramid
    CP_COLOR = (0.0, 0.85, 0.0)  # Green color for control points
    DASH_RADIUS = 0.03           # Radius of tube dashes
    DASH_LENGTH = 0.15           # Length of each dash segment
    DASH_GAP = 0.1               # Gap between dashes

    # Twist ring visual settings
    TWIST_RING_RADIUS_FACTOR = 1.8  # Ring radius = box_size * this factor
    TWIST_RING_COLOR = (0.8, 0.8, 1.0, 0.5)  # Light blue semi-transparent
    TWIST_RING_HOVER_COLOR = (1.0, 1.0, 0.5, 0.7)  # Yellow when hovering
    TWIST_RING_ACTIVE_COLOR = (0.5, 1.0, 0.5, 0.8)  # Green when dragging
    TWIST_NOTCH_COLOR = (1.0, 1.0, 1.0, 0.9)  # White notch marker
    TWIST_RING_SEGMENTS = 32  # Number of segments for the ring
    TWIST_RING_THICKNESS = 3.0  # Line width for the ring

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

        # Draw green pyramid at CP2 (near end), pointing toward end
        self._draw_cp_pyramid(strand.control_point2, strand.end)

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

    def _draw_cp_pyramid(self, position, target):
        """
        Draw a green pyramid at the given position for CP2.
        The pyramid points toward the target (end point).
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

        half = self.CP_CONE_RADIUS
        height = self.CP_CONE_HEIGHT
        base = [
            np.array([-half, -half, 0.0]),
            np.array([half, -half, 0.0]),
            np.array([half, half, 0.0]),
            np.array([-half, half, 0.0]),
        ]
        tip = np.array([0.0, 0.0, height])

        glBegin(GL_TRIANGLES)
        for i in range(4):
            v0 = base[i]
            v1 = base[(i + 1) % 4]
            normal = np.cross(v1 - v0, tip - v0)
            normal_len = np.linalg.norm(normal)
            if normal_len > 1e-6:
                normal = normal / normal_len
            glNormal3f(normal[0], normal[1], normal[2])
            glVertex3f(v0[0], v0[1], v0[2])
            glVertex3f(v1[0], v1[1], v1[2])
            glVertex3f(tip[0], tip[1], tip[2])
        glEnd()

        glBegin(GL_QUADS)
        glNormal3f(0.0, 0.0, -1.0)
        glVertex3f(base[0][0], base[0][1], base[0][2])
        glVertex3f(base[1][0], base[1][1], base[1][2])
        glVertex3f(base[2][0], base[2][1], base[2][2])
        glVertex3f(base[3][0], base[3][1], base[3][2])
        glEnd()

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

        # Draw twist rings around all control point boxes
        self._draw_twist_rings_for_strand(strand, box_size)

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

    def _draw_twist_ring(self, position, box_size, strand, point_name, tangent=None):
        """
        Draw a twist rotation ring around a control point.

        Uses a fixed world-space orientation (horizontal ring in XZ plane)
        so that moving other control points doesn't affect the ring orientation.

        Args:
            position: 3D position of the control point
            box_size: Size of the control point box (ring radius is based on this)
            strand: The strand object (to get twist angle)
            point_name: 'start', 'end', 'cp1', or 'cp2'
            tangent: Ignored - kept for API compatibility
        """
        # Get current twist angle for this point
        twist_angle = strand.get_twist(point_name)

        # Calculate ring radius
        ring_radius = box_size * self.TWIST_RING_RADIUS_FACTOR

        # Determine color based on hover/drag state
        hovered_ring = getattr(self, 'hovered_twist_ring', None)
        dragging_ring = getattr(self, 'dragging_twist_ring', None)

        if dragging_ring == point_name:
            color = self.TWIST_RING_ACTIVE_COLOR
            line_width = self.TWIST_RING_THICKNESS + 1.5
        elif hovered_ring == point_name:
            color = self.TWIST_RING_HOVER_COLOR
            line_width = self.TWIST_RING_THICKNESS + 1.0
        else:
            color = self.TWIST_RING_COLOR
            line_width = self.TWIST_RING_THICKNESS

        # Use fixed world-space orientation based on current move axis mode
        # This ensures moving start/end doesn't affect other ring orientations
        move_mode = getattr(self, 'move_axis_mode', 'normal')

        if move_mode == "normal":
            # XZ mode: ring perpendicular to XZ plane (vertical ring in YZ plane)
            perp1 = np.array([0.0, 1.0, 0.0])  # Y axis
            perp2 = np.array([0.0, 0.0, 1.0])  # Z axis

        elif move_mode == "vertical":
            # Y mode: ring in XZ plane (horizontal)
            perp1 = np.array([1.0, 0.0, 0.0])  # X axis
            perp2 = np.array([0.0, 0.0, 1.0])  # Z axis

        elif move_mode == "depth":
            # Depth mode: ring always faces camera (perpendicular to view direction)
            # Calculate camera direction
            azimuth_rad = math.radians(self.camera_azimuth)
            elevation_rad = math.radians(self.camera_elevation)

            # Camera forward direction (from camera to target)
            cam_forward = np.array([
                -math.cos(elevation_rad) * math.sin(azimuth_rad),
                -math.sin(elevation_rad),
                -math.cos(elevation_rad) * math.cos(azimuth_rad)
            ])

            # Ring plane perpendicular to camera view
            # Find two perpendicular vectors in the plane facing camera
            if abs(cam_forward[1]) < 0.9:
                up_hint = np.array([0.0, 1.0, 0.0])
            else:
                up_hint = np.array([1.0, 0.0, 0.0])

            perp1 = np.cross(cam_forward, up_hint)
            perp1_len = np.linalg.norm(perp1)
            if perp1_len > 1e-6:
                perp1 = perp1 / perp1_len
            else:
                perp1 = np.array([1.0, 0.0, 0.0])

            perp2 = np.cross(cam_forward, perp1)
            perp2_len = np.linalg.norm(perp2)
            if perp2_len > 1e-6:
                perp2 = perp2 / perp2_len
            else:
                perp2 = np.array([0.0, 1.0, 0.0])

        elif move_mode == "along":
            # Along mode: each ring perpendicular to its own along vector
            # Calculate along direction based on which point this is
            along_dir = None
            if point_name == 'start':
                along_dir = strand.end - strand.start
            elif point_name == 'end':
                along_dir = strand.start - strand.end
            elif point_name == 'cp1':
                along_dir = strand.start - strand.control_point1  # CP1 to Start
            elif point_name == 'cp2':
                along_dir = strand.end - strand.control_point2    # CP2 to End

            if along_dir is not None and np.linalg.norm(along_dir) > 1e-6:
                along_dir = along_dir / np.linalg.norm(along_dir)

                # Find perpendicular vectors to along direction
                if abs(along_dir[1]) < 0.9:
                    up_hint = np.array([0.0, 1.0, 0.0])
                else:
                    up_hint = np.array([1.0, 0.0, 0.0])

                perp1 = np.cross(along_dir, up_hint)
                perp1_len = np.linalg.norm(perp1)
                if perp1_len > 1e-6:
                    perp1 = perp1 / perp1_len
                else:
                    perp1 = np.array([1.0, 0.0, 0.0])

                perp2 = np.cross(along_dir, perp1)
                perp2_len = np.linalg.norm(perp2)
                if perp2_len > 1e-6:
                    perp2 = perp2 / perp2_len
                else:
                    perp2 = np.array([0.0, 1.0, 0.0])
            else:
                # Fallback to horizontal if no along direction
                perp1 = np.array([1.0, 0.0, 0.0])
                perp2 = np.array([0.0, 0.0, 1.0])

        else:
            # Default: horizontal ring in XZ plane
            perp1 = np.array([1.0, 0.0, 0.0])  # X axis
            perp2 = np.array([0.0, 0.0, 1.0])  # Z axis

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Draw the ring
        glLineWidth(line_width)
        glColor4f(*color)
        glBegin(GL_LINE_LOOP)

        for i in range(self.TWIST_RING_SEGMENTS):
            angle = 2 * math.pi * i / self.TWIST_RING_SEGMENTS
            point = (position +
                     perp1 * math.cos(angle) * ring_radius +
                     perp2 * math.sin(angle) * ring_radius)
            glVertex3f(point[0], point[1], point[2])

        glEnd()

        # Draw the notch marker showing current twist angle
        notch_angle = math.radians(twist_angle)
        notch_inner = ring_radius * 0.7
        notch_outer = ring_radius * 1.1

        # Notch position
        notch_dir = perp1 * math.cos(notch_angle) + perp2 * math.sin(notch_angle)
        notch_start = position + notch_dir * notch_inner
        notch_end = position + notch_dir * notch_outer

        # Draw notch as a thick line
        glLineWidth(line_width + 2.0)
        glColor4f(*self.TWIST_NOTCH_COLOR)
        glBegin(GL_LINES)
        glVertex3f(notch_start[0], notch_start[1], notch_start[2])
        glVertex3f(notch_end[0], notch_end[1], notch_end[2])
        glEnd()

        # Draw a small circle at the notch end for visibility
        glPointSize(8.0)
        glBegin(GL_POINTS)
        glVertex3f(notch_end[0], notch_end[1], notch_end[2])
        glEnd()
        glPointSize(1.0)

        glLineWidth(1.0)
        glDisable(GL_BLEND)

    def _draw_twist_rings_for_strand(self, strand, box_size):
        """
        Draw twist rings for all control points of a strand.

        Args:
            strand: The strand to draw rings for
            box_size: Base box size for calculating ring radius
        """
        # Draw twist ring for start point
        self._draw_twist_ring(strand.start, box_size, strand, 'start')

        # Draw twist ring for end point
        self._draw_twist_ring(strand.end, box_size, strand, 'end')

        # Draw twist rings for control points (if not in straight mode)
        if not self.straight_segment_mode:
            cp_box_size = box_size * 0.8
            self._draw_twist_ring(strand.control_point1, cp_box_size, strand, 'cp1')
            self._draw_twist_ring(strand.control_point2, cp_box_size, strand, 'cp2')

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
        min_hover_threshold = 12  # pixels

        closest_cp = None
        closest_dist = float('inf')

        for cp_name, cp_pos in control_points.items():
            screen_center = self._project_point_to_screen(cp_pos)
            if not screen_center:
                continue

            box_size = self.control_point_box_size
            if cp_name in ('cp1', 'cp2'):
                box_size *= 0.8

            half = box_size / 2.0
            max_radius = 0.0
            for sx in (-1.0, 1.0):
                for sy in (-1.0, 1.0):
                    for sz in (-1.0, 1.0):
                        offset = np.array([sx * half, sy * half, sz * half])
                        screen_offset = self._project_point_to_screen(cp_pos + offset)
                        if not screen_offset:
                            continue
                        dx = screen_offset[0] - screen_center[0]
                        dy = screen_offset[1] - screen_center[1]
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > max_radius:
                            max_radius = dist

            hover_threshold = max(min_hover_threshold, max_radius)
            dx = screen_center[0] - screen_x
            dy = screen_center[1] - screen_y
            screen_dist = math.sqrt(dx * dx + dy * dy)
            if screen_dist < hover_threshold and screen_dist < closest_dist:
                closest_dist = screen_dist
                closest_cp = cp_name

        self.hovered_control_point = closest_cp

        # Check for twist ring hover (only if not hovering over a box)
        hovered_ring = None
        if not self.hovered_control_point:
            hovered_ring = self._check_twist_ring_hover(screen_x, screen_y, strand, control_points)

        # Store the hovered ring state
        self.hovered_twist_ring = hovered_ring

        # Update cursor based on hover state
        if self.hovered_control_point:
            self.setCursor(Qt.SizeAllCursor)  # Move cursor when hovering over control point
        elif self.hovered_twist_ring:
            self.setCursor(Qt.PointingHandCursor)  # Point cursor for twist ring
        else:
            self.setCursor(Qt.ArrowCursor)

    def _check_twist_ring_hover(self, screen_x, screen_y, strand, control_points):
        """
        Check if the mouse is hovering over a twist ring.

        The ring is detected as a donut-shaped area around the control point,
        between the box edge and the ring outer edge.

        Args:
            screen_x, screen_y: Mouse screen coordinates
            strand: The selected strand
            control_points: Dict of control point names to positions

        Returns:
            Name of the hovered ring ('start', 'end', 'cp1', 'cp2') or None
        """
        closest_ring = None
        closest_ring_dist = float('inf')

        for cp_name, cp_pos in control_points.items():
            screen_center = self._project_point_to_screen(cp_pos)
            if not screen_center:
                continue

            # Calculate box size and ring radius in screen space
            box_size = self.control_point_box_size
            if cp_name in ('cp1', 'cp2'):
                box_size *= 0.8

            ring_radius_3d = box_size * self.TWIST_RING_RADIUS_FACTOR

            # Use orientation matching _draw_twist_ring based on move axis mode
            move_mode = getattr(self, 'move_axis_mode', 'normal')

            if move_mode == "normal":
                # XZ mode: vertical ring (YZ plane)
                perp = np.array([0.0, 1.0, 0.0])  # Y axis
            elif move_mode == "vertical":
                # Y mode: horizontal ring (XZ plane)
                perp = np.array([1.0, 0.0, 0.0])  # X axis
            elif move_mode == "depth":
                # Depth mode: ring faces camera
                azimuth_rad = math.radians(self.camera_azimuth)
                elevation_rad = math.radians(self.camera_elevation)
                cam_forward = np.array([
                    -math.cos(elevation_rad) * math.sin(azimuth_rad),
                    -math.sin(elevation_rad),
                    -math.cos(elevation_rad) * math.cos(azimuth_rad)
                ])
                if abs(cam_forward[1]) < 0.9:
                    up_hint = np.array([0.0, 1.0, 0.0])
                else:
                    up_hint = np.array([1.0, 0.0, 0.0])
                perp = np.cross(cam_forward, up_hint)
                perp_len = np.linalg.norm(perp)
                if perp_len > 1e-6:
                    perp = perp / perp_len
                else:
                    perp = np.array([1.0, 0.0, 0.0])
            elif move_mode == "along":
                # Along mode: each ring perpendicular to its own along vector
                along_dir = None
                if cp_name == 'start':
                    along_dir = strand.end - strand.start
                elif cp_name == 'end':
                    along_dir = strand.start - strand.end
                elif cp_name == 'cp1':
                    along_dir = strand.start - strand.control_point1  # CP1 to Start
                elif cp_name == 'cp2':
                    along_dir = strand.end - strand.control_point2    # CP2 to End

                if along_dir is not None and np.linalg.norm(along_dir) > 1e-6:
                    along_dir = along_dir / np.linalg.norm(along_dir)
                    if abs(along_dir[1]) < 0.9:
                        up_hint = np.array([0.0, 1.0, 0.0])
                    else:
                        up_hint = np.array([1.0, 0.0, 0.0])
                    perp = np.cross(along_dir, up_hint)
                    perp_len = np.linalg.norm(perp)
                    if perp_len > 1e-6:
                        perp = perp / perp_len
                    else:
                        perp = np.array([1.0, 0.0, 0.0])
                else:
                    perp = np.array([1.0, 0.0, 0.0])
            else:
                # Default: horizontal
                perp = np.array([1.0, 0.0, 0.0])

            # Project ring edge point
            ring_edge = cp_pos + perp * ring_radius_3d
            ring_screen = self._project_point_to_screen(ring_edge)
            if not ring_screen:
                continue

            # Calculate screen ring radius
            screen_ring_radius = math.sqrt(
                (ring_screen[0] - screen_center[0]) ** 2 +
                (ring_screen[1] - screen_center[1]) ** 2
            )

            # Calculate screen distance from mouse to center
            dx = screen_x - screen_center[0]
            dy = screen_y - screen_center[1]
            screen_dist = math.sqrt(dx * dx + dy * dy)

            # Ring is detected as donut between inner and outer radius
            # Inner radius is about 60% of ring radius (to exclude box area)
            # Outer radius is about 120% of ring radius (tolerance)
            inner_threshold = screen_ring_radius * 0.5
            outer_threshold = screen_ring_radius * 1.3

            if inner_threshold < screen_dist < outer_threshold:
                # Calculate how close to the ring line itself
                ring_dist = abs(screen_dist - screen_ring_radius)
                if ring_dist < closest_ring_dist:
                    closest_ring_dist = ring_dist
                    closest_ring = cp_name

        return closest_ring

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
            # Save state for undo BEFORE starting the move
            if hasattr(self, 'undo_redo_manager') and self.undo_redo_manager:
                self.undo_redo_manager.save_state()

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
        if hasattr(self, "_add_drag_lod_target"):
            self._add_drag_lod_target(strand)

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
        # (2D-style: save and restore non-moving endpoints to prevent drift)
        if self.moving_control_point == 'start':
            # Save non-moving endpoint before modification
            original_end = strand.end.copy()
            strand.set_start(strand.start + delta)
            # Restore non-moving endpoint (matches 2D behavior)
            strand.end = original_end
            strand._mark_geometry_dirty()
            # Propagate to connected strand at start
            self._move_connected_strands(strand, 'start', delta)
            # In straight mode, re-straighten the strand after movement
            if self.straight_segment_mode:
                strand.make_straight()
        elif self.moving_control_point == 'end':
            # Save non-moving endpoint before modification
            original_start = strand.start.copy()
            strand.set_end(strand.end + delta)
            # Restore non-moving endpoint (matches 2D behavior)
            strand.start = original_start
            strand._mark_geometry_dirty()
            # Propagate to connected strand at end
            self._move_connected_strands(strand, 'end', delta)
            # In straight mode, re-straighten the strand after movement
            if self.straight_segment_mode:
                strand.make_straight()
        elif self.moving_control_point == 'cp1':
            # Use setter to trigger C1 continuity sync with parent and children
            strand.set_control_point1(strand.control_point1 + delta, delta=delta)
            # If this is an AttachedStrand, also sync parent's control point (mirror movement)
            if hasattr(strand, 'sync_parent_cp_with_our_cp1'):
                strand.sync_parent_cp_with_our_cp1(delta)
                # Add parent to LOD targets so it renders with updated geometry
                if hasattr(strand, 'parent_strand') and hasattr(self, "_add_drag_lod_target"):
                    self._add_drag_lod_target(strand.parent_strand)
            # Also add any attached strands at start (side=0) to LOD targets
            for attached in strand.attached_strands:
                if hasattr(attached, 'attachment_side') and attached.attachment_side == 0:
                    if hasattr(self, "_add_drag_lod_target"):
                        self._add_drag_lod_target(attached)
        elif self.moving_control_point == 'cp2':
            # Use setter to trigger C1 continuity sync with attached strands (mirror movement)
            strand.set_control_point2(strand.control_point2 + delta, delta=delta)
            # Add attached strands at end (side=1) to LOD targets so they render with updated geometry
            for attached in strand.attached_strands:
                if hasattr(attached, 'attachment_side') and attached.attachment_side == 1:
                    if hasattr(self, "_add_drag_lod_target"):
                        self._add_drag_lod_target(attached)
        else:
            # Move whole strand
            strand.move(delta)

    def _move_connected_strands(self, strand, endpoint, delta):
        """
        Move strands that are connected to the given endpoint.
        (2D-style: save/restore non-moving endpoints)

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

                # Move the parent's connected endpoint DIRECTLY (not via set_start/set_end)
                # to avoid triggering update_start_from_parent on the strand we're moving
                if attachment_side == 0:
                    # Connected to parent's start
                    old_parent_start = parent.start.copy()
                    new_parent_start = parent.start + delta

                    # Only move control points if they coincide with the old start
                    if np.allclose(parent.control_point1, old_parent_start, atol=1e-6):
                        parent.control_point1 = new_parent_start.copy()
                    if np.allclose(parent.control_point2, old_parent_start, atol=1e-6):
                        parent.control_point2 = new_parent_start.copy()

                    parent.start = new_parent_start
                    parent._mark_geometry_dirty()

                    if hasattr(self, "_add_drag_lod_target"):
                        self._add_drag_lod_target(parent)
                    # In straight mode, re-straighten parent
                    if self.straight_segment_mode:
                        parent.make_straight()
                    # Also propagate to anything else connected to parent's start
                    self._propagate_to_attached_strands(parent, 0, delta, exclude=strand)
                else:
                    # Connected to parent's end
                    old_parent_end = parent.end.copy()
                    new_parent_end = parent.end + delta

                    # Only move control points if they coincide with the old end
                    if np.allclose(parent.control_point1, old_parent_end, atol=1e-6):
                        parent.control_point1 = new_parent_end.copy()
                    if np.allclose(parent.control_point2, old_parent_end, atol=1e-6):
                        parent.control_point2 = new_parent_end.copy()

                    parent.end = new_parent_end
                    parent._mark_geometry_dirty()

                    if hasattr(self, "_add_drag_lod_target"):
                        self._add_drag_lod_target(parent)
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
        Move attached strands' connection points to match parent's moved endpoint.
        (2D-style: only move the connection point, not the whole strand)

        Args:
            parent_strand: The parent strand
            side: 0 for start, 1 for end
            delta: Movement delta
            exclude: Strand to exclude (to prevent infinite recursion)
        """
        # Get the new position of parent's attachment point
        if side == 0:
            new_attach_pos = parent_strand.start.copy()
        else:
            new_attach_pos = parent_strand.end.copy()

        for attached in parent_strand.attached_strands:
            if attached == exclude:
                continue

            if hasattr(attached, 'attachment_side') and attached.attachment_side == side:
                # This attached strand is connected at this side
                # 2D-style: Only move connection point (start) to match parent
                # Do NOT move the rest of the strand (end stays in place)
                old_start = attached.start.copy()

                # Only move control points if they coincide with the old start
                if np.allclose(attached.control_point1, old_start, atol=1e-6):
                    attached.control_point1 = new_attach_pos.copy()
                if np.allclose(attached.control_point2, old_start, atol=1e-6):
                    attached.control_point2 = new_attach_pos.copy()

                # Move only the start point to match parent's attachment point
                attached.start = new_attach_pos.copy()
                attached._mark_geometry_dirty()

                if hasattr(self, "_add_drag_lod_target"):
                    self._add_drag_lod_target(attached)

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

    # ==================== Twist Drag Methods ====================

    def _start_twist_drag(self, screen_x, screen_y):
        """
        Start twisting a control point's orientation.

        Only starts if the mouse is over a twist ring.

        Args:
            screen_x, screen_y: Mouse screen coordinates

        Returns:
            True if twist drag started, False otherwise
        """
        if not self.selected_strand:
            return False

        # Check if we're hovering over a twist ring
        hovered_ring = getattr(self, 'hovered_twist_ring', None)
        if not hovered_ring:
            return False

        # Save state for undo
        if hasattr(self, 'undo_redo_manager') and self.undo_redo_manager:
            self.undo_redo_manager.save_state()

        # Initialize twist drag state
        self.dragging_twist_ring = hovered_ring
        self.twist_drag_start_x = screen_x
        self.twist_drag_last_x = screen_x
        self.twist_drag_start_screen_pos = (screen_x, screen_y)
        self.twist_drag_start_angle = self.selected_strand.get_twist(hovered_ring)
        self.twist_drag_total_angle = 0.0

        print(f"Twist: Started twisting {hovered_ring} of {self.selected_strand.name}")
        self.update()
        return True

    def _update_twist_drag(self, screen_x, screen_y):
        """
        Update the twist angle based on horizontal mouse movement.

        Dragging right increases the angle, dragging left decreases it.

        Args:
            screen_x, screen_y: Current mouse screen coordinates

        Returns:
            True if twist was updated, False otherwise
        """
        dragging_ring = getattr(self, 'dragging_twist_ring', None)
        if not dragging_ring or not self.selected_strand:
            return False

        # Calculate horizontal movement
        screen_dx = screen_x - self.twist_drag_last_x
        self.twist_drag_last_x = screen_x

        # Convert screen pixels to degrees
        # Use a reasonable sensitivity (about 1 degree per 2 pixels)
        angle_speed = 0.5  # Degrees per pixel
        angle_delta = screen_dx * angle_speed

        # Update the twist angle
        current_angle = self.selected_strand.get_twist(dragging_ring)
        new_angle = current_angle + angle_delta
        self.selected_strand.set_twist(dragging_ring, new_angle)

        self.twist_drag_total_angle += angle_delta

        self.update()
        return True

    def _end_twist_drag(self):
        """
        End the twist drag operation.

        Returns:
            True if twist drag was ended, False if not dragging
        """
        dragging_ring = getattr(self, 'dragging_twist_ring', None)
        if not dragging_ring:
            return False

        total_angle = getattr(self, 'twist_drag_total_angle', 0.0)
        print(f"Twist: Finished twisting {dragging_ring} (delta: {total_angle:.1f}°)")

        # Clear twist drag state
        self.dragging_twist_ring = None
        self.twist_drag_start_x = None
        self.twist_drag_last_x = None
        self.twist_drag_start_screen_pos = None
        self.twist_drag_start_angle = None
        self.twist_drag_total_angle = 0.0

        self.update()
        return True

    def _is_twist_dragging(self):
        """Check if we're currently dragging a twist ring."""
        return getattr(self, 'dragging_twist_ring', None) is not None

    def _draw_twist_drag_ui(self):
        """
        Draw 2D overlay UI showing twist angle during drag.
        Similar to rotate mode's drag UI.
        """
        dragging_ring = getattr(self, 'dragging_twist_ring', None)
        if not dragging_ring:
            return

        start_pos = getattr(self, 'twist_drag_start_screen_pos', None)
        if not start_pos:
            return

        start_x, start_y = start_pos
        total_angle = getattr(self, 'twist_drag_total_angle', 0.0)

        # Switch to 2D orthographic projection
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        width = self.width()
        height = self.height()
        glOrtho(0, width, height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Draw indicator lines
        line_length = 100
        arrow_size = 10

        # Left arrow (negative rotation) - red
        glLineWidth(3.0)
        glColor4f(1.0, 0.3, 0.3, 0.9)
        glBegin(GL_LINES)
        glVertex2f(start_x, start_y)
        glVertex2f(start_x - line_length, start_y)
        glEnd()

        glBegin(GL_TRIANGLES)
        glVertex2f(start_x - line_length, start_y)
        glVertex2f(start_x - line_length + arrow_size, start_y - arrow_size * 0.6)
        glVertex2f(start_x - line_length + arrow_size, start_y + arrow_size * 0.6)
        glEnd()

        # Right arrow (positive rotation) - green
        glColor4f(0.3, 1.0, 0.3, 0.9)
        glBegin(GL_LINES)
        glVertex2f(start_x, start_y)
        glVertex2f(start_x + line_length, start_y)
        glEnd()

        glBegin(GL_TRIANGLES)
        glVertex2f(start_x + line_length, start_y)
        glVertex2f(start_x + line_length - arrow_size, start_y - arrow_size * 0.6)
        glVertex2f(start_x + line_length - arrow_size, start_y + arrow_size * 0.6)
        glEnd()

        # Center point
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glPointSize(10.0)
        glBegin(GL_POINTS)
        glVertex2f(start_x, start_y)
        glEnd()

        # Angle bar
        text_y = start_y - 25
        angle_bar_width = min(abs(total_angle) * 1.5, 100)
        if total_angle != 0:
            if total_angle > 0:
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
