# sp_pitch_track_praat.py
import numpy as np
import parselmouth  # pip install praat-parselmouth
import matplotlib.pyplot as plt

def spPitchTrackPraat(x, fs, frame_length=30, frame_overlap=None,
                      f0min=75.0, f0max=500.0, show=False):
    """
    Pitch tracking using Praat (Parselmouth).

    Parameters
    ----------
    x : 1D array
        Mono audio signal.
    fs : int
        Sampling rate (Hz).
    frame_length : float (ms)
        Analysis window length (kept for API compatibility; Praat uses its own internal window,
        but we'll honor the hop/time step derived from frame_length and frame_overlap).
    frame_overlap : float (ms or None)
        Frame overlap. If None, defaults to frame_length/2 (i.e., hop = frame_length/2).
    f0min, f0max : float
        Pitch search bounds (Hz).
    show : bool
        If True, plots the waveform and the pitch track.

    Returns
    -------
    F0 : 1D array
        Fundamental frequency (Hz), 0 for unvoiced.
    T  : 1D array
        Time stamps (s) for each F0 value.
    C  : 2D array
        Placeholder to match the old API; returns an empty (0,0) array.
    """
    x = np.asarray(x).flatten()
    N = len(x)

    if frame_overlap is None:
        frame_overlap = frame_length / 2.0

    # Hop (time step) in seconds derived from the legacy frame params
    hop_ms = max(frame_length - frame_overlap, 1e-6)
    time_step_s = hop_ms / 1000.0

    snd = parselmouth.Sound(x, sampling_frequency=fs)
    # Praat: to_pitch(time_step, pitch_floor, pitch_ceiling)
    pitch = snd.to_pitch(time_step_s, f0min, f0max)

    T = pitch.xs()  # times (s)
    F0 = pitch.selected_array["frequency"]  # Hz, 0.0 when unvoiced

    F0 = np.asarray(F0, dtype=float)
    T  = np.asarray(T, dtype=float)
    C  = np.zeros((0, 0), dtype=float)  # no cepstrogram in Praat tracker

    return F0, T, C
