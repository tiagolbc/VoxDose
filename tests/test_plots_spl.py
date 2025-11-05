import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend

from voxdose_reports.plots_spl import render_spl_plot

def test_plot_writes_png(tmp_path):
    # Fake full timeline t and per-frame window_time/dB
    Fs = 16000
    t = np.arange(0, 1.0, 1.0 / Fs)
    window_time = np.linspace(0.05, 0.95, 12)
    dB = np.linspace(60.0, 80.0, window_time.size)

    out = tmp_path / "SPL_plot.png"
    render_spl_plot(window_time, dB, t, out_png=str(out))
    assert out.exists()
    assert out.stat().st_size > 0
