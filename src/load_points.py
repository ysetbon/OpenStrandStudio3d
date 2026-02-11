"""
OpenStrandStudio 3D - Load Points Mixin
Handles loading point coordinates from a JSON file and creating strands.
"""

import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog


class LoadPointsMixin:
    """Mixin providing _load_points() for MainWindow."""

    def _load_points(self):
        """Load points from a JSON file and create strands from consecutive points"""
        # Get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Points",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Read points data
            with open(file_path, 'r', encoding='utf-8') as f:
                points = json.load(f)

            # Validate: must be a list of 3D points
            if not isinstance(points, list) or len(points) < 2:
                QMessageBox.warning(
                    self,
                    "Load Points",
                    "JSON must contain a list of at least 2 points."
                )
                return

            # Validate each point is [x, y, z]
            for i, point in enumerate(points):
                if not isinstance(point, list) or len(point) != 3:
                    QMessageBox.warning(
                        self,
                        "Load Points",
                        f"Point {i} is invalid. Each point must be [x, y, z]."
                    )
                    return

            # Import Strand, AttachedStrand and numpy
            from strand import Strand
            from attached_strand import AttachedStrand
            import numpy as np

            # Ask user for strand length
            strand_length, ok = QInputDialog.getDouble(
                self, "Strand Length",
                "Length of each strand:",
                self._last_load_strand_length,
                0.2, 5.0, 1
            )
            if not ok:
                return
            self._last_load_strand_length = strand_length
            self._original_segment_lengths = []
            STRAND_LENGTH = strand_length

            # Get next set number for naming
            set_number = self.canvas._get_next_set_number()

            # Get or assign color for this set
            if set_number not in self.canvas.set_colors:
                palette_idx = (int(set_number) - 1) % len(self.canvas._color_palette)
                self.canvas.set_colors[set_number] = self.canvas._color_palette[palette_idx]

            color = self.canvas.set_colors[set_number]

            # Convert points to numpy arrays
            np_points = [np.array(p, dtype=float) for p in points]

            # Create strands using direction vectors from tiny segments
            # Each strand is STRAND_LENGTH units long in the direction of the original segment
            created_strands = []
            strand_index = 1
            previous_strand = None

            for i in range(len(np_points) - 1):
                # Get direction vector from tiny segment (points[i] → points[i+1])
                direction = np_points[i + 1] - np_points[i]
                length = np.linalg.norm(direction)

                if length < 1e-10:
                    continue  # Skip zero-length segments

                self._original_segment_lengths.append(length)

                # Normalize direction
                direction_normalized = direction / length

                strand_name = f"{set_number}_{strand_index}"

                if previous_strand is None:
                    # First strand: regular Strand starting at first point
                    start = np_points[0].copy()
                    end = start + direction_normalized * STRAND_LENGTH

                    strand = Strand(
                        start=start,
                        end=end,
                        name=strand_name,
                        color=color,
                        width=self.canvas.default_strand_width
                    )
                else:
                    # Subsequent strands: AttachedStrand connected to previous strand's end
                    # Calculate end position based on direction
                    end_position = previous_strand.end + direction_normalized * STRAND_LENGTH

                    strand = AttachedStrand(
                        parent_strand=previous_strand,
                        attachment_side=1,  # Attach to parent's end
                        end_position=end_position,
                        name=strand_name
                    )

                    # Reset control points to default (straight line)
                    # AttachedStrand aligns CP1 for smooth curves, but we want straight
                    strand._init_control_points()

                # Apply default profile settings
                strand.height_ratio = self.canvas.default_height_ratio
                strand.cross_section_shape = self.canvas.default_cross_section_shape
                strand.corner_radius = self.canvas.default_corner_radius

                self.canvas.strands.append(strand)
                created_strands.append(strand)

                previous_strand = strand
                strand_index += 1

            # Update layer panel
            for strand in created_strands:
                self.layer_panel.add_strand(strand.name, color=strand.color)

            self.layer_panel.update_layer_button_states(self.canvas)

            # Select the first created strand
            if created_strands:
                self.canvas.selected_strand = created_strands[0]
                self.canvas.strand_selected.emit(created_strands[0].name)

            # Update layer state manager with new strand relationships
            if self.layer_state_manager:
                self.layer_state_manager.save_current_state()

            self.canvas.update()
            self.statusbar.showMessage(f"Loaded {len(created_strands)} strands from points", 3000)

        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self,
                "Load Points Error",
                f"Invalid JSON file:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Points Error",
                f"Failed to load points:\n{str(e)}"
            )
