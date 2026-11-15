import numpy as np
from voxdose_core.spl_fast import SPL_fast

def _tone(Fs=16000, dur_s=1.2, freq=220.0, amp=0.1):
    t = np.arange(int(Fs * dur_s)) / Fs
    x = amp * np.sin(2 * np.pi * freq * t)
    return x, Fs

def test_shapes_and_types():
    x, Fs = _tone()
    mean_, std_ = SPL_fast(x, Fs)
    assert isinstance(mean_, float)
    assert isinstance(std_, float)

def test_duration_effect_on_frames_not_crashing():
    x, Fs = _tone(dur_s=2.0)
    m1, s1 = SPL_fast(x, Fs)
    x2, _ = _tone(dur_s=0.6)
    m2, s2 = SPL_fast(x2, Fs)
    # Not asserting equality; just ensuring both runs succeed and produce numbers.
    assert all(np.isfinite([m1, s1, m2, s2]))

def test_level_increases_with_amplitude():
    x1, Fs = _tone(amp=0.10)
    x2, _  = _tone(amp=0.20)
    m1, s1 = SPL_fast(x1, Fs)
    m2, s2 = SPL_fast(x2, Fs)
    assert m2 > m1
