import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless

from voxdose_reports.plots_spl_dba import render_spl_dba_plot

def test_plot_writes_png(tmp_path):
    # Build fake inputs consistent with your plotting code
    Fs = 16000
    t = np.arange(0, 1.0, 1.0 / Fs)
    window_time = np.linspace(0.05, 0.95, 12)
    dBA = np.linspace(60.0, 80.0, window_time.size)

    out = tmp_path / "SPL_dBA_plot.png"
    render_spl_dba_plot(window_time, dBA, t, out_png=str(out))
    assert out.exists()
    assert out.stat().st_size > 0
