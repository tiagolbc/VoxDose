# tests/test_stima_livello.py
import numpy as np
import math
import pytest

from voxdose_core.stima_livello import stimaLivello

def _tone(Fs=16000, dur_s=1.0, freq=200.0, amp=0.1, phase=0.0):
    t = np.arange(int(Fs * dur_s)) / Fs
    x = amp * np.sin(2 * np.pi * freq * t + phase)
    return x, Fs

def test_returns_shapes_and_types():
    x, Fs = _tone()
    X_db, dB = stimaLivello(x, Fs, C=50.0)
    assert isinstance(dB, float)
    assert isinstance(X_db, np.ndarray)
    assert X_db.ndim == 1
    assert np.isfinite(X_db).all()  # we guard zeros before log
    # dB can be -inf only for strict silence; for a tone it should be finite
    assert np.isfinite(dB)

def test_scaling_law_20log_amplitude():
    # Doubling amplitude should add ~6.0206 dB
    x1, Fs = _tone(amp=0.10)
    x2, _  = _tone(amp=0.20)
    _, dB1 = stimaLivello(x1, Fs, C=50.0)
    _, dB2 = stimaLivello(x2, Fs, C=50.0)
    diff = dB2 - dB1
    assert abs(diff - 20.0 * math.log10(2.0)) < 0.2  # tolerance

def test_calibration_offset_is_linear():
    x, Fs = _tone(amp=0.12)
    _, dB_a = stimaLivello(x, Fs, C=40.0)
    _, dB_b = stimaLivello(x, Fs, C=55.0)
    assert abs((dB_b - dB_a) - (55.0 - 40.0)) < 1e-6

def test_frequency_independence_same_amp():
    # With no A-weighting, equal-amplitude tones at different freqs
    # should produce very similar dB (allow small numerical differences).
    x1, Fs = _tone(freq=200.0, amp=0.1)
    x2, _  = _tone(freq=800.0, amp=0.1)
    _, dB1 = stimaLivello(x1, Fs, C=50.0)
    _, dB2 = stimaLivello(x2, Fs, C=50.0)
    assert abs(dB1 - dB2) < 0.5  # generous tolerance for FFT windowing effects

def test_duration_invariance_same_amp_freq():
    # Changing duration should not change the reported level meaningfully
    x1, Fs = _tone(dur_s=0.5, freq=250.0, amp=0.08)
    x2, _  = _tone(dur_s=1.5, freq=250.0, amp=0.08)
    _, dB1 = stimaLivello(x1, Fs, C=50.0)
    _, dB2 = stimaLivello(x2, Fs, C=50.0)
    assert abs(dB1 - dB2) < 0.5

def test_silence_returns_minus_inf_level():
    Fs = 16000
    x = np.zeros(int(Fs * 1.0), dtype=float)
    X_db, dB = stimaLivello(x, Fs, C=50.0)
    # Spectrum is finite due to epsilon guard:
    assert np.isfinite(X_db).all()
    # Overall level is -inf for silence:
    assert dB == float("-inf")
