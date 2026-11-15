import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless

from pathlib import Path
from voxdose_reports.analyze_plots import render_summary_figure
from voxdose_core.dosi import DOSI

def test_render_summary_png(tmp_path):
    # minimal synthetic inputs consistent with your plotting code
    Fs = 16000
    t_audio = np.arange(0, 1.0, 1.0/Fs)
    x = 0.05 * np.sin(2 * np.pi * 220.0 * t_audio)

    # 20 Hz analysis grid
    step = 0.05
    T = np.arange(0.0, 1.0, step)
    dB = np.linspace(60.0, 80.0, T.size)
    F0 = np.full_like(T, 220.0)
    CPPS = np.linspace(5.0, 12.0, T.size)

    # moving means (any simple vectors with same length)
    F0_mean = np.copy(F0)
    CPPS_mean = np.copy(CPPS)

    # doses from actual DOSI call to keep consistency
    A = np.column_stack([T, dB, F0])
    dose = DOSI(A, gender_mode='male')

    dist_cm = 30
    distance_cal = 0.30
    is_calibrated = False
    base = str(tmp_path / "summary")

    render_summary_figure(
        time_vector=t_audio, x=x,
        windowTime=T, dB=dB,
        F0=F0, F0_mean_t=F0_mean,
        CPPS=CPPS, CPPS_mean_t=CPPS_mean,
        dist_cm=dist_cm,
        distance_cal=distance_cal,
        is_calibrated=is_calibrated,
        dose=dose,
        base=base
    )

    out = Path(f"{base}_Summary_{dist_cm}cm.png")
    assert out.exists()
    assert out.stat().st_size > 0
