"""
OpenStrandStudio 3D - Main Entry Point
A 3D strand/braid design application using OpenGL
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QSurfaceFormat, QIcon
from main_window import MainWindow


def main():
    # Disable automatic high-DPI scaling to prevent mouse coordinate mismatch
    # with OpenGL viewport (same approach as OpenStrand v106)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Request a higher-quality OpenGL surface (anti-aliasing, depth/stencil).
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(8)
    fmt.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setApplicationName("OpenStrandStudio 3D")
    app.setApplicationVersion("0.1.0")

    # Set application icon (works for window icon, taskbar, etc.)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "box_stitch_3d.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create and show main window
    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
