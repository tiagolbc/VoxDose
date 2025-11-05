import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless for CI

from voxdose_reports.plots_pitch_block import render_pitch_plot

def test_render_pitch_plot_runs_headless():
    Fs = 16000
    t = np.arange(0, 1.0, 1.0/Fs)
    x = 0.1 * np.sin(2 * np.pi * 220.0 * t)
    # Fake tracker output for plotting call
    T = np.linspace(0.0, 1.0, 100)
    F0 = np.full_like(T, 220.0)
    # Should run without error and not require a display
    render_pitch_plot(x, Fs, T, F0)
