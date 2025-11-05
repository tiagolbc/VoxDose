import numpy as np
from voxdose_core.sp_cpps import _nearest_idx, _windows

def test_nearest_idx_basic():
    x = np.array([0.0, 0.5, 1.0, 2.0])
    assert _nearest_idx(x, -1.0) == 0
    assert _nearest_idx(x, 0.0) == 0
    assert _nearest_idx(x, 0.49) in (0,1)
    assert _nearest_idx(x, 0.51) in (1,2)
    assert _nearest_idx(x, 10.0) == len(x) - 1

def test_windows_generation():
    out = _windows(duration_s=1.0, win_s=0.4, hop_s=0.3)
    # Each item is (start, end, center); should cover from 0 with positive hops
    assert len(out) >= 1
    for i, (s, e, c) in enumerate(out):
        assert 0.0 <= s < e <= 1.0 + 1e-12
        assert abs(c - 0.5 * (s + e)) < 1e-12
        if i > 0:
            # Increasing start times by hop_s (approx)
            assert s > out[i-1][0]
