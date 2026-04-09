#!/usr/bin/env python3
"""
FileOrganizer - Automated cross-platform file organization tool.
Entry point for the application.
"""

import sys
import os

# Ensure the app directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.gui import FileOrganizerApp


def main():
    app = FileOrganizerApp()
    app.run()


if __name__ == "__main__":
    main()
