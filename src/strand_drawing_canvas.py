"""
OpenStrandStudio 3D - Strand Drawing Canvas
OpenGL-based 3D canvas for rendering and manipulating strands
"""

import math
import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QKeyEvent

from OpenGL.GL import *
from OpenGL.GLU import *

from move_mode import MoveModeMixin
from attach_mode import AttachModeMixin


class StrandDrawingCanvas(QOpenGLWidget, MoveModeMixin, AttachModeMixin):
    """3D OpenGL canvas for strand visualization and manipulation"""

    # Signals
    mode_changed = pyqtSignal(str)
    camera_changed = pyqtSignal(str)
    strand_created = pyqtSignal(str)
    strand_selected = pyqtSignal(str)
    strand_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Interaction mode
        self.current_mode = "select"

        # Camera parameters
        self.camera_distance = 10.0
        self.camera_azimuth = 45.0    # Horizontal rotation (degrees)
        self.camera_elevation = 30.0   # Vertical rotation (degrees)
        self.camera_target = np.array([0.0, 0.0, 0.0])  # Look-at point

        # Mouse tracking
        self.last_mouse_pos = QPoint()
        self.mouse_pressed = False
        self.mouse_button = None

        # Strand data
        self.strands = []  # List of Strand objects
        self.selected_strand = None
        self.hovered_strand = None

        # Strand creation state
        self.creating_strand = False
        self.new_strand_start = None

        # Move mode state
        self.moving_strand = None
        self.moving_control_point = None  # 'start', 'end', 'cp1', 'cp2', or None for whole strand
        self.move_start_pos = None  # 3D position where drag started
        self.hovered_control_point = None  # Which control point is hovered: 'start', 'end', 'cp1', 'cp2'
        self.control_point_box_size = 0.25  # Size of control point boxes

        # Attach mode state
        self.attaching = False
        self.attach_parent_strand = None
        self.attach_side = None  # 0=start, 1=end
        self.attach_new_strand = None
        self.hovered_attach_point = None  # (strand, side) tuple for hover feedback
        self.attach_sphere_radius = 0.3  # Radius of attachment point spheres

        # Rigid mode state - shows start/end point spheres
        self.show_rigid_points = False
        self.rigid_sphere_radius = 0.12  # Small spheres at strand endpoints

        # Straight segment mode state - forces strands to be straight lines
        self.straight_segment_mode = False
        self.saved_control_points = {}  # Maps strand id -> saved CP data for restoration

        # Grid and axes settings
        self.show_grid = True
        self.show_axes = True
        self.grid_size = 10
        self.grid_spacing = 1.0

        # Rendering settings
        self.background_color = (0.15, 0.15, 0.15, 1.0)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Set focus policy for keyboard input
        self.setFocusPolicy(Qt.StrongFocus)

    def initializeGL(self):
        """Initialize OpenGL settings"""
        glClearColor(*self.background_color)

        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Enable smooth lines
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

        # Enable lighting
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_LIGHT2)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        # Normalize normals (important for scaled geometry)
        glEnable(GL_NORMALIZE)

        # === KEY LIGHT (from above-front) ===
        # Main light casting shadows - positioned high and slightly in front
        # w=0.0 makes it directional (like sun), cheaper than point light
        glLightfv(GL_LIGHT0, GL_POSITION, [0.3, 1.0, 0.5, 0.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.15, 0.15, 0.15, 1.0])  # Low ambient for contrast
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.85, 0.85, 0.80, 1.0])  # Warm white
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 0.95, 1.0])

        # === FILL LIGHT (from below-side) ===
        # Softer light to fill in shadows - prevents pure black areas
        glLightfv(GL_LIGHT1, GL_POSITION, [-0.5, -0.3, 0.4, 0.0])
        glLightfv(GL_LIGHT1, GL_AMBIENT, [0.0, 0.0, 0.0, 1.0])
        glLightfv(GL_LIGHT1, GL_DIFFUSE, [0.25, 0.25, 0.30, 1.0])  # Cool, dim
        glLightfv(GL_LIGHT1, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])    # No specular

        # === RIM LIGHT (from behind) ===
        # Creates subtle edge highlighting for depth
        glLightfv(GL_LIGHT2, GL_POSITION, [0.0, 0.5, -1.0, 0.0])
        glLightfv(GL_LIGHT2, GL_AMBIENT, [0.0, 0.0, 0.0, 1.0])
        glLightfv(GL_LIGHT2, GL_DIFFUSE, [0.2, 0.2, 0.25, 1.0])   # Subtle blue tint
        glLightfv(GL_LIGHT2, GL_SPECULAR, [0.3, 0.3, 0.35, 1.0])

        # Material properties - plastic leather sheen
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.7, 0.7, 0.7, 1.0])  # Brighter specular for plastic look
        glMaterialf(GL_FRONT, GL_SHININESS, 64.0)  # Higher = tighter, glossier highlights

    def resizeGL(self, width, height):
        """Handle widget resize"""
        if height == 0:
            height = 1

        glViewport(0, 0, width, height)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        aspect = width / height
        gluPerspective(45.0, aspect, 0.1, 1000.0)

        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        """Render the scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Setup camera
        self._setup_camera()

        # Draw grid
        if self.show_grid:
            self._draw_grid()

        # Draw coordinate axes
        if self.show_axes:
            self._draw_axes()

        # Draw all strands
        self._draw_strands()

        # Draw creation preview if creating strand
        if self.creating_strand and self.new_strand_start is not None:
            self._draw_strand_preview()

        # Draw control points for selected strand (from MoveModeMixin)
        if self.selected_strand is not None:
            self._draw_control_points()

        # Draw attachment points in attach mode (from AttachModeMixin)
        if self.current_mode == "attach":
            self._draw_attachment_points()

        # Draw rigid points (start/end spheres) if enabled
        if self.show_rigid_points:
            self._draw_rigid_points()

    def _setup_camera(self):
        """Setup the camera view matrix"""
        # Convert spherical to Cartesian coordinates
        azimuth_rad = math.radians(self.camera_azimuth)
        elevation_rad = math.radians(self.camera_elevation)

        camera_x = self.camera_target[0] + self.camera_distance * math.cos(elevation_rad) * math.sin(azimuth_rad)
        camera_y = self.camera_target[1] + self.camera_distance * math.sin(elevation_rad)
        camera_z = self.camera_target[2] + self.camera_distance * math.cos(elevation_rad) * math.cos(azimuth_rad)

        gluLookAt(
            camera_x, camera_y, camera_z,  # Camera position
            self.camera_target[0], self.camera_target[1], self.camera_target[2],  # Look at
            0.0, 1.0, 0.0  # Up vector
        )

        # Emit camera info
        self.camera_changed.emit(f"Dist: {self.camera_distance:.1f}, Az: {self.camera_azimuth:.0f}, El: {self.camera_elevation:.0f}")

    def _draw_grid(self):
        """Draw a reference grid on the XZ plane"""
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)

        half_size = self.grid_size * self.grid_spacing / 2

        # Grid lines (gray)
        glColor4f(0.3, 0.3, 0.3, 0.5)

        for i in range(-self.grid_size // 2, self.grid_size // 2 + 1):
            pos = i * self.grid_spacing
            # X direction lines
            glVertex3f(-half_size, 0, pos)
            glVertex3f(half_size, 0, pos)
            # Z direction lines
            glVertex3f(pos, 0, -half_size)
            glVertex3f(pos, 0, half_size)

        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_axes(self):
        """Draw coordinate axes"""
        glDisable(GL_LIGHTING)
        glLineWidth(2.0)
        glBegin(GL_LINES)

        axis_length = 2.0

        # X axis - Red
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(axis_length, 0, 0)

        # Y axis - Green
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, axis_length, 0)

        # Z axis - Blue
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, axis_length)

        glEnd()
        glLineWidth(1.0)
        glEnable(GL_LIGHTING)

    def _draw_strands(self):
        """Draw all strands in the scene"""
        for strand in self.strands:
            is_selected = (strand == self.selected_strand)
            is_hovered = (strand == self.hovered_strand)
            strand.draw(is_selected, is_hovered)

        # Draw selection highlight for selected strand (semi-transparent overlay)
        if self.selected_strand and self.selected_strand.visible:
            self.selected_strand.draw_selection_highlight()

    def _draw_strand_preview(self):
        """Draw preview while creating a new strand"""
        if self.new_strand_start is None:
            return

        # Get current mouse position in 3D
        end_pos = self._get_mouse_3d_position()
        if end_pos is None:
            return

        glDisable(GL_LIGHTING)
        glLineWidth(3.0)
        glColor4f(1.0, 1.0, 0.0, 0.7)  # Yellow preview

        glBegin(GL_LINES)
        glVertex3f(*self.new_strand_start)
        glVertex3f(*end_pos)
        glEnd()

        glLineWidth(1.0)
        glEnable(GL_LIGHTING)

    def _draw_sphere(self, position, radius, color):
        """Draw a simple sphere at the given position"""
        glPushMatrix()
        glTranslatef(*position)
        glColor3f(*color)

        quadric = gluNewQuadric()
        gluSphere(quadric, radius, 16, 16)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _draw_rigid_points(self):
        """Draw small spheres at start/end points of all strands when rigid mode is enabled"""
        from attached_strand import AttachedStrand

        for strand in self.strands:
            if not strand.visible:
                continue

            # Use the strand's color for the spheres
            color = strand.color

            # For AttachedStrand, don't draw sphere at the attached start point
            # (it's connected to parent, so only draw at the free end)
            if isinstance(strand, AttachedStrand):
                # Only draw at end point (start is attached to parent)
                self._draw_sphere(strand.end, self.rigid_sphere_radius, color)
            else:
                # Regular strand - draw at both start and end
                self._draw_sphere(strand.start, self.rigid_sphere_radius, color)
                self._draw_sphere(strand.end, self.rigid_sphere_radius, color)

    def _get_mouse_3d_position(self, ground_y=0.0):
        """Convert current mouse position to 3D point on ground plane"""
        # Get mouse position
        mouse_pos = self.mapFromGlobal(self.cursor().pos())
        return self._screen_to_ground(mouse_pos.x(), mouse_pos.y(), ground_y)

    def _screen_to_ground(self, screen_x, screen_y, ground_y=0.0):
        """Convert screen coordinates to 3D point on ground plane (Y = ground_y)"""
        # Make sure we have OpenGL context
        self.makeCurrent()

        # Setup matrices (same as in paintGL)
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

        # Setup camera (same as _setup_camera)
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

        # Get viewport, modelview and projection matrices
        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)

        # Flip Y coordinate (OpenGL has origin at bottom-left)
        win_y = viewport[3] - screen_y

        result = None
        try:
            # Get ray from camera through screen point
            near_point = gluUnProject(screen_x, win_y, 0.0, modelview, projection, viewport)
            far_point = gluUnProject(screen_x, win_y, 1.0, modelview, projection, viewport)

            # Calculate ray direction
            ray_dir = np.array(far_point) - np.array(near_point)
            ray_origin = np.array(near_point)

            # Intersect with ground plane (Y = ground_y)
            if abs(ray_dir[1]) > 1e-6:
                t = (ground_y - ray_origin[1]) / ray_dir[1]
                if t >= 0:
                    intersection = ray_origin + t * ray_dir
                    result = tuple(intersection)
        except Exception as e:
            print(f"Error in _screen_to_ground: {e}")

        # Restore matrices
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        return result

    # ==================== Mouse Events ====================

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press"""
        self.last_mouse_pos = event.pos()
        self.mouse_pressed = True
        self.mouse_button = event.button()

        if event.button() == Qt.LeftButton:
            if self.current_mode == "add_strand":
                # Start creating a new strand
                pos_3d = self._screen_to_ground(event.x(), event.y())
                print(f"Add strand mode - click at screen ({event.x()}, {event.y()}) -> 3D: {pos_3d}")
                if pos_3d:
                    self.creating_strand = True
                    self.new_strand_start = pos_3d
                else:
                    print("Could not get 3D position - click on the grid area")

            elif self.current_mode == "select":
                # Try to select a strand
                self._try_select_strand(event.x(), event.y())

            elif self.current_mode == "move":
                # Start moving selected strand or control point (from MoveModeMixin)
                self._start_move(event.x(), event.y())

            elif self.current_mode == "attach":
                # Start attaching a new strand (from AttachModeMixin)
                self._start_attach(event.x(), event.y())

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            if self.creating_strand and self.new_strand_start is not None:
                # Finish creating strand
                end_pos = self._screen_to_ground(event.x(), event.y())
                print(f"Release at screen ({event.x()}, {event.y()}) -> 3D: {end_pos}")
                if end_pos:
                    self._create_strand(self.new_strand_start, end_pos)
                else:
                    print("Could not get end 3D position")

                self.creating_strand = False
                self.new_strand_start = None

            elif self.current_mode == "move" and self.moving_strand:
                # End move operation (from MoveModeMixin)
                self._end_move()

            elif self.current_mode == "attach" and self.attaching:
                # Finish attachment (from AttachModeMixin)
                self._finish_attach(event.x(), event.y())

        self.mouse_pressed = False
        self.mouse_button = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Handle mouse move with camera controls similar to SolidWorks/Blender:

        Camera Controls:
        - Middle mouse drag: Orbit (rotate view)
        - Shift + Middle mouse: Pan
        - Ctrl + Middle mouse: Zoom
        - Right mouse drag: Also orbit
        - Scroll wheel: Zoom
        """
        dx = event.x() - self.last_mouse_pos.x()
        dy = event.y() - self.last_mouse_pos.y()

        modifiers = event.modifiers()
        shift_held = bool(modifiers & Qt.ShiftModifier)
        ctrl_held = bool(modifiers & Qt.ControlModifier)

        if self.mouse_pressed:
            if self.mouse_button == Qt.MiddleButton:
                if ctrl_held:
                    # Ctrl + Middle mouse: Zoom
                    zoom_speed = 0.01
                    zoom_factor = 1.0 + dy * zoom_speed
                    self.camera_distance *= zoom_factor
                    self.camera_distance = max(1.0, min(100.0, self.camera_distance))
                elif shift_held:
                    # Shift + Middle mouse: Pan
                    self._pan_camera(dx, dy)
                else:
                    # Middle mouse drag: Orbit
                    self._orbit_camera(dx, dy)

            elif self.mouse_button == Qt.RightButton:
                if shift_held:
                    # Shift + Right mouse: Pan (alternative)
                    self._pan_camera(dx, dy)
                else:
                    # Right mouse drag: Orbit
                    self._orbit_camera(dx, dy)

            elif self.mouse_button == Qt.LeftButton:
                if self.creating_strand:
                    # Update preview while creating strand
                    pass  # Just trigger update below
                elif self.current_mode == "move" and self.moving_strand:
                    # Update move - check modifiers for movement direction (from MoveModeMixin)
                    # Shift = vertical (Y), Ctrl = depth (towards/away from camera)
                    self._update_move(event.x(), event.y(), shift_held=shift_held, ctrl_held=ctrl_held)
                elif self.current_mode == "attach" and self.attaching:
                    # Update attached strand end position (from AttachModeMixin)
                    # Note: Ignore Ctrl/Shift in attach mode - only basic mouse movement
                    self._update_attach(event.x(), event.y(), shift_held=False)
        else:
            # Not dragging - check for hover states
            if self.current_mode == "move" and self.selected_strand:
                self._update_control_point_hover(event.x(), event.y())
            elif self.current_mode == "attach":
                self._update_attach_point_hover(event.x(), event.y())

        self.last_mouse_pos = event.pos()
        self.update()

    def _orbit_camera(self, dx, dy):
        """Orbit camera around target"""
        self.camera_azimuth -= dx * 0.5
        self.camera_elevation += dy * 0.5
        # Clamp elevation to avoid gimbal lock
        self.camera_elevation = max(-89, min(89, self.camera_elevation))

    def _pan_camera(self, dx, dy):
        """Pan camera (move target point)"""
        pan_speed = self.camera_distance * 0.002

        # Calculate right and up vectors based on current view
        azimuth_rad = math.radians(self.camera_azimuth)
        elevation_rad = math.radians(self.camera_elevation)

        # Right vector (perpendicular to view direction in XZ plane)
        right = np.array([math.cos(azimuth_rad), 0, -math.sin(azimuth_rad)])

        # Up vector (perpendicular to view direction and right)
        # For more accurate panning, calculate based on elevation too
        forward = np.array([
            -math.cos(elevation_rad) * math.sin(azimuth_rad),
            -math.sin(elevation_rad),
            -math.cos(elevation_rad) * math.cos(azimuth_rad)
        ])
        up = np.cross(right, forward)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        self.camera_target -= right * dx * pan_speed
        self.camera_target += up * dy * pan_speed

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zoom"""
        delta = event.angleDelta().y()

        # Zoom in/out
        zoom_factor = 1.1 if delta < 0 else 0.9
        self.camera_distance *= zoom_factor

        # Clamp distance
        self.camera_distance = max(1.0, min(100.0, self.camera_distance))

        self.update()

    def keyPressEvent(self, event: QKeyEvent):
        """
        Handle key press.

        Camera View Shortcuts (like Blender numpad):
        - 1: Front view
        - 3: Right view
        - 7: Top view
        - 5: Toggle perspective/orthographic (future)
        - 0: Reset to default perspective
        - F: Focus on selected strand

        Other:
        - Delete: Delete selected strand
        - Escape: Cancel/deselect
        - G: Toggle grid/axes (via toolbar shortcut)
        - Home: Reset camera
        """
        if event.key() == Qt.Key_Delete:
            # Delete selected strand
            if self.selected_strand:
                self._delete_selected_strand()

        elif event.key() == Qt.Key_Escape:
            # Cancel current operation or deselect
            if self.creating_strand:
                self.creating_strand = False
                self.new_strand_start = None
            else:
                self.selected_strand = None
                self.strand_selected.emit("")

        # Note: 'G' key for grid/axes toggle is handled by toolbar action shortcut

        # Camera view shortcuts
        elif event.key() == Qt.Key_1:
            # Front view (looking at XY plane from +Z)
            self.camera_azimuth = 0
            self.camera_elevation = 0
            print("View: Front")

        elif event.key() == Qt.Key_2:
            # Back view (looking at XY plane from -Z)
            self.camera_azimuth = 180
            self.camera_elevation = 0
            print("View: Back")

        elif event.key() == Qt.Key_3:
            # Right view (looking at YZ plane from +X)
            self.camera_azimuth = 90
            self.camera_elevation = 0
            print("View: Right")

        elif event.key() == Qt.Key_4:
            # Left view (looking at YZ plane from -X)
            self.camera_azimuth = -90
            self.camera_elevation = 0
            print("View: Left")

        elif event.key() == Qt.Key_7:
            # Top view (looking down at XZ plane from +Y)
            self.camera_azimuth = 0
            self.camera_elevation = 89  # Almost 90 to avoid gimbal lock
            print("View: Top")

        elif event.key() == Qt.Key_9:
            # Bottom view (looking up at XZ plane from -Y)
            self.camera_azimuth = 0
            self.camera_elevation = -89
            print("View: Bottom")

        elif event.key() == Qt.Key_0 or event.key() == Qt.Key_Home:
            # Reset to default perspective view
            self.reset_camera()
            print("View: Default Perspective")

        elif event.key() == Qt.Key_F:
            # Focus on selected strand
            if self.selected_strand:
                self._focus_on_strand(self.selected_strand)
                print(f"Focused on {self.selected_strand.name}")

        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            # Zoom in
            self.camera_distance *= 0.8
            self.camera_distance = max(1.0, self.camera_distance)

        elif event.key() == Qt.Key_Minus:
            # Zoom out
            self.camera_distance *= 1.25
            self.camera_distance = min(100.0, self.camera_distance)

        self.update()

    def _focus_on_strand(self, strand):
        """Move camera target to focus on a strand"""
        # Calculate center of strand
        center = (strand.start + strand.end) / 2
        self.camera_target = center.copy()

        # Adjust distance based on strand length
        strand_length = np.linalg.norm(strand.end - strand.start)
        self.camera_distance = max(strand_length * 2, 5.0)

    # ==================== Strand Operations ====================

    def _create_strand(self, start, end):
        """Create a new strand"""
        from strand import Strand

        # Check minimum length
        start_arr = np.array(start)
        end_arr = np.array(end)
        length = np.linalg.norm(end_arr - start_arr)

        if length < 0.3:  # Minimum length threshold
            print(f"Strand too short: {length:.2f} - need at least 0.3")
            return

        # Generate strand name
        set_number = self._get_next_set_number()
        strand_name = f"{set_number}_1"

        # Create strand
        strand = Strand(
            start=start_arr,
            end=end_arr,
            name=strand_name
        )

        # If in straight mode, make sure new strand is straight
        # (it should already be straight by default, but this ensures consistency)
        if self.straight_segment_mode:
            strand.make_straight()

        self.strands.append(strand)
        self.selected_strand = strand

        print(f"Created strand '{strand_name}': {start} -> {end} (length: {length:.2f})")

        self.strand_created.emit(strand_name)
        self.strand_selected.emit(strand_name)

    def _get_next_set_number(self):
        """Get the next available set number"""
        if not self.strands:
            return 1

        # Find max set number
        max_set = 0
        for strand in self.strands:
            parts = strand.name.split('_')
            if len(parts) >= 1:
                try:
                    set_num = int(parts[0])
                    max_set = max(max_set, set_num)
                except ValueError:
                    pass

        return max_set + 1

    def _try_select_strand(self, screen_x, screen_y):
        """Try to select a strand at the given screen position"""
        # Simple ray-based selection (can be improved)
        closest_strand = None
        closest_dist = float('inf')

        for strand in self.strands:
            dist = self._get_strand_screen_distance(strand, screen_x, screen_y)
            if dist < closest_dist and dist < 20:  # 20 pixel threshold
                closest_dist = dist
                closest_strand = strand

        self.selected_strand = closest_strand

        if closest_strand:
            self.strand_selected.emit(closest_strand.name)
        else:
            self.strand_selected.emit("")

    def _get_strand_screen_distance(self, strand, screen_x, screen_y):
        """Get approximate screen distance to a strand"""
        # Project strand midpoint to screen
        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)

        midpoint = (strand.start + strand.end) / 2

        try:
            screen_pos = gluProject(midpoint[0], midpoint[1], midpoint[2],
                                   modelview, projection, viewport)

            dx = screen_pos[0] - screen_x
            dy = (viewport[3] - screen_pos[1]) - screen_y

            return math.sqrt(dx * dx + dy * dy)
        except:
            return float('inf')

    def _delete_selected_strand(self):
        """Delete the currently selected strand"""
        if self.selected_strand:
            strand_name = self.selected_strand.name

            # Clean up saved control points if in straight mode
            strand_id = id(self.selected_strand)
            if strand_id in self.saved_control_points:
                del self.saved_control_points[strand_id]

            self.strands.remove(self.selected_strand)
            self.selected_strand = None

            self.strand_deleted.emit(strand_name)
            self.strand_selected.emit("")

    def _get_point_screen_distance(self, point_3d, screen_x, screen_y):
        """Get screen-space distance from a 3D point to screen coordinates"""
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

        result = float('inf')
        try:
            screen_pos = gluProject(point_3d[0], point_3d[1], point_3d[2],
                                   modelview, projection, viewport)
            dx = screen_pos[0] - screen_x
            dy = (viewport[3] - screen_pos[1]) - screen_y
            result = math.sqrt(dx * dx + dy * dy)
        except:
            pass

        # Restore matrices
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        return result

    # ==================== Public Methods ====================

    def set_mode(self, mode: str):
        """Set the current interaction mode"""
        print(f"Mode changed to: {mode}")
        self.current_mode = mode
        self.mode_changed.emit(mode)

        # Cancel any ongoing operation
        self.creating_strand = False
        self.new_strand_start = None

        # Reset move state
        self.moving_strand = None
        self.moving_control_point = None
        self.move_start_pos = None
        self.hovered_control_point = None

        # Reset attach state
        self.attaching = False
        self.attach_new_strand = None
        self.attach_parent_strand = None
        self.attach_side = None
        self.hovered_attach_point = None

        self.update()

    def reset_camera(self):
        """Reset camera to default position"""
        self.camera_distance = 10.0
        self.camera_azimuth = 45.0
        self.camera_elevation = 30.0
        self.camera_target = np.array([0.0, 0.0, 0.0])
        self.update()

    def toggle_grid_axes(self):
        """Toggle visibility of grid and axes"""
        # Toggle both together
        new_state = not (self.show_grid and self.show_axes)
        self.show_grid = new_state
        self.show_axes = new_state
        self.update()
        return new_state

    def set_grid_axes_visible(self, visible: bool):
        """Set visibility of grid and axes"""
        self.show_grid = visible
        self.show_axes = visible
        self.update()

    def set_rigid_points_visible(self, visible: bool):
        """Set visibility of rigid points (start/end spheres on strands)"""
        self.show_rigid_points = visible
        self.update()

    def set_straight_segment_mode(self, enabled: bool):
        """
        Toggle straight segment mode.

        When enabled:
        - All strands become straight lines (control points hidden)
        - Moving strands keeps them straight
        - Original control points are saved for restoration

        When disabled:
        - Strands return to their previous curve state
        - Custom control points are restored
        - Default control points are recalculated
        """
        if enabled == self.straight_segment_mode:
            return  # No change

        if enabled:
            # Entering straight mode - save CPs and straighten all strands
            self.saved_control_points.clear()
            for strand in self.strands:
                # Save current CP state
                self.saved_control_points[id(strand)] = strand.save_control_points()
                # Make strand straight
                strand.make_straight()
        else:
            # Leaving straight mode - restore CPs
            for strand in self.strands:
                saved = self.saved_control_points.get(id(strand))
                strand.restore_control_points(saved)
            self.saved_control_points.clear()

        self.straight_segment_mode = enabled
        self.update()

    def make_all_strands_straight(self):
        """
        Force all strands to be straight.
        Called after operations that might affect strand geometry when in straight mode.
        """
        if self.straight_segment_mode:
            for strand in self.strands:
                strand.make_straight()

    def select_strand_by_name(self, name: str):
        """Select a strand by its name"""
        for strand in self.strands:
            if strand.name == name:
                self.selected_strand = strand
                self.update()
                return

        self.selected_strand = None
        self.update()

    def set_strand_visibility(self, name: str, visible: bool):
        """Set visibility of a strand"""
        for strand in self.strands:
            if strand.name == name:
                strand.visible = visible
                self.update()
                return

    def set_strand_color(self, name: str, color: tuple):
        """Set color of a strand"""
        for strand in self.strands:
            if strand.name == name:
                strand.color = color
                self.update()
                return

    def update_color_for_set(self, set_number: int, color: tuple):
        """
        Update color for all strands in a specific set.

        Args:
            set_number: The set number (e.g., 1 for strands 1_1, 1_2, etc.)
            color: RGB tuple (0-1 range)
        """
        set_prefix = f"{set_number}_"

        for strand in self.strands:
            if strand.name.startswith(set_prefix):
                strand.color = color

        self.update()

    def deselect_all(self):
        """Deselect all strands"""
        self.selected_strand = None
        self.hovered_strand = None
        self.update()

    # ==================== Save/Load Methods ====================

    def get_project_data(self):
        """
        Get all project data as a dictionary for saving.

        Returns:
            dict: Project data including all strands
        """
        from attached_strand import AttachedStrand

        # Separate strands into base strands and attached strands
        # Base strands must be saved first (parents before children)
        base_strands = []
        attached_strands = []

        for strand in self.strands:
            if isinstance(strand, AttachedStrand):
                attached_strands.append(strand)
            else:
                base_strands.append(strand)

        # Sort attached strands by dependency order (parents before children)
        attached_strands = self._sort_attached_strands(attached_strands)

        # Build strands list
        strands_data = []

        # Add base strands first
        for strand in base_strands:
            data = strand.to_dict()
            data['type'] = 'strand'
            strands_data.append(data)

        # Add attached strands in dependency order
        for strand in attached_strands:
            data = strand.to_dict()
            # type is already set by AttachedStrand.to_dict()
            strands_data.append(data)

        return {
            'version': '1.0',
            'project_name': 'OpenStrandStudio Project',
            'camera': {
                'distance': self.camera_distance,
                'azimuth': self.camera_azimuth,
                'elevation': self.camera_elevation,
                'target': self.camera_target.tolist()
            },
            'strands': strands_data
        }

    def _sort_attached_strands(self, attached_strands):
        """
        Sort attached strands so parents come before children.

        This ensures proper reconstruction during load.
        """
        sorted_list = []
        remaining = attached_strands.copy()

        # Keep processing until all are sorted
        max_iterations = len(remaining) * 2  # Safety limit
        iterations = 0

        while remaining and iterations < max_iterations:
            iterations += 1
            for strand in remaining[:]:
                # Check if parent is already in sorted list or is a base strand
                parent = strand.parent_strand
                parent_is_sorted = (
                    parent not in [s for s in attached_strands] or
                    parent in sorted_list
                )

                if parent_is_sorted:
                    sorted_list.append(strand)
                    remaining.remove(strand)

        # Add any remaining (shouldn't happen with valid data)
        sorted_list.extend(remaining)

        return sorted_list

    def load_project_data(self, data):
        """
        Load project data from a dictionary.

        Args:
            data: dict with project data
        """
        from strand import Strand
        from attached_strand import AttachedStrand

        # Clear existing strands
        self.strands.clear()
        self.selected_strand = None
        self.hovered_strand = None

        # Load camera settings
        if 'camera' in data:
            cam = data['camera']
            self.camera_distance = cam.get('distance', 10.0)
            self.camera_azimuth = cam.get('azimuth', 45.0)
            self.camera_elevation = cam.get('elevation', 30.0)
            if 'target' in cam:
                self.camera_target = np.array(cam['target'])

        # Build lookup table as we load strands
        strand_lookup = {}

        # Load strands
        for strand_data in data.get('strands', []):
            strand_type = strand_data.get('type', 'strand')

            if strand_type == 'strand':
                # Load base strand
                strand = Strand.from_dict(strand_data)
                self.strands.append(strand)
                strand_lookup[strand.name] = strand

            elif strand_type == 'attached':
                # Load attached strand
                try:
                    strand = AttachedStrand.from_dict(strand_data, strand_lookup)
                    self.strands.append(strand)
                    strand_lookup[strand.name] = strand
                except ValueError as e:
                    print(f"Warning: Could not load attached strand: {e}")

        self.update()
        print(f"Loaded {len(self.strands)} strands")

    def clear_project(self):
        """Clear all strands and reset the canvas"""
        self.strands.clear()
        self.selected_strand = None
        self.hovered_strand = None
        self.reset_camera()
        self.update()
