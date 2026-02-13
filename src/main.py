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
    app.setApplicationVersion("1.0.0")

    # Set application icon.
    # Windows: color PNG for the custom title bar rendering.
    # macOS: gray icon to match the Dock/taskbar (no custom title bar on mac).
    icon_base_dir = os.path.dirname(os.path.abspath(__file__))
    if sys.platform == "darwin":
        icon_candidates = [
            "openstrandstudio3d_icon_gray.icns",
            "openstrandstudio3d_icon.icns",
            "openstrandstudio3d_icon.png",
        ]
    else:
        icon_candidates = [
            "openstrandstudio3d_icon.png",
            "openstrandstudio3d_icon_gray.ico",
            "openstrandstudio3d_icon.ico",
        ]
    for icon_name in icon_candidates:
        icon_path = os.path.join(icon_base_dir, icon_name)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break

    # Create and show main window
    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
