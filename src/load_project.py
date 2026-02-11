"""
OpenStrandStudio 3D - Load Project Mixin
Handles loading a project from a JSON file.
"""

import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox


class LoadProjectMixin:
    """Mixin providing _load_project() for MainWindow."""

    def _load_project(self):
        """Load a project from a JSON file"""
        # Ask for confirmation if there are strands
        if self.canvas.strands:
            reply = QMessageBox.question(
                self,
                "Load Project",
                "This will replace the current project. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project",
            "",
            "OpenStrandStudio 3D Files (*.oss3d);;JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Read project data
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Clear layer panel
            self.layer_panel.clear()

            # Load into canvas
            self.canvas.load_project_data(project_data)

            # Clear undo history (fresh start with loaded project)
            self.undo_redo_manager.clear_history()

            # Update layer panel with loaded strands
            for strand in self.canvas.strands:
                self.layer_panel.add_strand(strand.name, color=strand.color)

            self.layer_panel.update_layer_button_states(self.canvas)

            # Update layer state manager with loaded strand relationships
            if self.layer_state_manager:
                self.layer_state_manager.save_current_state()

            self.current_project_file = file_path
            self.setWindowTitle(f"OpenStrandStudio 3D - {file_path.split('/')[-1].split(chr(92))[-1]}")
            self.statusbar.showMessage(f"Loaded: {file_path}", 3000)

        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Invalid JSON file:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load project:\n{str(e)}"
            )
