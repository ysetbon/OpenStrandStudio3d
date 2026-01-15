"""
OpenStrandStudio 3D - Attach Mode
Handles all attach mode functionality for the canvas
"""

import numpy as np
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *


class AttachModeMixin:
    """
    Mixin class providing attach mode functionality.

    This class should be inherited by StrandDrawingCanvas along with other mixins.
    It provides methods for:
    - Drawing attachment point spheres
    - Checking if endpoints are free for attachment
    - Hover detection for attachment points
    - Creating and managing attached strands
    """

    def _draw_attachment_points(self):
        """
        Draw attachment point spheres at free ends of all strands.

        A point is "free" (attachable) if:
        - For AttachedStrands: Only the END point can be attached to, and only if end_attached is False
          (The start is always connected to the parent strand)
        - For regular Strands: Both START and END can be attached to, unless they already have
          an attached strand at that side (check attached_strands list and attachment_side)
        """
        # DEBUG: Print attachment state for all strands
        print("=== ATTACHMENT STATE DEBUG ===")
        for strand in self.strands:
            attached_info = [(s.name, s.attachment_side) for s in strand.attached_strands]
            start_free = self._is_endpoint_free(strand, 0)
            end_free = self._is_endpoint_free(strand, 1)
            print(f"{strand.name}: attached_strands={attached_info}, start_free={start_free}, end_free={end_free}")
        print("==============================")

        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        for strand in self.strands:
            if not strand.visible:
                continue

            # Determine which endpoints are free for attachment
            start_is_free = self._is_endpoint_free(strand, 0)  # 0 = start
            end_is_free = self._is_endpoint_free(strand, 1)    # 1 = end

            # Draw start point sphere if free
            if start_is_free:
                is_start_hovered = (self.hovered_attach_point == (strand, 0))
                if is_start_hovered:
                    color = (1.0, 1.0, 0.0, 0.8)  # Yellow when hovered
                else:
                    color = (0.0, 1.0, 0.5, 0.5)  # Green semi-transparent

                self._draw_attachment_sphere(strand.start, color)

            # Draw end point sphere if free
            if end_is_free:
                is_end_hovered = (self.hovered_attach_point == (strand, 1))
                if is_end_hovered:
                    color = (1.0, 1.0, 0.0, 0.8)  # Yellow when hovered
                else:
                    color = (1.0, 0.3, 0.3, 0.5)  # Red semi-transparent

                self._draw_attachment_sphere(strand.end, color)

        # Draw preview of new strand being attached
        if self.attaching and self.attach_new_strand:
            self.attach_new_strand.draw(is_selected=True, is_hovered=False)

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def _is_endpoint_free(self, strand, side):
        """
        Check if an endpoint is free for attachment.

        Args:
            strand: The strand to check
            side: 0 for start, 1 for end

        Returns:
            True if the endpoint is free (can have a strand attached), False otherwise
        """
        from attached_strand import AttachedStrand

        # For AttachedStrands:
        # - Start (side=0) is NEVER free - it's always connected to parent
        # - End (side=1) is free only if it has no child attached to its end
        if isinstance(strand, AttachedStrand):
            if side == 0:
                return False  # Start is always connected to parent
            else:
                return strand.is_end_attachable()

        # For regular Strands:
        # Check if any attached strand is connected at this side
        # attachment_side=0 means attached to parent's START
        # attachment_side=1 means attached to parent's END
        for attached in strand.attached_strands:
            if hasattr(attached, 'attachment_side'):
                if attached.attachment_side == side:
                    return False  # Already has something attached here

        return True  # No attachment at this side, it's free

    def _draw_attachment_sphere(self, position, color):
        """Draw a semi-transparent sphere at attachment point"""
        glPushMatrix()
        glTranslatef(*position)
        glColor4f(*color)

        quadric = gluNewQuadric()
        gluQuadricDrawStyle(quadric, GLU_FILL)
        gluSphere(quadric, self.attach_sphere_radius, 16, 16)
        gluDeleteQuadric(quadric)

        # Draw wireframe for better visibility
        glColor4f(color[0] * 0.5, color[1] * 0.5, color[2] * 0.5, 1.0)
        quadric = gluNewQuadric()
        gluQuadricDrawStyle(quadric, GLU_LINE)
        gluSphere(quadric, self.attach_sphere_radius * 1.02, 12, 12)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _update_attach_point_hover(self, screen_x, screen_y):
        """Update which attachment point is being hovered (only free endpoints)"""
        hover_threshold = 30  # pixels

        closest_point = None
        closest_dist = float('inf')

        for strand in self.strands:
            if not strand.visible:
                continue

            # Check start point if it's free
            if self._is_endpoint_free(strand, 0):
                dist = self._get_point_screen_distance(strand.start, screen_x, screen_y)
                if dist < hover_threshold and dist < closest_dist:
                    closest_dist = dist
                    closest_point = (strand, 0)

            # Check end point if it's free
            if self._is_endpoint_free(strand, 1):
                dist = self._get_point_screen_distance(strand.end, screen_x, screen_y)
                if dist < hover_threshold and dist < closest_dist:
                    closest_dist = dist
                    closest_point = (strand, 1)

        self.hovered_attach_point = closest_point

        # Update cursor
        if self.hovered_attach_point:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _start_attach(self, screen_x, screen_y):
        """Start attaching a new strand to an attachment point"""
        from attached_strand import AttachedStrand

        # Must be hovering over an attachment point
        if not self.hovered_attach_point:
            print("Click on an attachment point (colored sphere) to attach a new strand")
            return

        parent_strand, side = self.hovered_attach_point

        # Verify the endpoint is still free (hover state might be stale)
        if not self._is_endpoint_free(parent_strand, side):
            print(f"Endpoint {parent_strand.name} side {side} is no longer free")
            self.hovered_attach_point = None
            return

        # Get attachment point position
        if side == 0:
            attach_pos = parent_strand.start.copy()
        else:
            attach_pos = parent_strand.end.copy()

        # Generate name for new attached strand
        strand_name = self._get_next_attached_strand_name(parent_strand)

        # Create the attached strand
        self.attach_new_strand = AttachedStrand(
            parent_strand=parent_strand,
            attachment_side=side,
            name=strand_name
        )

        # Override control points to make it a straight line initially
        # (AttachedStrand.__init__ applies C1 alignment which curves it)
        strand = self.attach_new_strand
        direction = strand.end - strand.start
        strand.control_point1 = strand.start + direction * 0.33
        strand.control_point2 = strand.start + direction * 0.67

        self.attaching = True
        self.attach_parent_strand = parent_strand
        self.attach_side = side

        print(f"Attaching new strand '{strand_name}' to {parent_strand.name} (side {side})")

    def _update_attach(self, screen_x, screen_y, shift_held=False):
        """Update the attached strand's end position while dragging"""
        if not self.attach_new_strand:
            return

        strand = self.attach_new_strand
        current_point = strand.end.copy()

        if shift_held:
            # Shift held: move on vertical plane
            new_pos = self._screen_to_vertical_plane(screen_x, screen_y, current_point)
            if new_pos:
                # Only change Y, keep X and Z
                new_end = current_point.copy()
                new_end[1] = new_pos[1]
                strand.end = np.array(new_end)
        else:
            # Normal: move on XZ plane at current Y
            new_pos = self._screen_to_ground(screen_x, screen_y, ground_y=current_point[1])
            if new_pos:
                strand.end = np.array(new_pos)

        # Keep control points linear (straight line) during drag
        # CP1 at 1/3, CP2 at 2/3 along the strand
        direction = strand.end - strand.start
        strand.control_point1 = strand.start + direction * 0.33
        strand.control_point2 = strand.start + direction * 0.67

    def _finish_attach(self, screen_x, screen_y):
        """Finalize the attachment"""
        if not self.attach_new_strand:
            self.attaching = False
            return

        strand = self.attach_new_strand

        # Check minimum length
        length = strand.get_length()
        if length < strand.min_length:
            print(f"Strand too short ({length:.2f}), cancelled")
            # Remove from parent's attached strands list
            if strand in self.attach_parent_strand.attached_strands:
                self.attach_parent_strand.attached_strands.remove(strand)
        else:
            # In straight mode, keep strand straight (skip C1 alignment)
            # Otherwise, apply C1 continuity alignment for seamless connection
            if self.straight_segment_mode:
                # Make sure strand is straight
                strand.make_straight()
            else:
                # Apply C1 continuity alignment for seamless connection
                # This aligns CP1 with parent's tangent at the connection point
                if hasattr(strand, '_align_cp1_with_parent'):
                    strand._align_cp1_with_parent()

            # Add to strands list
            self.strands.append(strand)
            self.selected_strand = strand

            print(f"Created attached strand '{strand.name}' (length: {length:.2f})")

            # Emit signal
            self.strand_created.emit(strand.name)
            self.strand_selected.emit(strand.name)

        # Reset attach state
        self.attaching = False
        self.attach_new_strand = None
        self.attach_parent_strand = None
        self.attach_side = None

    def _get_next_attached_strand_name(self, parent_strand):
        """Generate name for new attached strand based on parent"""
        # Parse parent name to get set number
        parts = parent_strand.name.split('_')
        if len(parts) >= 1:
            try:
                set_num = int(parts[0])
            except ValueError:
                set_num = 1
        else:
            set_num = 1

        # Find next available strand number in this set
        max_strand_num = 0
        for strand in self.strands:
            strand_parts = strand.name.split('_')
            if len(strand_parts) >= 2:
                try:
                    strand_set = int(strand_parts[0])
                    strand_num = int(strand_parts[1])
                    if strand_set == set_num:
                        max_strand_num = max(max_strand_num, strand_num)
                except ValueError:
                    pass

        return f"{set_num}_{max_strand_num + 1}"
