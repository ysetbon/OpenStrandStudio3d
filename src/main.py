"""
OpenStrandStudio 3D - Main Entry Point
A 3D strand/braid design application using OpenGL
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from main_window import MainWindow


def main():
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("OpenStrandStudio 3D")
    app.setApplicationVersion("0.1.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
