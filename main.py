#!/usr/bin/env python3
"""Compresso — Professional AI-Powered Image Compression.

Entry point for the application.
"""
from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so absolute imports work
# whether we run `python main.py` or `python -m compresso.main`.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main() -> None:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Compresso")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Compresso")

    # Apply dark theme
    from themes.dark_theme import DarkTheme
    DarkTheme.apply(app)

    # Show main window
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()