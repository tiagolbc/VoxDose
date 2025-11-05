import numpy as np
import pytest

# Import the logic-only copy
from voxdose_core.sp_pitch_track_praat import spPitchTrackPraat

def _tone(Fs=16000, dur_s=1.0, freq=200.0, amp=0.1):
    t = np.arange(int(Fs * dur_s)) / Fs
    x = amp * np.sin(2 * np.pi * freq * t)
    return x, Fs, freq

@pytest.mark.parametrize("f0min,f0max", [(150.0, 250.0)])
def test_shapes_and_monotonic_time(f0min, f0max):
    x, Fs, _ = _tone()
    F0, T, C = spPitchTrackPraat(
        x, Fs,
        frame_length=30,
        frame_overlap=None,
        f0min=f0min,
        f0max=f0max,
        show=False
    )
    assert F0.ndim == 1 and T.ndim == 1
    assert F0.shape == T.shape
    assert C.ndim == 2
    # strictly increasing time stamps
    if len(T) > 1:
        assert np.all(np.diff(T) > 0)

def test_estimated_f0_within_bounds_and_close_to_tone():
    x, Fs, fref = _tone(freq=220.0)
    F0, T, _ = spPitchTrackPraat(
        x, Fs, frame_length=30, frame_overlap=None,
        f0min=100.0, f0max=300.0, show=False
    )
    voiced = F0[F0 > 0]
    # All voiced values must be inside [f0min, f0max]
    assert np.all((voiced >= 100.0) & (voiced <= 300.0))
    # Median voiced F0 should be close to the reference tone
    if voiced.size:
        med = float(np.median(voiced))
        assert abs(med - fref) < 20.0  # generous tolerance
