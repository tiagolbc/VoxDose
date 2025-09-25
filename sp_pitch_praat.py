# sp_pitch_praat.py
import numpy as np
import parselmouth  # pip install praat-parselmouth

def spPitchPraat(x, fs, time_step_s=0.05, f0min=75.0, f0max=500.0):
    """
    Praat pitch tracker via Parselmouth (RAPT/AC-like).
    Returns F0 (Hz) and time stamps (s) spaced at ~time_step_s.

    x  : 1-D numpy array (mono)
    fs : sampling rate
    """
    if x.ndim != 1:
        x = np.asarray(x).flatten()

    snd = parselmouth.Sound(x, sampling_frequency=fs)
    pitch = snd.to_pitch(time_step_s, f0min, f0max)  # time step in seconds

    # times and values
    t = pitch.xs()  # numpy array of times in seconds
    f0 = pitch.selected_array['frequency']  # 0 where unvoiced

    # Make sure outputs are 1-D float
    return np.asarray(f0, dtype=float), np.asarray(t, dtype=float)
