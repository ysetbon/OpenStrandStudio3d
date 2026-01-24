"""
OpenStrandStudio 3D - Select Mode
Handles selection and hover logic for strands.
"""

import math
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *


class SelectModeMixin:
    """Mixin class providing select mode functionality."""

    def _try_select_strand(self, screen_x, screen_y):
        """Select the strand closest to the cursor."""
        # Scale mouse coordinates by device pixel ratio to match viewport
        dpr = int(self.devicePixelRatioF())
        screen_x = screen_x * dpr
        screen_y = screen_y * dpr
        strand = self._find_strand_at_screen(screen_x, screen_y, threshold_px=20.0 * dpr)
        self.selected_strand = strand

        if strand:
            self.hovered_strand = strand
            self.strand_selected.emit(strand.name)
        else:
            self.hovered_strand = None
            self.strand_selected.emit("")

        self.update()

    def _update_select_hover(self, screen_x, screen_y):
        """Update hover highlight for select mode."""
        # Scale mouse coordinates by device pixel ratio to match viewport
        dpr = int(self.devicePixelRatioF())
        screen_x = screen_x * dpr
        screen_y = screen_y * dpr
        strand = self._find_strand_at_screen(screen_x, screen_y, threshold_px=24.0 * dpr)

        if strand != self.hovered_strand:
            self.hovered_strand = strand
            self.update()

        if self.hovered_strand:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _find_strand_at_screen(self, screen_x, screen_y, threshold_px):
        """Find the closest visible strand to the cursor within threshold."""
        if not self.strands:
            return None

        closest_strand = None
        closest_dist = float('inf')

        projection = self._prepare_selection_projection()
        if projection is None:
            return None

        viewport, modelview, projection_matrix = projection

        try:
            for strand in self.strands:
                if not getattr(strand, "visible", True):
                    continue

                dist = self._get_strand_screen_distance(
                    strand,
                    screen_x,
                    screen_y,
                    viewport,
                    modelview,
                    projection_matrix
                )

                if dist < closest_dist:
                    closest_dist = dist
                    closest_strand = strand
        finally:
            self._restore_selection_projection()

        if closest_dist <= threshold_px:
            return closest_strand
        return None

    def _get_strand_screen_distance(self, strand, screen_x, screen_y,
                                    viewport, modelview, projection_matrix):
        """Compute the closest screen-space distance to a strand."""
        # Sample along the curve for a closer hit test than midpoint only.
        num_segments = min(24, max(8, getattr(strand, "curve_segments", 16) // 2))
        points = strand.get_curve_points(num_segments=num_segments)
        closest = float('inf')

        for point in points:
            try:
                screen_pos = gluProject(
                    point[0], point[1], point[2],
                    modelview, projection_matrix, viewport
                )
            except Exception:
                continue

            dx = screen_pos[0] - screen_x
            dy = (viewport[3] - screen_pos[1]) - screen_y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < closest:
                closest = dist
                if closest <= 0.0:
                    break

        return closest

    def _prepare_selection_projection(self):
        """Setup camera projection for screen-space picking."""
        self.makeCurrent()

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        dpr = int(self.devicePixelRatioF())
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
        projection_matrix = glGetDoublev(GL_PROJECTION_MATRIX)

        return viewport, modelview, projection_matrix

    def _restore_selection_projection(self):
        """Restore matrices after selection projection."""
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
