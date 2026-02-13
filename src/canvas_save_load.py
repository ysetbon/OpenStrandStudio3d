"""
OpenStrandStudio 3D - Canvas Save/Load Mixin
Handles project data serialization and deserialization for the canvas.
"""

import numpy as np


class CanvasSaveLoadMixin:
    """Mixin providing save/load/clear methods for StrandDrawingCanvas."""

    def get_project_data(self, undo_redo_manager=None):
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

        # Include connection data from layer state manager
        connections_data = {}
        if self.layer_state_manager:
            connections_data = self.layer_state_manager.getConnections()

        result = {
            'version': '1.1',
            'project_name': 'OpenStrandStudio Project',
            'camera': {
                'distance': self.camera_distance,
                'azimuth': self.camera_azimuth,
                'elevation': self.camera_elevation,
                'target': self.camera_target.tolist()
            },
            'strands': strands_data,
            'connections': connections_data
        }

        if undo_redo_manager is not None:
            result['undo_redo'] = undo_redo_manager.get_history_data()

        return result

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

        # Update layer state manager with loaded strand relationships
        if self.layer_state_manager:
            self.layer_state_manager.save_current_state()

        # Invalidate rendering caches
        if hasattr(self, '_clear_chain_root_cache'):
            self._clear_chain_root_cache()

        # Invalidate move mode caches
        if hasattr(self, '_invalidate_cp_screen_cache'):
            self._invalidate_cp_screen_cache()

        self.update()
        print(f"Loaded {len(self.strands)} strands")

    def clear_project(self):
        """Clear all strands and reset the canvas"""
        self.strands.clear()
        self.selected_strand = None
        self.hovered_strand = None
        self.reset_camera()

        # Invalidate rendering caches
        if hasattr(self, '_clear_chain_root_cache'):
            self._clear_chain_root_cache()

        self.update()
