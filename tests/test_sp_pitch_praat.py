import numpy as np
import pytest

from voxdose_core.sp_pitch_praat import spPitchPraat

def _tone(Fs=16000, dur_s=1.0, freq=220.0, amp=0.1):
    t = np.arange(int(Fs * dur_s)) / Fs
    x = amp * np.sin(2 * np.pi * freq * t)
    return x, Fs, freq

@pytest.mark.parametrize("time_step_s", [0.005, 0.01, 0.02, 0.05])
def test_shapes_and_time_monotonicity(time_step_s):
    x, Fs, _ = _tone()
    f0, t = spPitchPraat(x, Fs, time_step_s=time_step_s, f0min=100.0, f0max=300.0)
    assert f0.ndim == 1 and t.ndim == 1
    assert f0.shape == t.shape
    if len(t) > 1:
        assert np.all(np.diff(t) > 0)

def test_estimated_f0_close_to_reference_tone():
    x, Fs, fref = _tone(freq=200.0)
    f0, t = spPitchPraat(x, Fs, time_step_s=0.01, f0min=100.0, f0max=300.0)
    voiced = f0[f0 > 0]
    assert voiced.size > 0
    med = float(np.median(voiced))
    assert abs(med - fref) < 20.0  # generous tolerance

def test_non_1d_input_is_flattened():
    # Create a 2D array view that flattens back to 1D inside the function
    x1d, Fs, _ = _tone()
    x2d = x1d.reshape(-1, 1)
    f0a, ta = spPitchPraat(x1d, Fs, time_step_s=0.02)
    f0b, tb = spPitchPraat(x2d, Fs, time_step_s=0.02)
    assert f0a.shape == f0b.shape
    assert ta.shape == tb.shape
    if f0a.size > 0:
        # They should be numerically very close
        assert np.allclose(f0a, f0b, atol=1e-6)
