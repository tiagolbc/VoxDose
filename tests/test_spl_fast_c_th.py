import numpy as np
from voxdose_core.spl_fast_c_th import SPL_fast_C_TH

def _tone(Fs=16000, dur_s=1.0, freq=220.0, amp=0.1):
    t = np.arange(int(Fs * dur_s)) / Fs
    x = amp * np.sin(2 * np.pi * freq * t)
    return x, Fs

def test_shapes_and_lengths():
    x, Fs = _tone(dur_s=1.2)
    mean_, std_, dB, wtime = SPL_fast_C_TH(x, Fs, C=50.0, duration=0.05)
    assert isinstance(mean_, float)
    assert isinstance(std_, float)
    assert dB.ndim == 1 and wtime.ndim == 1
    assert len(dB) == len(wtime)
    if len(wtime) > 1:
        dt = np.diff(wtime)
        assert np.all(dt > 0)

def test_frame_count_changes_with_duration():
    x, Fs = _tone(dur_s=2.0)
    m1, s1, d1, w1 = SPL_fast_C_TH(x, Fs, C=50.0, duration=0.05)
    m2, s2, d2, w2 = SPL_fast_C_TH(x, Fs, C=50.0, duration=0.10)
    assert len(d1) > len(d2)
    assert len(w1) > len(w2)

def test_levels_are_finite_for_tone():
    x, Fs = _tone(amp=0.2)
    m, s, dB, wtime = SPL_fast_C_TH(x, Fs, C=50.0, duration=0.05)
    if len(dB):
        assert np.isfinite(dB).all()
