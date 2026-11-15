# tests/test_splash.py
import os
import sys
import time
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from voxdose_gui.splash import show_splash_screen

def _get_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app

def test_splash_runs_and_returns_quickly():
    app = _get_app()
    # duration=0 ensures immediate exit of the loop
    t0 = time.time()
    show_splash_screen(app, duration=0)
    dt = time.time() - t0
    # Should complete essentially immediately
    assert dt < 0.5
