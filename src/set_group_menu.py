"""
OpenStrandStudio 3D - Set Group Menu
Context menu builder for set-level operations (e.g., duplicate a set).
"""

from PyQt5.QtWidgets import QMenu


def build_set_group_menu(parent, on_duplicate):
    """Build the context menu for a set group header."""
    menu = QMenu(parent)
    menu.setStyleSheet("""
        QMenu {
            background-color: #2a2a2a;
            color: white;
            border: 1px solid #555555;
            padding: 4px;
        }
        QMenu::separator {
            height: 1px;
            background-color: #555555;
            margin: 4px 8px;
        }
    """)

    duplicate_action = menu.addAction("Duplicate Set")
    duplicate_action.triggered.connect(on_duplicate)

    return menu
