import numpy as np
import pytest

parselmouth = pytest.importorskip("parselmouth")

from voxdose_core.sp_cpps import spCPPS

def _tone(Fs=16000, dur_s=1.0, freq=200.0, amp=0.1):
    t = np.arange(int(Fs * dur_s)) / Fs
    x = amp * np.sin(2 * np.pi * freq * t)
    return x, Fs

def test_empty_input_returns_empty():
    track, centers = spCPPS(np.array([], dtype=float), fs=16000)
    assert track.size == 0
    assert centers.size == 0

@pytest.mark.parametrize("dur_s", [0.6, 1.2])
def test_shapes_and_monotonic_time(dur_s):
    x, Fs = _tone(dur_s=dur_s)
    track, centers = spCPPS(
        x, Fs,
        frame_len_s=0.050,
        hop_s=0.050,
        f0min=100.0,
        f0max=300.0,
        silence_threshold_dbfs=-40.0,
        use_vad=True,
        cpps_win_s=0.5,   # keep small for speed
        cpps_hop_s=0.5
    )
    assert track.ndim == 1 and centers.ndim == 1
    assert track.shape == centers.shape
    if centers.size > 1:
        assert np.all(np.diff(centers) > 0)
    assert np.isfinite(track).all()

def test_parameter_variants_no_crash():
    x, Fs = _tone(dur_s=1.0, freq=220.0)
    # Variant 1: VAD off
    tr1, c1 = spCPPS(x, Fs, use_vad=False, cpps_win_s=0.4, cpps_hop_s=0.4, f0min=80.0, f0max=350.0)
    # Variant 2: different hop and tighter f0 bounds
    tr2, c2 = spCPPS(x, Fs, hop_s=0.025, f0min=150.0, f0max=300.0, cpps_win_s=0.4, cpps_hop_s=0.2)
    for tr, c in [(tr1, c1), (tr2, c2)]:
        assert tr.ndim == 1 and c.ndim == 1 and tr.shape == c.shape
        assert np.isfinite(tr).all()
