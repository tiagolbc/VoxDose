# sp_cpps.py — Connected-speech CPPS every 5 seconds (voiced-only + pause-removed),
# aligned to the original 50 ms analysis timeline.
from __future__ import annotations
import numpy as np
import parselmouth

_EPS = 1e-15

def _nearest_idx(x: np.ndarray, v: float) -> int:
    if x.size == 0:
        return 0
    if v <= x[0]:
        return 0
    if v >= x[-1]:
        return len(x) - 1
    k = np.searchsorted(x, v)
    return k-1 if abs(v - x[k-1]) <= abs(x[k] - v) else k

def _voiced_only_sound(x: np.ndarray, fs: float, f0min: float, f0max: float) -> parselmouth.Sound:
    """Build a voiced-only sound by marking 10 ms neighborhoods around pitch samples with f0>0."""
    snd = parselmouth.Sound(x, sampling_frequency=fs)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=f0min, pitch_ceiling=f0max)
    f0 = pitch.selected_array['frequency']
    tt = pitch.xs()
    samples = snd.values[0]
    sr = int(round(fs))
    voiced_mask = np.zeros_like(samples, dtype=bool)
    half = int(0.005 * sr)
    for t, hz in zip(tt, f0):
        if hz > 0 and np.isfinite(hz):
            i = int(t * sr)
            lo, hi = max(0, i - half), min(samples.size, i + half)
            voiced_mask[lo:hi] = True
    out = samples * voiced_mask.astype(samples.dtype)
    return parselmouth.Sound(out, sampling_frequency=fs)

def _trim_silences(snd: parselmouth.Sound, silence_threshold_db: float = -35.0) -> parselmouth.Sound:
    """Use Praat's 'Trim silences' similarly to your CepstralVox settings."""
    trimmed = parselmouth.praat.call(
        snd, "Trim silences",
        0.08,  # minimum silent duration (s)
        0,     # only at start and end (0=no)
        100,   # trim threshold (dB)
        0,     # channel (0 = all)
        float(silence_threshold_db),  # silence threshold (dB)
        0.10,  # min sounding interval
        0.05,  # min silent interval
        "no",  # mid points
        "trimmed"
    )
    if isinstance(trimmed, list):
        trimmed = trimmed[0]
    return trimmed

def _cpps_single_praat(snd: parselmouth.Sound,
                       f0min: float, f0max: float,
                       pcg_pitch_floor: float = 60.0,
                       pcg_time_step: float = 0.002,
                       pcg_max_freq: float = 5000.0,
                       pcg_preemph_from: float = 60.0,
                       subtract_trend: str = "no",
                       time_avg_win_s: float = 0.010,
                       quef_avg_win_s: float = 0.001,
                       trend_type: str = "Straight") -> float:
    """Compute CPPS via Praat on a (possibly short) connected-speech segment."""
    try:
        pcg = parselmouth.praat.call(
            snd, "To PowerCepstrogram...",
            float(pcg_pitch_floor), float(pcg_time_step),
            float(pcg_max_freq), float(pcg_preemph_from)
        )
        cpps = parselmouth.praat.call(
            pcg, "Get CPPS...",
            str(subtract_trend), float(time_avg_win_s), float(quef_avg_win_s),
            float(f0min), float(f0max),
            0.05, "Parabolic", 0.001, 0, str(trend_type), "Robust"
        )
        return float(cpps) if cpps is not None else 0.0
    except Exception:
        return 0.0

def _windows(duration_s: float, win_s: float, hop_s: float):
    """Yield (start, end, center) tuples covering [0, duration_s)."""
    if win_s <= 0 or hop_s <= 0:
        return []
    t = 0.0
    out = []
    while t < duration_s:
        start = t
        end = min(t + win_s, duration_s)
        center = 0.5 * (start + end)
        out.append((start, end, center))
        t += hop_s
    return out

def spCPPS(x: np.ndarray, fs: float,
           frame_len_s: float = 0.050,
           hop_s: float = 0.050,
           f0min: float = 75.0,
           f0max: float = 500.0,
           fft_size=None,                 # API compatibility
           freq_smooth_hz: float = 200.0, # unused
           quef_smooth_s: float = 0.010,  # kept for signature parity
           silence_threshold_dbfs: float = -35.0,
           use_vad: bool = True,
           # NEW: CPPS windowing across the file
           cpps_win_s: float = 5.0,
           cpps_hop_s: float = 5.0):
    """
    Compute a CPPS *track* aligned to the original 50 ms timeline, where
    CPPS is first evaluated on **5-second connected-speech windows** (voiced-only + pause-removed).
    For each 50 ms frame, we assign the CPPS of the window that contains that time
    (voiced frames → CPPS value, unvoiced/pauses → 0).

    Returns
    -------
    CPPS_track : (K,) ndarray of float (per 50 ms frame)
    T_frames   : (K,) ndarray of float (frame centers, seconds)
    """
    x = np.asarray(x, float).ravel()
    N = x.size
    if N == 0 or frame_len_s <= 0 or hop_s <= 0:
        return np.zeros(0), np.zeros(0)

    # Build frame centers for the original analysis timeline
    L = int(round(frame_len_s * fs))
    H = int(round(hop_s * fs))
    centers = []
    pos = 0
    while pos + L <= N:
        centers.append((pos + L // 2) / fs)
        pos += H
    centers = np.asarray(centers, float)
    K = centers.size
    if K == 0:
        return np.zeros(0), np.zeros(0)

    duration_s = N / fs

    # For voiced/unvoiced marking at the 50 ms frame centers
    snd_all = parselmouth.Sound(x, sampling_frequency=fs)
    pitch_all = snd_all.to_pitch(time_step=hop_s, pitch_floor=f0min, pitch_ceiling=f0max)
    pt = pitch_all.xs()
    pf = pitch_all.selected_array['frequency']
    voiced_flags = np.zeros(K, dtype=bool)
    for i, t in enumerate(centers):
        j = _nearest_idx(pt, t)
        f0_here = pf[j] if 0 <= j < pf.size else np.nan
        voiced_flags[i] = bool(f0_here > 0 and np.isfinite(f0_here))

    # Prepare CPPS per 5 s window over the *original* signal
    win_list = _windows(duration_s, cpps_win_s, cpps_hop_s)
    cpps_times = np.array([c for (_, _, c) in win_list], float)
    cpps_vals  = np.zeros(len(win_list), float)

    for w, (start, end, _) in enumerate(win_list):
        i0 = int(round(start * fs))
        i1 = int(round(end * fs))
        if i1 <= i0:
            cpps_vals[w] = 0.0
            continue

        seg = x[i0:i1]

        # Connected-speech preprocessing for *this* window:
        # (a) VAD → voiced-only, (b) trim pauses, then CPPS on the result.
        if use_vad:
            snd_voiced = _voiced_only_sound(seg, fs, f0min, f0max)
        else:
            snd_voiced = parselmouth.Sound(seg, sampling_frequency=fs)

        snd_proc = _trim_silences(snd_voiced, silence_threshold_db=silence_threshold_dbfs)

        # If almost empty after trimming, CPPS is 0
        if snd_proc.get_total_duration() < 0.2:  # guard for too-short content
            cpps_vals[w] = 0.0
        else:
            cpps_vals[w] = _cpps_single_praat(
                snd_proc,
                f0min=f0min, f0max=f0max,
                pcg_pitch_floor=60.0,
                pcg_time_step=0.002,
                pcg_max_freq=5000.0,
                pcg_preemph_from=max(50.0, f0min),
                subtract_trend="no",
                time_avg_win_s=0.010,
                quef_avg_win_s=0.001,
                trend_type="Straight"
            )

    # Map window CPPS back to the 50 ms timeline:
    # for each frame center, find the window that contains it (or the nearest window center)
    track = np.zeros(K, float)
    for i, t in enumerate(centers):
        # Find window index: prefer containment; fallback to nearest center
        idx = None
        # Quick containment check: compute which window this t belongs to
        # (works when hop == win, still fine when overlapping)
        for w, (start, end, _) in enumerate(win_list):
            if start <= t < end or (w == len(win_list)-1 and abs(t - end) < 1e-9):
                idx = w
                break
        if idx is None:
            # Not in any (possible at edges), use nearest window center
            idx = _nearest_idx(cpps_times, t)

        track[i] = cpps_vals[idx] if voiced_flags[i] else 0.0

    return track, centers
