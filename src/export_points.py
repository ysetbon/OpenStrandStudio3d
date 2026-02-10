"""
OpenStrandStudio 3D - Export Points Mixin
Handles exporting strand positions as a JSON point list.
"""

import json
from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QVBoxLayout, QLabel
)


class ExportPointsMixin:
    """Mixin providing _export_points() for MainWindow."""

    def _export_points(self):
        """Export strand positions as a JSON point list, reversing the unit conversion."""
        import numpy as np

        strands = self.canvas.strands
        if not strands or not self._original_segment_lengths:
            QMessageBox.warning(self, "Export Points",
                                "No loaded points to export. Use Load Points first.")
            return

        # Ask for export scale factor via a custom dialog with explanation.
        dlg = QDialog(self)
        dlg.setWindowTitle("Export Scale")
        dlg.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
                min-width: 350px;
            }
            QLabel {
                color: #E8E8E8;
                font-size: 18px;
            }
            QPushButton {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 8px 22px;
                color: #E8E8E8;
                font-size: 15px;
                font-weight: 500;
                min-width: 98px;
            }
            QPushButton:hover {
                background-color: #454548;
                border-color: #5A5A5D;
            }
            QPushButton:pressed {
                background-color: #2A2A2D;
            }
            QDoubleSpinBox {
                background-color: #353538;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 6px 11px;
                color: #E8E8E8;
                font-size: 17px;
            }
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {
                background-color: #454548;
                border: 1px solid #3E3E42;
                width: 22px;
            }
            QDoubleSpinBox::up-button:hover,
            QDoubleSpinBox::down-button:hover {
                background-color: #5A5A5D;
            }
        """)
        layout = QVBoxLayout(dlg)

        info = QLabel(
            "Scale factor for exported point spacing:\n\n"
            "  1.0  =  original units (identical to loaded file)\n"
            "  2.0  =  2x larger spacing between points\n"
            "  0.5  =  half the original spacing\n\n"
            "This only affects the exported file.\n"
            "Re-importing always uses the Load strand length."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        spin = QDoubleSpinBox()
        spin.setRange(0.1, 100.0)
        spin.setDecimals(1)
        spin.setValue(1.0)
        spin.setSingleStep(0.1)
        layout.addWidget(spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return
        scale = spin.value()

        # Reconstruct points using strand directions and original segment
        # lengths, multiplied by the scale factor.
        running = strands[0].start.copy()
        points = [running.tolist()]
        for i, strand in enumerate(strands):
            direction = strand.end - strand.start
            seg_len = np.linalg.norm(direction)
            if seg_len < 1e-10:
                continue
            direction_normalized = direction / seg_len
            orig_len = self._original_segment_lengths[i]
            running = running + direction_normalized * orig_len * scale
            points.append(running.tolist())

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Points", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w") as f:
                json.dump(points, f, indent=2)
            self.statusbar.showMessage(
                f"Exported {len(points)} points to {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(
                self, "Export Points Error",
                f"Failed to export points:\n{str(e)}"
            )
