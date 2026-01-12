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

        # Align control point for C1 continuity with parent
        self._align_cp1_with_parent()

    def _align_cp1_with_parent(self):
        """
        Align control_point1 so that the tangent at our start matches
        the parent's tangent at the connection point.
        This creates C1 continuity (smooth connection).
        """
        # Get parent's tangent at the connection point
        if self.attachment_side == 1:
            # Attached to parent's end
            # Parent's tangent at end = (parent.end - parent.control_point2)
            # We want our tangent at start to be the same direction
            parent_tangent_dir = self.parent_strand.end - self.parent_strand.control_point2
        else:
            # Attached to parent's start
            # Parent's tangent at start = (parent.control_point1 - parent.start)
            # We want our tangent at start to be opposite (continuing outward)
            parent_tangent_dir = self.parent_strand.start - self.parent_strand.control_point1

        # Normalize the direction
        tangent_len = np.linalg.norm(parent_tangent_dir)
        if tangent_len > 1e-6:
            parent_tangent_dir = parent_tangent_dir / tangent_len

        # Set our CP1 along this direction
        # Use similar distance as parent's CP to connection point
        if self.attachment_side == 1:
            parent_cp_dist = np.linalg.norm(self.parent_strand.end - self.parent_strand.control_point2)
        else:
            parent_cp_dist = np.linalg.norm(self.parent_strand.start - self.parent_strand.control_point1)

        # Use at least 1/3 of our length, or match parent's distance
        our_length = np.linalg.norm(self.end - self.start)
        cp_dist = max(parent_cp_dist, our_length * 0.33)

        self.control_point1 = self.start + parent_tangent_dir * cp_dist

    def sync_cp1_with_parent(self):
        """
        Synchronize our CP1 with parent's control point to maintain C1 continuity.
        Call this when parent's CP2 (or CP1 for start attachment) changes.
        """
        self._align_cp1_with_parent()

    def sync_parent_cp_with_our_cp1(self):
        """
        Synchronize parent's control point with our CP1 to maintain C1 continuity.
        Call this when our CP1 changes.
        """
        # Our tangent at start = (control_point1 - start)
        our_tangent_dir = self.control_point1 - self.start
        tangent_len = np.linalg.norm(our_tangent_dir)
        if tangent_len < 1e-6:
            return

        our_tangent_dir = our_tangent_dir / tangent_len

        if self.attachment_side == 1:
            # Attached to parent's end
            # Parent's CP2 should be on opposite side of connection point
            # Parent tangent at end = (end - CP2), should equal our tangent at start
            # So: CP2 = end - tangent_dir * distance
            parent_cp_dist = np.linalg.norm(self.parent_strand.end - self.parent_strand.control_point2)
            self.parent_strand.control_point2 = self.parent_strand.end - our_tangent_dir * parent_cp_dist
        else:
            # Attached to parent's start
            # Parent's CP1 should be on opposite side
            # Parent tangent at start = (CP1 - start), should equal -our_tangent
            parent_cp_dist = np.linalg.norm(self.parent_strand.start - self.parent_strand.control_point1)
            self.parent_strand.control_point1 = self.parent_strand.start + our_tangent_dir * parent_cp_dist

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

    def _is_chain_root(self):
        """AttachedStrand is never a root - it's part of parent's chain"""
        return False

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

    @classmethod
    def from_dict(cls, data, strand_lookup):
        """
        Create an AttachedStrand from dictionary.

        Args:
            data: Dictionary with strand data
            strand_lookup: Dict mapping strand names to Strand objects (for finding parent)

        Returns:
            AttachedStrand instance
        """
        parent_name = data['parent_name']
        parent_strand = strand_lookup.get(parent_name)

        if parent_strand is None:
            raise ValueError(f"Parent strand '{parent_name}' not found")

        # Create attached strand
        attached = cls(
            parent_strand=parent_strand,
            attachment_side=data['attachment_side'],
            end_position=data['end'],
            name=data.get('name', '')
        )

        # Restore control points
        attached.control_point1 = np.array(data['control_point1'])
        attached.control_point2 = np.array(data['control_point2'])

        # Restore visual properties
        attached.color = tuple(data.get('color', (0.9, 0.5, 0.1)))
        attached.width = data.get('width', 0.15)
        attached.height_ratio = data.get('height_ratio', 0.4)
        attached.visible = data.get('visible', True)

        # Restore attachment state
        attached.start_attached = data.get('start_attached', True)
        attached.end_attached = data.get('end_attached', False)

        return attached

    def __repr__(self):
        return f"AttachedStrand(name='{self.name}', parent='{self.parent_strand.name}', side={self.attachment_side})"
