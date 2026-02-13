"""
OpenStrandStudio 3D - User Settings Manager
Handles saving and loading user preferences
"""

import json
import os
import sys
from pathlib import Path


class UserSettings:
    """Manages user settings persistence"""

    # Default settings file location (in user's home directory)
    SETTINGS_FILENAME = ".openstrandstudio3d_settings.json"

    # Default values
    DEFAULTS = {
        # Strand profile defaults
        'default_strand_width': 0.15,
        'default_height_ratio': 0.4,
        'default_cross_section_shape': 'ellipse',
        'default_corner_radius': 0.0,

        # View settings
        'show_grid': True,
        'show_axes': True,

        # Move mode settings
        'link_control_points': False,
        'move_edit_all': False,

        # Toolbar visibility
        'always_show_move_attach_toolbars': False,
    }

    def __init__(self):
        self._settings = self.DEFAULTS.copy()
        self._settings_path = self._get_settings_path()
        self.load()

    def _get_settings_path(self):
        """Get the path to the settings file"""
        # When running as a PyInstaller bundle, always use home directory
        # (the app directory is a temporary extraction path that gets deleted)
        if getattr(sys, 'frozen', False):
            return Path.home() / self.SETTINGS_FILENAME

        # In development, try app directory first, fall back to home
        app_dir = Path(__file__).parent
        app_settings = app_dir / self.SETTINGS_FILENAME

        try:
            test_file = app_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return app_settings
        except (PermissionError, OSError):
            return Path.home() / self.SETTINGS_FILENAME

    def load(self):
        """Load settings from file"""
        if not self._settings_path.exists():
            return

        try:
            with open(self._settings_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            # Merge loaded settings with defaults (to handle new settings)
            for key, value in loaded.items():
                if key in self.DEFAULTS:
                    self._settings[key] = value

            print(f"Settings loaded from {self._settings_path}")

        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load settings: {e}")

    def save(self):
        """Save settings to file"""
        try:
            with open(self._settings_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)

            print(f"Settings saved to {self._settings_path}")

        except IOError as e:
            print(f"Warning: Could not save settings: {e}")

    def get(self, key, default=None):
        """Get a setting value"""
        if default is None:
            default = self.DEFAULTS.get(key)
        return self._settings.get(key, default)

    def set(self, key, value):
        """Set a setting value"""
        self._settings[key] = value

    def set_and_save(self, key, value):
        """Set a setting value and immediately save"""
        self.set(key, value)
        self.save()

    def update(self, settings_dict):
        """Update multiple settings at once"""
        for key, value in settings_dict.items():
            self._settings[key] = value

    def update_and_save(self, settings_dict):
        """Update multiple settings and save"""
        self.update(settings_dict)
        self.save()

    # Convenience properties for strand profile settings
    @property
    def default_strand_width(self):
        return self.get('default_strand_width')

    @default_strand_width.setter
    def default_strand_width(self, value):
        self.set('default_strand_width', value)

    @property
    def default_height_ratio(self):
        return self.get('default_height_ratio')

    @default_height_ratio.setter
    def default_height_ratio(self, value):
        self.set('default_height_ratio', value)

    @property
    def default_cross_section_shape(self):
        return self.get('default_cross_section_shape')

    @default_cross_section_shape.setter
    def default_cross_section_shape(self, value):
        self.set('default_cross_section_shape', value)

    @property
    def default_corner_radius(self):
        return self.get('default_corner_radius')

    @default_corner_radius.setter
    def default_corner_radius(self, value):
        self.set('default_corner_radius', value)


# Global settings instance
_settings_instance = None


def get_settings():
    """Get the global settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = UserSettings()
    return _settings_instance
