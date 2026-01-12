"""
OpenStrandStudio 3D - Strand Class
3D Bezier curve strand with control points
"""

import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *


class Strand:
    """
    A 3D strand represented as a cubic Bezier curve.

    Control points:
    - start: Starting point of the strand
    - end: Ending point of the strand
    - control_point1: First Bezier control point (influences curve near start)
    - control_point2: Second Bezier control point (influences curve near end)
    """

    def __init__(self, start, end, name="", color=None, width=0.15):
        """
        Initialize a 3D strand.

        Args:
            start: numpy array [x, y, z] - start position
            end: numpy array [x, y, z] - end position
            name: strand identifier (e.g., "1_1", "1_2")
            color: RGB tuple (0-1 range), default is orange
            width: tube radius for rendering
        """
        self.name = name
        self.start = np.array(start, dtype=float)
        self.end = np.array(end, dtype=float)

        # Visual properties
        self.color = color if color else (0.9, 0.5, 0.1)  # Orange default
        self.width = width
        self.visible = True

        # Calculate initial control points (1/3 and 2/3 along the strand)
        self._init_control_points()

        # Rendering settings
        self.tube_segments = 16  # Segments around tube circumference
        self.curve_segments = 32  # Segments along curve length

        # Selection/highlight state
        self.is_selected = False
        self.is_hovered = False

        # Attached strands (children)
        self.attached_strands = []

        # Connection info (for LayerStateManager compatibility)
        self.start_connection = None  # {'strand': Strand, 'end': 'start'/'end'}
        self.end_connection = None

    def _init_control_points(self):
        """Initialize control points based on start and end positions"""
        direction = self.end - self.start

        # Place control points at 1/3 and 2/3 along the strand
        # Offset them slightly upward (Y) for initial curve
        offset = np.array([0, 0.3, 0])  # Slight Y offset for visual curve

        self.control_point1 = self.start + direction * 0.33 + offset
        self.control_point2 = self.start + direction * 0.67 + offset

    def get_bezier_point(self, t):
        """
        Get a point on the cubic Bezier curve at parameter t.

        Args:
            t: Parameter from 0 to 1

        Returns:
            numpy array [x, y, z]
        """
        # Cubic Bezier formula: B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        return (mt3 * self.start +
                3 * mt2 * t * self.control_point1 +
                3 * mt * t2 * self.control_point2 +
                t3 * self.end)

    def get_bezier_tangent(self, t):
        """
        Get the tangent vector at parameter t on the Bezier curve.

        Args:
            t: Parameter from 0 to 1

        Returns:
            numpy array [x, y, z] (normalized)
        """
        # Derivative of cubic Bezier
        t2 = t * t
        mt = 1 - t
        mt2 = mt * mt

        tangent = (3 * mt2 * (self.control_point1 - self.start) +
                   6 * mt * t * (self.control_point2 - self.control_point1) +
                   3 * t2 * (self.end - self.control_point2))

        # Normalize
        length = np.linalg.norm(tangent)
        if length > 1e-6:
            tangent /= length

        return tangent

    def get_curve_points(self, num_segments=None):
        """
        Get array of points along the Bezier curve.

        Args:
            num_segments: Number of segments (default: self.curve_segments)

        Returns:
            List of numpy arrays
        """
        if num_segments is None:
            num_segments = self.curve_segments

        points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            points.append(self.get_bezier_point(t))

        return points

    def draw(self, is_selected=False, is_hovered=False):
        """
        Draw the strand as a 3D tube along the Bezier curve.

        Args:
            is_selected: Whether this strand is selected
            is_hovered: Whether mouse is hovering over this strand
        """
        if not self.visible:
            return

        self.is_selected = is_selected
        self.is_hovered = is_hovered

        # Determine color based on state
        if is_selected:
            color = (1.0, 1.0, 0.0)  # Yellow for selected
        elif is_hovered:
            color = (0.7, 0.7, 1.0)  # Light blue for hovered
        else:
            color = self.color

        glColor3f(*color)

        # Draw as tube
        self._draw_tube()

        # Draw end caps
        self._draw_end_caps()

    def _draw_tube(self):
        """Draw the strand as a tube along the Bezier curve using parallel transport frame"""
        curve_points = self.get_curve_points()

        if len(curve_points) < 2:
            return

        # Build frames along the curve using parallel transport
        # This prevents twisting
        frames = self._compute_parallel_frames(curve_points)

        # Generate tube mesh
        for i in range(len(curve_points) - 1):
            p1 = curve_points[i]
            p2 = curve_points[i + 1]

            right1, up1 = frames[i]
            right2, up2 = frames[i + 1]

            # Generate circle of vertices at each point
            circle1 = self._get_circle_from_frame(p1, right1, up1)
            circle2 = self._get_circle_from_frame(p2, right2, up2)

            # Draw quad strip between circles
            glBegin(GL_QUAD_STRIP)
            for j in range(self.tube_segments + 1):
                idx = j % self.tube_segments

                # Normal is direction from center to vertex
                normal1 = circle1[idx] - p1
                norm_len1 = np.linalg.norm(normal1)
                if norm_len1 > 1e-6:
                    normal1 /= norm_len1

                normal2 = circle2[idx] - p2
                norm_len2 = np.linalg.norm(normal2)
                if norm_len2 > 1e-6:
                    normal2 /= norm_len2

                glNormal3f(*normal1)
                glVertex3f(*circle1[idx])

                glNormal3f(*normal2)
                glVertex3f(*circle2[idx])

            glEnd()

    def _compute_parallel_frames(self, points):
        """
        Compute parallel transport frames along the curve.
        This prevents the tube from twisting unexpectedly.

        Returns list of (right, up) tuples for each point.
        """
        frames = []

        # Initial frame at start
        tangent = points[1] - points[0]
        tangent_len = np.linalg.norm(tangent)
        if tangent_len > 1e-6:
            tangent /= tangent_len
        else:
            tangent = np.array([1.0, 0.0, 0.0])

        # Find initial perpendicular vectors
        if abs(tangent[1]) < 0.9:
            up_hint = np.array([0.0, 1.0, 0.0])
        else:
            up_hint = np.array([0.0, 0.0, 1.0])

        right = np.cross(tangent, up_hint)
        right_len = np.linalg.norm(right)
        if right_len > 1e-6:
            right /= right_len
        else:
            right = np.array([1.0, 0.0, 0.0])

        up = np.cross(right, tangent)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        frames.append((right.copy(), up.copy()))

        # Propagate frame along curve (parallel transport)
        for i in range(1, len(points)):
            if i < len(points) - 1:
                tangent_new = points[i + 1] - points[i]
            else:
                tangent_new = points[i] - points[i - 1]

            tangent_len = np.linalg.norm(tangent_new)
            if tangent_len > 1e-6:
                tangent_new /= tangent_len
            else:
                tangent_new = tangent.copy()

            # Rotate the frame to align with new tangent
            # Use reflection method for parallel transport
            v = tangent_new - tangent
            c = np.dot(tangent, tangent_new)

            if c > -0.99:  # Not opposite directions
                # Rodrigues rotation formula simplified
                right = right - (2.0 / (1.0 + c)) * np.dot(v, right) * (tangent + tangent_new) / 2.0

                # Re-orthogonalize
                right = right - np.dot(right, tangent_new) * tangent_new
                right_len = np.linalg.norm(right)
                if right_len > 1e-6:
                    right /= right_len

                up = np.cross(right, tangent_new)
                up_len = np.linalg.norm(up)
                if up_len > 1e-6:
                    up /= up_len

            tangent = tangent_new
            frames.append((right.copy(), up.copy()))

        return frames

    def _get_circle_from_frame(self, center, right, up):
        """
        Get vertices of a circle using pre-computed frame vectors.
        """
        vertices = []
        for i in range(self.tube_segments):
            angle = 2 * np.pi * i / self.tube_segments
            offset = self.width * (np.cos(angle) * right + np.sin(angle) * up)
            vertices.append(center + offset)
        return vertices

    def _get_circle_vertices(self, center, tangent):
        """
        Get vertices of a circle perpendicular to the tangent.
        (Legacy method - kept for compatibility)
        """
        # Find perpendicular vectors
        if abs(tangent[1]) < 0.9:
            up = np.array([0.0, 1.0, 0.0])
        else:
            up = np.array([0.0, 0.0, 1.0])

        # Create perpendicular basis
        right = np.cross(tangent, up)
        right_len = np.linalg.norm(right)
        if right_len > 1e-6:
            right /= right_len

        up = np.cross(right, tangent)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        # Generate circle vertices
        vertices = []
        for i in range(self.tube_segments):
            angle = 2 * np.pi * i / self.tube_segments
            offset = self.width * (np.cos(angle) * right + np.sin(angle) * up)
            vertices.append(center + offset)

        return vertices

    def _draw_end_caps(self):
        """Draw spherical end caps on the tube"""
        # Start cap
        self._draw_sphere(self.start, self.width)

        # End cap
        self._draw_sphere(self.end, self.width)

    def _draw_sphere(self, position, radius):
        """Draw a sphere at the given position"""
        glPushMatrix()
        glTranslatef(*position)

        quadric = gluNewQuadric()
        gluSphere(quadric, radius, 16, 16)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    # ==================== Control Point Methods ====================

    def set_control_point1(self, position):
        """Set the first control point position"""
        self.control_point1 = np.array(position, dtype=float)

    def set_control_point2(self, position):
        """Set the second control point position"""
        self.control_point2 = np.array(position, dtype=float)

    def set_start(self, position):
        """Set the start position"""
        delta = np.array(position, dtype=float) - self.start
        self.start = np.array(position, dtype=float)

        # Move control point 1 with start
        self.control_point1 += delta

    def set_end(self, position):
        """Set the end position"""
        delta = np.array(position, dtype=float) - self.end
        self.end = np.array(position, dtype=float)

        # Move control point 2 with end
        self.control_point2 += delta

    def move(self, delta):
        """Move the entire strand by delta"""
        delta = np.array(delta, dtype=float)
        self.start += delta
        self.end += delta
        self.control_point1 += delta
        self.control_point2 += delta

    # ==================== Serialization ====================

    def to_dict(self):
        """Convert strand to dictionary for saving"""
        return {
            'name': self.name,
            'start': self.start.tolist(),
            'end': self.end.tolist(),
            'control_point1': self.control_point1.tolist(),
            'control_point2': self.control_point2.tolist(),
            'color': self.color,
            'width': self.width,
            'visible': self.visible
        }

    @classmethod
    def from_dict(cls, data):
        """Create strand from dictionary"""
        strand = cls(
            start=data['start'],
            end=data['end'],
            name=data.get('name', ''),
            color=tuple(data.get('color', (0.9, 0.5, 0.1))),
            width=data.get('width', 0.1)
        )

        strand.control_point1 = np.array(data['control_point1'])
        strand.control_point2 = np.array(data['control_point2'])
        strand.visible = data.get('visible', True)

        return strand

    def __repr__(self):
        return f"Strand(name='{self.name}', start={self.start}, end={self.end})"
