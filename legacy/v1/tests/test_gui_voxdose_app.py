import os
import numpy as np
import pytest

# run Qt headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from voxdose_gui.voxdose_app import VoxDoseApp

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app

def test_voxdose_app_constructs_and_plots(qapp):
    win = VoxDoseApp()
    assert win.windowTitle() == "VoxDose Analyzer v1.0.0"

    # Provide tiny synthetic arrays so plot_results doesn't crash
    win.time = np.linspace(0, 1.0, 21)
    win.dB = np.linspace(60, 80, 21)
    win.F0 = np.linspace(200, 220, 21)

    # Should render without raising
    win.plot_results()
