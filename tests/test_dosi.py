import numpy as np
import pytest

from voxdose_core.dosi import DOSI

def _make_data(Fs=20, dur_s=2.0, spl_val=75.0, f0_val=200.0, voiced=True):
    """
    Build an (n, 3) array with columns [t, SPL, F0].
    Default time step is ~0.05 s (Fs = 20 Hz).
    """
    n = int(Fs * dur_s)
    t = np.arange(n) / Fs
    SPL = np.full(n, spl_val, dtype=float)
    F0 = np.full(n, f0_val if voiced else 0.0, dtype=float)
    return np.column_stack([t, SPL, F0])

def test_basic_shapes_and_types():
    data = _make_data()
    dose = DOSI(data, gender_mode='male')
    assert isinstance(dose, np.ndarray)
    assert dose.shape == (13,)
    assert np.isfinite(dose).all()

def test_invalid_input_raises():
    with pytest.raises(ValueError):
        DOSI(np.zeros((10, 2)))  # fewer than 3 columns
    with pytest.raises(ValueError):
        DOSI(_make_data(), gender_mode='unknown')  # invalid mode

def test_gender_mode_int_backward_compat():
    data = _make_data()
    dose_male_str = DOSI(data, gender_mode='male')
    dose_male_int = DOSI(data, gender_mode=1)
    dose_fem_str  = DOSI(data, gender_mode='female')
    dose_fem_int  = DOSI(data, gender_mode=0)

    # Must match exactly (string vs int)
    assert np.allclose(dose_male_str, dose_male_int, atol=1e-12)
    assert np.allclose(dose_fem_str,  dose_fem_int,  atol=1e-12)

def test_other_is_between_male_and_female_for_key_doses():
    data = _make_data(spl_val=80.0, f0_val=220.0)
    male = DOSI(data, gender_mode='male')
    fem  = DOSI(data, gender_mode='female')
    oth  = DOSI(data, gender_mode='other')

    # Indices: [Dt, VLI, Dd, De, Dr, Dt%, Dd_norm, De_norm, Dr_norm, SPL_mean, F0_mean, SPL_sd, F0_sd]
    for idx in [2, 3, 4, 6, 7, 8]:  # Dd, De, Dr and normalized versions
        lo, hi = (male[idx], fem[idx]) if male[idx] <= fem[idx] else (fem[idx], male[idx])
        assert lo - 1e-9 <= oth[idx] <= hi + 1e-9

def test_time_step_inference_matches_dt_and_vli_scales():
    # ~0.05 s step → Dt ≈ n * 0.05, VLI ≈ sum(f0*dt)/1000
    Fs = 20  # 0.05 s
    data = _make_data(Fs=Fs, dur_s=1.0, spl_val=78.0, f0_val=200.0)
    dose = DOSI(data, gender_mode='male')
    n = data.shape[0]
    dt = 1.0 / Fs

    # Dt = sum(time_step over voiced frames)
    expected_Dt = n * dt
    assert abs(dose[0] - expected_Dt) < 1e-6  # Dt

    # VLI ≈ (n * 200 * dt)/1000
    expected_VLI = (n * 200.0 * dt) / 1000.0
    assert abs(dose[1] - expected_VLI) < 1e-3  # generous tolerance

def test_no_voiced_frames_returns_zeros():
    data = _make_data(voiced=False)
    dose = DOSI(data, gender_mode='female')
    assert np.allclose(dose, 0.0)

def test_increasing_amplitude_increases_energy_related_doses():
    # Higher SPL should increase Dr (radiation) and typically De/Dd
    data1 = _make_data(spl_val=70.0, f0_val=180.0)
    data2 = _make_data(spl_val=85.0, f0_val=180.0)
    d1 = DOSI(data1, gender_mode='male')
    d2 = DOSI(data2, gender_mode='male')

    # Dr (index 4) should clearly increase
    assert d2[4] > d1[4]
    # At least one of De or Dd should increase
    assert (d2[2] > d1[2]) or (d2[3] > d1[3])

def test_irregular_time_grid_uses_median_positive_diff():
    # Build t with small random jitters to force median-based dt
    rng = np.random.default_rng(0)
    Fs_nom = 20.0
    dt_nom = 1.0 / Fs_nom
    n = 200
    t = np.cumsum(dt_nom + rng.normal(0, 0.002, n))  # around 0.05 s
    t -= t[0]
    SPL = np.full(n, 76.0)
    F0  = np.full(n, 210.0)
    data = np.column_stack([t, SPL, F0])

    d = DOSI(data, gender_mode='other')
    # Just ensure it doesn’t break and Dt, VLI are finite
    assert np.isfinite(d[0]) and np.isfinite(d[1])
