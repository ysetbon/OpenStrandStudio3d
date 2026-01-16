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
        self.height_ratio = 0.4  # Height is 40% of width (2.5:1 flat ratio for plastic leather look)
        self.visible = True

        # Calculate initial control points (1/3 and 2/3 along the strand)
        self._init_control_points()

        # Rendering settings
        self.tube_segments = 24  # Segments around circumference (more for smooth ellipse)
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
        # Keep them in the same XZ plane as start/end (no Y offset)
        self.control_point1 = self.start + direction * 0.33
        self.control_point2 = self.start + direction * 0.67

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

        # Use strand's actual color (selection highlight is drawn separately)
        color = self.color

        glColor3f(*color)

        # Check if this strand is a root (not attached to anything)
        # If so, draw the entire chain as one continuous spline
        if self._is_chain_root():
            self._draw_chain_as_spline()
        else:
            # This strand will be drawn as part of its parent's chain
            pass

    def draw_selection_highlight(self):
        """
        Draw a semi-transparent highlight overlay for this strand only.
        Used to show which strand is selected within a chain.
        """
        self._draw_highlight(color=(1.0, 0.0, 0.0, 0.2), width_scale=1.5)

    def draw_hover_highlight(self):
        """Draw a subtle hover highlight for this strand."""
        self._draw_highlight(color=(1.0, 0.85, 0.2, 0.25), width_scale=1.25)

    def _draw_highlight(self, color, width_scale):
        """Draw a semi-transparent overlay along this strand."""
        if not self.visible:
            return

        curve_points = self.get_curve_points()
        if len(curve_points) < 2:
            return

        frames = self._compute_parallel_frames(curve_points)
        if len(frames) < 2:
            return

        highlight_width = self.width * width_scale

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)

        glColor4f(*color)

        height = highlight_width * self.height_ratio

        glBegin(GL_QUAD_STRIP)

        for i in range(len(curve_points) - 1):
            right1, up1 = frames[i]
            right2, up2 = frames[i + 1]
            center1 = curve_points[i]
            center2 = curve_points[i + 1]

            for j in range(self.tube_segments + 1):
                idx = j % self.tube_segments
                angle = 2 * np.pi * idx / self.tube_segments

                cos_a = np.cos(angle)
                sin_a = np.sin(angle)

                offset1 = highlight_width * cos_a * right1 + height * sin_a * up1
                v1 = center1 + offset1
                n1 = cos_a * right1 + sin_a * up1
                n1_len = np.linalg.norm(n1)
                if n1_len > 1e-6:
                    n1 = n1 / n1_len
                glNormal3f(*n1)
                glVertex3f(*v1)

                offset2 = highlight_width * cos_a * right2 + height * sin_a * up2
                v2 = center2 + offset2
                n2 = cos_a * right2 + sin_a * up2
                n2_len = np.linalg.norm(n2)
                if n2_len > 1e-6:
                    n2 = n2 / n2_len
                glNormal3f(*n2)
                glVertex3f(*v2)

        glEnd()

        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)

    def _is_chain_root(self):
        """Check if this strand is the root of a chain (not attached to another strand)"""
        # Base Strand class is always a root
        # AttachedStrand will override this to return False
        return True

    def _get_chain_strands(self):
        """
        Get all strands in this chain, in order from root to leaves.
        Returns a list of strand chains (each chain is a list of strands).
        For now, we follow the first attached strand at each level (linear chain).
        """
        chains = []
        self._collect_chains([], chains)
        return chains

    def _collect_chains(self, current_chain, all_chains):
        """Recursively collect strand chains"""
        current_chain = current_chain + [self]

        # Find strands attached to our end (attachment_side == 1)
        end_attachments = [s for s in self.attached_strands
                          if hasattr(s, 'attachment_side') and s.attachment_side == 1]

        if not end_attachments:
            # End of chain - save it
            all_chains.append(current_chain)
        else:
            # Continue chain with each attached strand
            for attached in end_attachments:
                attached._collect_chains(current_chain, all_chains)

    def _draw_chain_as_spline(self):
        """Draw the entire strand chain as one continuous Bezier spline"""
        chains = self._get_chain_strands()

        for chain in chains:
            if not chain:
                continue

            # Collect all curve points from all strands in the chain
            all_points = []
            for i, strand in enumerate(chain):
                points = strand.get_curve_points()
                if i == 0:
                    # First strand - include all points
                    all_points.extend(points)
                else:
                    # Skip first point (it's the same as previous strand's last point)
                    all_points.extend(points[1:])

            if len(all_points) < 2:
                continue

            # Compute parallel transport frames for the entire chain
            frames = self._compute_chain_frames(all_points)

            # Draw as one continuous tube
            self._draw_tube_from_points(all_points, frames)

            # Draw end caps only at the true start and end of the chain
            # Pass frames and points so end caps use the same orientation as the tube
            self._draw_chain_end_caps(chain, all_points, frames)

    def _compute_chain_frames(self, points):
        """Compute parallel transport frames for a chain of points"""
        frames = []
        n = len(points)

        if n < 2:
            return frames

        # Initial frame at first point
        tangent = points[1] - points[0]
        tangent_len = np.linalg.norm(tangent)
        if tangent_len > 1e-6:
            tangent /= tangent_len

        # Find initial right and up vectors
        if abs(tangent[1]) < 0.9:
            up_hint = np.array([0.0, 1.0, 0.0])
        else:
            up_hint = np.array([0.0, 0.0, 1.0])

        right = np.cross(tangent, up_hint)
        right_len = np.linalg.norm(right)
        if right_len > 1e-6:
            right /= right_len

        up = np.cross(right, tangent)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        frames.append((right.copy(), up.copy()))

        # Propagate frame using parallel transport
        for i in range(1, n):
            if i < n - 1:
                new_tangent = points[i + 1] - points[i]
            else:
                new_tangent = points[i] - points[i - 1]

            new_tangent_len = np.linalg.norm(new_tangent)
            if new_tangent_len > 1e-6:
                new_tangent /= new_tangent_len

            # Parallel transport the frame
            dot = np.dot(tangent, new_tangent)

            if dot < -0.99:
                # Nearly opposite - flip
                right = -right
            elif dot < 0.99:
                # Rotate frame
                axis = np.cross(tangent, new_tangent)
                axis_len = np.linalg.norm(axis)
                if axis_len > 1e-6:
                    axis /= axis_len
                    angle = np.arccos(np.clip(dot, -1.0, 1.0))
                    right = self._rotate_vector(right, axis, angle)

            up = np.cross(right, new_tangent)
            up_len = np.linalg.norm(up)
            if up_len > 1e-6:
                up /= up_len

            right = np.cross(new_tangent, up)
            right_len = np.linalg.norm(right)
            if right_len > 1e-6:
                right /= right_len

            frames.append((right.copy(), up.copy()))
            tangent = new_tangent

        return frames

    def _rotate_vector(self, v, axis, angle):
        """Rotate vector v around axis by angle (Rodrigues' formula)"""
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        return v * cos_a + np.cross(axis, v) * sin_a + axis * np.dot(axis, v) * (1 - cos_a)

    def _draw_tube_from_points(self, points, frames):
        """Draw a tube along the given points using the provided frames"""
        if len(points) < 2 or len(frames) < 2:
            return

        height = self.width * self.height_ratio

        glBegin(GL_QUAD_STRIP)

        for i in range(len(points) - 1):
            right1, up1 = frames[i]
            right2, up2 = frames[i + 1]
            center1 = points[i]
            center2 = points[i + 1]

            for j in range(self.tube_segments + 1):
                idx = j % self.tube_segments
                angle = 2 * np.pi * idx / self.tube_segments

                # Elliptical cross-section
                cos_a = np.cos(angle)
                sin_a = np.sin(angle)

                # First ring vertex
                offset1 = self.width * cos_a * right1 + height * sin_a * up1
                v1 = center1 + offset1
                n1 = cos_a * right1 + sin_a * up1
                n1 /= np.linalg.norm(n1)
                glNormal3f(*n1)
                glVertex3f(*v1)

                # Second ring vertex
                offset2 = self.width * cos_a * right2 + height * sin_a * up2
                v2 = center2 + offset2
                n2 = cos_a * right2 + sin_a * up2
                n2 /= np.linalg.norm(n2)
                glNormal3f(*n2)
                glVertex3f(*v2)

        glEnd()

    def _draw_chain_end_caps(self, chain, all_points=None, frames=None):
        """
        Draw end caps only at the true start and end of the chain.

        Uses the parallel transport frames from tube rendering to ensure
        end cap orientation matches the tube exactly.
        """
        if not chain:
            return

        first_strand = chain[0]
        last_strand = chain[-1]

        # Use frames if provided (for consistent orientation with tube)
        if all_points is not None and frames is not None and len(all_points) >= 2 and len(frames) >= 2:
            # Start cap - use tangent from first two points (matches tube start)
            tangent_start = all_points[1] - all_points[0]
            tangent_len = np.linalg.norm(tangent_start)
            if tangent_len > 1e-6:
                tangent_start = tangent_start / tangent_len
            self._draw_ellipsoid_cap_with_frame(first_strand.start, tangent_start, frames[0])

            # End cap - use tangent from last two points (matches tube end)
            tangent_end = all_points[-1] - all_points[-2]
            tangent_len = np.linalg.norm(tangent_end)
            if tangent_len > 1e-6:
                tangent_end = tangent_end / tangent_len
            self._draw_ellipsoid_cap_with_frame(last_strand.end, tangent_end, frames[-1])
        else:
            # Fallback to original behavior if frames not provided
            tangent_start = first_strand.get_bezier_tangent(0.0)
            self._draw_ellipsoid_cap(first_strand.start, tangent_start)

            tangent_end = last_strand.get_bezier_tangent(1.0)
            self._draw_ellipsoid_cap(last_strand.end, tangent_end)

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

    def _get_ellipse_from_frame(self, center, right, up):
        """
        Get vertices of an ellipse using pre-computed frame vectors.
        Creates a flat, lenticular cross-section for plastic leather look.

        - 'right' direction: full width
        - 'up' direction: reduced height (height_ratio * width)
        """
        vertices = []
        height = self.width * self.height_ratio

        for i in range(self.tube_segments):
            angle = 2 * np.pi * i / self.tube_segments
            # Ellipse: width in 'right' direction, height in 'up' direction
            offset = (self.width * np.cos(angle) * right +
                     height * np.sin(angle) * up)
            vertices.append(center + offset)
        return vertices

    def _get_circle_from_frame(self, center, right, up):
        """
        Get vertices of a circle using pre-computed frame vectors.
        Now redirects to ellipse for plastic leather look.
        """
        return self._get_ellipse_from_frame(center, right, up)

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
        """Draw ellipsoid end caps on the tube"""
        tangent_start = self.get_bezier_tangent(0.0)
        tangent_end = self.get_bezier_tangent(1.0)

        # Draw both end caps
        self._draw_ellipsoid_cap(self.start, tangent_start)
        self._draw_ellipsoid_cap(self.end, tangent_end)

    def _draw_ellipsoid_cap(self, position, tangent):
        """Draw an ellipsoid cap at the given position, oriented along tangent"""
        glPushMatrix()
        glTranslatef(*position)

        # Calculate orientation to align with tangent
        # We need to rotate the ellipsoid so its long axis aligns with 'right' vector
        if abs(tangent[1]) < 0.9:
            up_hint = np.array([0.0, 1.0, 0.0])
        else:
            up_hint = np.array([0.0, 0.0, 1.0])

        right = np.cross(tangent, up_hint)
        right_len = np.linalg.norm(right)
        if right_len > 1e-6:
            right /= right_len

        up = np.cross(right, tangent)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        # Build rotation matrix (column vectors: right, up, tangent)
        rotation = np.array([
            [right[0], up[0], tangent[0], 0],
            [right[1], up[1], tangent[1], 0],
            [right[2], up[2], tangent[2], 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        glMultMatrixf(rotation.T.flatten())

        # Scale to create ellipsoid: wide in X (right), flat in Y (up), short in Z (tangent)
        height = self.width * self.height_ratio
        glScalef(self.width, height, self.width * 0.5)  # Hemisphere depth

        # Enable normal renormalization for correct lighting after scaling
        glEnable(GL_NORMALIZE)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)  # Smooth normals for proper lighting
        gluSphere(quadric, 1.0, 16, 16)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _draw_ellipsoid_cap_with_frame(self, position, tangent, frame):
        """
        Draw an ellipsoid cap using a pre-computed frame for orientation.

        This ensures the cap orientation matches the tube exactly by using
        the same frame (right, up vectors) computed during parallel transport.

        Args:
            position: 3D position for the cap
            tangent: Tangent direction at this point
            frame: Tuple of (right, up) vectors from parallel transport
        """
        glPushMatrix()
        glTranslatef(*position)

        # Use the pre-computed frame vectors
        right, up = frame

        # Ensure tangent is normalized
        tangent = np.array(tangent, dtype=float)
        tangent_len = np.linalg.norm(tangent)
        if tangent_len > 1e-6:
            tangent = tangent / tangent_len

        # Build rotation matrix (column vectors: right, up, tangent)
        rotation = np.array([
            [right[0], up[0], tangent[0], 0],
            [right[1], up[1], tangent[1], 0],
            [right[2], up[2], tangent[2], 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        glMultMatrixf(rotation.T.flatten())

        # Scale to create ellipsoid: wide in X (right), flat in Y (up), short in Z (tangent)
        height = self.width * self.height_ratio
        glScalef(self.width, height, self.width * 0.5)  # Hemisphere depth

        # Enable normal renormalization for correct lighting after scaling
        glEnable(GL_NORMALIZE)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)  # Smooth normals for proper lighting
        gluSphere(quadric, 1.0, 16, 16)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _draw_sphere(self, position, radius):
        """Draw a sphere at the given position (legacy, now uses ellipsoid)"""
        glPushMatrix()
        glTranslatef(*position)

        # Scale to ellipsoid shape
        height = radius * self.height_ratio
        glScalef(radius, height, radius)

        # Enable normal renormalization for correct lighting after scaling
        glEnable(GL_NORMALIZE)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)  # Smooth normals for proper lighting
        gluSphere(quadric, 1.0, 16, 16)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    # ==================== Control Point Methods ====================

    def get_default_control_points(self):
        """
        Calculate what the default control points would be for current start/end.
        Default is 1/3 and 2/3 along the direction from start to end.

        Returns:
            tuple: (cp1, cp2) numpy arrays
        """
        direction = self.end - self.start
        cp1 = self.start + direction * 0.33
        cp2 = self.start + direction * 0.67
        return cp1, cp2

    def is_control_points_default(self, tolerance=1e-4):
        """
        Check if control points are at their default positions (1/3 and 2/3 along strand).

        Args:
            tolerance: Maximum distance to consider as "default"

        Returns:
            bool: True if CPs are at default positions
        """
        expected_cp1, expected_cp2 = self.get_default_control_points()
        return (np.allclose(self.control_point1, expected_cp1, atol=tolerance) and
                np.allclose(self.control_point2, expected_cp2, atol=tolerance))

    def make_straight(self):
        """
        Set control points to make the strand a straight line.
        CPs are placed at 1/3 and 2/3 along the line from start to end.
        """
        direction = self.end - self.start
        self.control_point1 = self.start + direction * 0.33
        self.control_point2 = self.start + direction * 0.67

    def save_control_points(self):
        """
        Save current control point state for later restoration.

        Returns:
            dict: Contains cp1, cp2 arrays and is_default flag
        """
        return {
            'cp1': self.control_point1.copy(),
            'cp2': self.control_point2.copy(),
            'is_default': self.is_control_points_default()
        }

    def restore_control_points(self, saved):
        """
        Restore control points from saved state.
        If saved state was default, recalculates default for current positions.

        Args:
            saved: dict from save_control_points() or None
        """
        if saved is None:
            # No saved state - use default
            self._init_control_points()
            return

        if saved.get('is_default', False):
            # Was default - recalculate default for current start/end
            self._init_control_points()
        else:
            # Was custom - restore exact positions
            self.control_point1 = saved['cp1'].copy()
            self.control_point2 = saved['cp2'].copy()

    def set_control_point1(self, position):
        """Set the first control point position"""
        self.control_point1 = np.array(position, dtype=float)

        # Sync attached strands at start (attachment_side == 0) for C1 continuity
        for attached in self.attached_strands:
            if hasattr(attached, 'attachment_side') and attached.attachment_side == 0:
                if hasattr(attached, 'sync_cp1_with_parent'):
                    attached.sync_cp1_with_parent()

    def set_control_point2(self, position):
        """Set the second control point position"""
        self.control_point2 = np.array(position, dtype=float)

        # Sync attached strands at end (attachment_side == 1) for C1 continuity
        for attached in self.attached_strands:
            if hasattr(attached, 'attachment_side') and attached.attachment_side == 1:
                if hasattr(attached, 'sync_cp1_with_parent'):
                    attached.sync_cp1_with_parent()

    def set_start(self, position):
        """Set the start position"""
        delta = np.array(position, dtype=float) - self.start
        self.start = np.array(position, dtype=float)

        # Move control point 1 with start
        self.control_point1 += delta

        # Update attached strands at start (attachment_side == 0)
        for attached in self.attached_strands:
            if hasattr(attached, 'attachment_side') and attached.attachment_side == 0:
                if hasattr(attached, 'update_start_from_parent'):
                    attached.update_start_from_parent()
                if hasattr(attached, 'sync_cp1_with_parent'):
                    attached.sync_cp1_with_parent()

    def set_end(self, position):
        """Set the end position"""
        delta = np.array(position, dtype=float) - self.end
        self.end = np.array(position, dtype=float)

        # Move control point 2 with end
        self.control_point2 += delta

        # Update attached strands at end (attachment_side == 1)
        for attached in self.attached_strands:
            if hasattr(attached, 'attachment_side') and attached.attachment_side == 1:
                if hasattr(attached, 'update_start_from_parent'):
                    attached.update_start_from_parent()
                if hasattr(attached, 'sync_cp1_with_parent'):
                    attached.sync_cp1_with_parent()

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
            'height_ratio': self.height_ratio,
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
            width=data.get('width', 0.15)
        )

        strand.control_point1 = np.array(data['control_point1'])
        strand.control_point2 = np.array(data['control_point2'])
        strand.height_ratio = data.get('height_ratio', 0.4)
        strand.visible = data.get('visible', True)

        return strand

    def __repr__(self):
        return f"Strand(name='{self.name}', start={self.start}, end={self.end})"
