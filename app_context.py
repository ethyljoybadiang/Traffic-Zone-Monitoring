import os
import sys


def get_application_path() -> str:
    """
    Return the base directory for app data/output.

    - When bundled (PyInstaller), use the executable directory.
    - Otherwise, use this source directory.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APPLICATION_PATH = get_application_path()

