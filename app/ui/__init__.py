# ThetaDataTerminalManager UI package

import os
import sys


def set_window_icon(window):
    """Set the window icon for any tkinter window (root or Toplevel)"""
    try:
        # Try to find the icon file
        icon_paths = [
            # For development (source)
            "app/resources/icon.ico",
            # For PyInstaller bundle
            (
                os.path.join(sys._MEIPASS, "app", "resources", "icon.ico")
                if hasattr(sys, "_MEIPASS")
                else None
            ),
            # Alternative paths
            "app/resources/icon_32x32.ico",
            "icon.ico",
        ]

        for icon_path in icon_paths:
            if icon_path and os.path.exists(icon_path):
                window.iconbitmap(icon_path)
                return True

        return False
    except Exception as e:
        print(f"Error setting window icon: {e}")
        return False
