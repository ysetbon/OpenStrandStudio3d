"""
OpenStrandStudio 3D - Attached Strand Class
A strand that is attached to another strand's endpoint
"""

import numpy as np
from strand import Strand


class AttachedStrand(Strand):
    """
    A strand attached to another strand's endpoint.

    The start point of an AttachedStrand is always connected to its parent strand.
    Only the end point can be freely moved or have other strands attached to it.
    """

    def __init__(self, parent_strand, attachment_side, end_position=None, name=""):
        """
        Initialize an attached strand.

        Args:
            parent_strand: The Strand this is attached to
            attachment_side: 0 = attach to parent's start, 1 = attach to parent's end
            end_position: Initial end position (if None, extends from parent)
            name: Strand identifier
        """
        # Get attachment point from parent
        if attachment_side == 0:
            attach_point = parent_strand.start.copy()
        else:
            attach_point = parent_strand.end.copy()

        # Calculate initial end position if not provided
        if end_position is None:
            # Extend outward from parent by default length
            direction = self._get_default_direction(parent_strand, attachment_side)
            end_position = attach_point + direction * 2.0  # Default length of 2 units

        # Initialize base Strand class
        super().__init__(
            start=attach_point,
            end=end_position,
            name=name,
            color=parent_strand.color,  # Inherit color from parent
            width=parent_strand.width
        )

        # Attachment properties
        self.parent_strand = parent_strand
        self.attachment_side = attachment_side  # 0=start, 1=end

        # Attachment state
        self.start_attached = True  # Start is always attached to parent
        self.end_attached = False   # End is free for further attachments

        # Minimum length constraint
        self.min_length = 0.5

        # Add self to parent's attached strands list
        if self not in parent_strand.attached_strands:
            parent_strand.attached_strands.append(self)

    def _get_default_direction(self, parent_strand, attachment_side):
        """Get a default direction for the new strand based on parent's orientation"""
        # Get parent's direction
        parent_dir = parent_strand.end - parent_strand.start
        parent_len = np.linalg.norm(parent_dir)

        if parent_len > 1e-6:
            parent_dir /= parent_len
        else:
            parent_dir = np.array([1.0, 0.0, 0.0])

        # Default direction: continue in parent's direction if attaching to end,
        # opposite direction if attaching to start
        if attachment_side == 1:
            return parent_dir
        else:
            return -parent_dir

    def update_start_from_parent(self):
        """Update start position to match parent's attachment point"""
        if self.attachment_side == 0:
            new_start = self.parent_strand.start.copy()
        else:
            new_start = self.parent_strand.end.copy()

        # Calculate delta and move the whole strand to maintain shape
        delta = new_start - self.start
        self.start = new_start
        self.end = self.end + delta
        self.control_point1 = self.control_point1 + delta
        self.control_point2 = self.control_point2 + delta

    def set_end(self, position):
        """
        Set the end position with minimum length constraint.

        Args:
            position: New end position as numpy array
        """
        position = np.array(position, dtype=float)

        # Calculate direction and length
        direction = position - self.start
        length = np.linalg.norm(direction)

        # Enforce minimum length
        if length < self.min_length:
            if length > 1e-6:
                direction /= length
            else:
                # Default direction if too close
                direction = self._get_default_direction(self.parent_strand, self.attachment_side)
            position = self.start + direction * self.min_length

        # Update end and control point 2
        delta = position - self.end
        self.end = position
        self.control_point2 = self.control_point2 + delta

    def get_angle(self):
        """Get the angle of the strand in 3D (returns direction vector)"""
        direction = self.end - self.start
        length = np.linalg.norm(direction)
        if length > 1e-6:
            return direction / length
        return np.array([1.0, 0.0, 0.0])

    def get_length(self):
        """Get the length of the strand"""
        return np.linalg.norm(self.end - self.start)

    def is_start_attachable(self):
        """Check if start point can have strands attached (always False for AttachedStrand)"""
        return False  # Start is already attached to parent

    def is_end_attachable(self):
        """Check if end point can have strands attached"""
        return not self.end_attached

    def to_dict(self):
        """Convert to dictionary for saving"""
        data = super().to_dict()
        data['type'] = 'attached'
        data['parent_name'] = self.parent_strand.name
        data['attachment_side'] = self.attachment_side
        data['start_attached'] = self.start_attached
        data['end_attached'] = self.end_attached
        return data

    def __repr__(self):
        return f"AttachedStrand(name='{self.name}', parent='{self.parent_strand.name}', side={self.attachment_side})"
