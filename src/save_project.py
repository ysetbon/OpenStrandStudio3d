"""
OpenStrandStudio 3D - Save Project Mixin
Handles saving the project to a JSON file.
"""

import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox


class SaveProjectMixin:
    """Mixin providing _save_project() for MainWindow."""

    def _save_project(self):
        """Save the project to a JSON file"""
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            self.current_project_file or "project.oss3d",
            "OpenStrandStudio 3D Files (*.oss3d);;JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Get project data from canvas
            project_data = self.canvas.get_project_data()

            # Write to file with nice formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2)

            self.current_project_file = file_path
            self.setWindowTitle(f"OpenStrandStudio 3D - {file_path.split('/')[-1].split(chr(92))[-1]}")
            self.statusbar.showMessage(f"Saved: {file_path}", 3000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save project:\n{str(e)}"
            )
