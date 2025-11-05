import numpy as np
import soundfile as sf
import tempfile
from pathlib import Path

# core function (logic-only copy)
from voxdose_core.analyze_wav_spl_f0 import analyze_wav_spl_f0

def _sine(Fs=16000, dur_s=1.0, freq=220.0, amp=0.1):
    t = np.arange(int(Fs * dur_s)) / Fs
    x = amp * np.sin(2 * np.pi * freq * t)
    return x, Fs

def test_runs_and_writes_excels(tmp_path):
    # synth audio file
    x, Fs = _sine(dur_s=1.2, freq=220.0, amp=0.05)
    wav_path = tmp_path / "test_voxdose.wav"
    sf.write(wav_path, x, Fs)

    # run UNCALIBRATED (no calibration file/level)
    A, dose = analyze_wav_spl_f0(
        gender_mode='male',
        fname=str(wav_path),
        calibration_file=None,
        calibration_level_dBA=None,
        freq_low=75,
        freq_high=400,
        distance_cal=0.30,
        target_distance_m=0.30,
        f0_mean_win_s=1.0,
        cpps_mean_win_s=1.0
    )

    # returns
    assert isinstance(A, np.ndarray) and A.ndim == 2 and A.shape[1] == 3
    assert isinstance(dose, np.ndarray) and dose.shape == (13,)

    # Excel outputs next to audio file
    base = wav_path.with_suffix("")
    xlsx_main = Path(str(base) + ".xlsx")
    xlsx_dose = Path(str(base) + "_VocalDoses.xlsx")
    assert xlsx_main.exists()
    assert xlsx_dose.exists()
