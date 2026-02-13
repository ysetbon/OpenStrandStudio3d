"""
OpenStrandStudio 3D - Undo/Redo Manager
Manages undo/redo state history for the application
"""

import copy
from PyQt5.QtCore import QObject, pyqtSignal


class UndoRedoManager(QObject):
    """
    Manages undo/redo functionality using in-memory state snapshots.

    Design:
    - Uses two stacks: undo_stack (past states) and redo_stack (future states)
    - Each state is a complete snapshot of the canvas (strands + selection)
    - Deduplication prevents saving identical consecutive states
    - Maximum history limit prevents unbounded memory growth
    """

    # Signals for UI updates
    state_changed = pyqtSignal()  # Emitted when undo/redo availability changes
    undo_performed = pyqtSignal()  # Emitted after successful undo
    redo_performed = pyqtSignal()  # Emitted after successful redo

    def __init__(self, canvas, max_history=50):
        """
        Initialize the undo/redo manager.

        Args:
            canvas: The StrandDrawingCanvas instance
            max_history: Maximum number of states to keep in history
        """
        super().__init__()

        self.canvas = canvas
        self.max_history = max_history

        # State stacks
        self.undo_stack = []  # List of past states
        self.redo_stack = []  # List of future states (cleared on new action)

        # Last saved state for deduplication
        self._last_state = None

        # Flag to prevent recursive saves during undo/redo
        self._is_restoring = False

    def save_state(self, description=""):
        """
        Save the current canvas state to the undo stack.

        Args:
            description: Optional description for debugging

        Returns:
            bool: True if state was saved, False if skipped (duplicate)
        """
        if self._is_restoring:
            return False

        # Capture current state
        current_state = self._capture_state()

        # Check for duplicate (skip if identical to last state)
        if self._is_duplicate(current_state):
            return False

        # Clear redo stack on new action (standard undo/redo behavior)
        self.redo_stack.clear()

        # Add to undo stack
        self.undo_stack.append(current_state)

        # Enforce max history limit
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)  # Remove oldest state

        # Update last state for deduplication
        self._last_state = current_state

        self.state_changed.emit()
        return True

    def undo(self):
        """
        Undo the last action by restoring the previous state.

        Returns:
            bool: True if undo was performed, False if no history
        """
        if not self.can_undo():
            return False

        self._is_restoring = True

        try:
            # Save current state to redo stack before restoring
            current_state = self._capture_state()
            self.redo_stack.append(current_state)

            # Pop and restore previous state
            previous_state = self.undo_stack.pop()
            self._restore_state(previous_state)

            # Update last state
            self._last_state = previous_state

            self.state_changed.emit()
            self.undo_performed.emit()
            return True

        finally:
            self._is_restoring = False

    def redo(self):
        """
        Redo a previously undone action.

        Returns:
            bool: True if redo was performed, False if no redo history
        """
        if not self.can_redo():
            return False

        self._is_restoring = True

        try:
            # Save current state to undo stack before restoring
            current_state = self._capture_state()
            self.undo_stack.append(current_state)

            # Pop and restore next state
            next_state = self.redo_stack.pop()
            self._restore_state(next_state)

            # Update last state
            self._last_state = next_state

            self.state_changed.emit()
            self.redo_performed.emit()
            return True

        finally:
            self._is_restoring = False

    def can_undo(self):
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self):
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def clear_history(self):
        """Clear all undo/redo history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._last_state = None
        self.state_changed.emit()

    def get_history_data(self):
        """Return undo/redo stacks as a JSON-serializable dict."""
        return {
            'undo_stack': list(self.undo_stack),
            'redo_stack': list(self.redo_stack),
        }

    def load_history_data(self, data):
        """Restore undo/redo stacks from a dict (e.g. loaded from file)."""
        self.undo_stack = list(data.get('undo_stack', []))
        self.redo_stack = list(data.get('redo_stack', []))
        self._last_state = self.undo_stack[-1] if self.undo_stack else None
        self.state_changed.emit()

    def _capture_state(self):
        """
        Capture the current canvas state.

        Returns:
            dict: Complete state snapshot
        """
        from attached_strand import AttachedStrand

        strands_data = []

        # Separate base strands and attached strands
        base_strands = []
        attached_strands = []

        for strand in self.canvas.strands:
            if isinstance(strand, AttachedStrand):
                attached_strands.append(strand)
            else:
                base_strands.append(strand)

        # Sort attached strands by dependency
        attached_strands = self._sort_attached_strands(attached_strands)

        # Serialize base strands first
        for strand in base_strands:
            data = strand.to_dict()
            data['type'] = 'strand'
            strands_data.append(data)

        # Serialize attached strands
        for strand in attached_strands:
            data = strand.to_dict()
            strands_data.append(data)

        # Capture selection state
        selected_name = None
        if self.canvas.selected_strand:
            selected_name = self.canvas.selected_strand.name

        return {
            'strands': strands_data,
            'selected_strand': selected_name,
        }

    def _restore_state(self, state):
        """
        Restore canvas to a saved state.

        Args:
            state: State dict from _capture_state()
        """
        from strand import Strand
        from attached_strand import AttachedStrand

        # Clear current strands
        self.canvas.strands.clear()
        self.canvas.selected_strand = None
        self.canvas.hovered_strand = None

        # Build lookup table as we load
        strand_lookup = {}

        # Restore strands
        for strand_data in state.get('strands', []):
            strand_type = strand_data.get('type', 'strand')

            if strand_type == 'strand':
                strand = Strand.from_dict(strand_data)
                self.canvas.strands.append(strand)
                strand_lookup[strand.name] = strand

            elif strand_type == 'attached':
                try:
                    strand = AttachedStrand.from_dict(strand_data, strand_lookup)
                    self.canvas.strands.append(strand)
                    strand_lookup[strand.name] = strand
                except ValueError as e:
                    print(f"Warning: Could not restore attached strand: {e}")

        # Restore selection
        selected_name = state.get('selected_strand')
        if selected_name:
            for strand in self.canvas.strands:
                if strand.name == selected_name:
                    self.canvas.selected_strand = strand
                    break

        # Invalidate rendering caches
        if hasattr(self.canvas, '_clear_chain_root_cache'):
            self.canvas._clear_chain_root_cache()

        # Invalidate move mode caches
        if hasattr(self.canvas, '_invalidate_cp_screen_cache'):
            self.canvas._invalidate_cp_screen_cache()

        # Sync layer state manager
        if hasattr(self.canvas, 'layer_state_manager') and self.canvas.layer_state_manager:
            self.canvas.layer_state_manager.save_current_state()

        # Update canvas display
        self.canvas.update()

    def _sort_attached_strands(self, attached_strands):
        """Sort attached strands so parents come before children."""
        sorted_list = []
        remaining = attached_strands.copy()

        max_iterations = len(remaining) * 2
        iterations = 0

        while remaining and iterations < max_iterations:
            iterations += 1
            for strand in remaining[:]:
                parent = strand.parent_strand
                parent_is_sorted = (
                    parent not in attached_strands or
                    parent in sorted_list
                )

                if parent_is_sorted:
                    sorted_list.append(strand)
                    remaining.remove(strand)

        sorted_list.extend(remaining)
        return sorted_list

    def _is_duplicate(self, new_state):
        """
        Check if new state is identical to the last saved state.

        Args:
            new_state: State dict to compare

        Returns:
            bool: True if duplicate, False otherwise
        """
        if self._last_state is None:
            return False

        # Compare strand count
        if len(new_state['strands']) != len(self._last_state['strands']):
            return False

        # Compare each strand
        for new_strand, old_strand in zip(new_state['strands'], self._last_state['strands']):
            if not self._strands_equal(new_strand, old_strand):
                return False

        # Compare selection
        if new_state.get('selected_strand') != self._last_state.get('selected_strand'):
            return False

        return True

    def _strands_equal(self, strand1, strand2, tolerance=0.001):
        """
        Compare two strand dicts for equality.

        Args:
            strand1, strand2: Strand dictionaries to compare
            tolerance: Floating point comparison tolerance

        Returns:
            bool: True if strands are equal
        """
        # Compare type
        if strand1.get('type') != strand2.get('type'):
            return False

        # Compare name
        if strand1.get('name') != strand2.get('name'):
            return False

        # Compare positions with tolerance
        position_keys = ['start', 'end', 'control_point1', 'control_point2']
        for key in position_keys:
            if key in strand1 and key in strand2:
                pos1 = strand1[key]
                pos2 = strand2[key]
                for v1, v2 in zip(pos1, pos2):
                    if abs(v1 - v2) > tolerance:
                        return False

        # Compare other properties
        if strand1.get('color') != strand2.get('color'):
            return False

        if strand1.get('visible') != strand2.get('visible'):
            return False

        if abs(strand1.get('width', 0.15) - strand2.get('width', 0.15)) > tolerance:
            return False

        # Compare attached strand properties
        if strand1.get('parent_name') != strand2.get('parent_name'):
            return False

        if strand1.get('attachment_side') != strand2.get('attachment_side'):
            return False

        return True
