# analyze_wav_spl_f0.py
import os
import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import soundfile as sf

from .spl_fast import SPL_fast
from .spl_fast_c_th import SPL_fast_C_TH
from .sp_pitch_track_praat import spPitchTrackPraat
from .dosi import DOSI

# --- CPPS is optional; use ONLY the relative import and DO NOT override the flag later ---
try:
    from .sp_cpps import spCPPS
    _HAS_CPPS = True
except Exception:
    _HAS_CPPS = False


def _read_audio_best_channel(path):
    x, Fs = sf.read(path)
    x = np.asarray(x)
    if x.ndim == 1:
        return x.astype(float), Fs
    rms = np.sqrt(np.mean(x**2, axis=0))
    ch = int(np.argmax(rms))
    return x[:, ch].astype(float), Fs


def _moving_leq_dB(dB_series, win_len_frames):
    if win_len_frames < 1:
        return np.zeros_like(dB_series)
    lin = np.where(dB_series > 0, 10.0**(dB_series/10.0), 0.0)
    k = np.ones(int(win_len_frames), dtype=float) / float(win_len_frames)
    leq_lin = np.convolve(lin, k, mode="same")
    return 10.0 * np.log10(np.maximum(leq_lin, 1e-12))


def _moving_mean_ignore_zeros(series, win_len_frames):
    if win_len_frames < 1:
        return np.zeros_like(series, dtype=float)
    v = np.asarray(series, dtype=float)
    valid = (v > 0) & np.isfinite(v)
    num = np.convolve(np.where(valid, v, 0.0), np.ones(win_len_frames), mode="same")
    den = np.convolve(valid.astype(float), np.ones(win_len_frames), mode="same")
    out = np.divide(num, np.maximum(den, 1e-9))
    out[den < 1] = 0.0
    return out


def analyze_wav_spl_f0(
        gender_mode='male',                  # 'male' | 'female' | 'other'
        fname='handheld_recorder_calibration_file.wav',
        calibration_file=None,               # single calibration file (.wav or .mp3)
        calibration_level_dBA=None,          # SPL from SLM for that file (float)
        freq_low=75,
        freq_high=150,
        distance_cal=0.30,                   # meters used during calibration
        target_distance_m=0.30,              # DEFAULT: report at 30 cm; set 0.50 to report at 50 cm
        f0_mean_win_s=5.0,                   # window for F0 moving mean (s)
        cpps_mean_win_s=5.0                  # window for CPPS moving mean (s)
):
    """
    - Calibrated SPL (dBA), Praat F0 (Hz), and optional CPPS (dB) from an audio file.
    - Provide calibration_file (.wav or .mp3) and calibration_level_dBA (measured with SLM).
    - Analysis frame is 0.05 s (20 Hz).
    - SPL is distance-normalized to target_distance_m via 20*log10(distance_cal/target_distance_m).
    """

    # === Calibration from ONE file ===
    is_calibrated = False
    if calibration_file and (calibration_level_dBA is not None):
        try:
            cal_x, cal_Fs = _read_audio_best_channel(calibration_file)
            # SPL_fast returns (SPL_mean, SPL_std) → unpack the mean!
            SPL_mean_cal, _ = SPL_fast(cal_x, cal_Fs)
            C = 50 + float(calibration_level_dBA) - SPL_mean_cal
            is_calibrated = True
        except Exception as e:
            print(f"⚠️ Calibration failed ({e}). Using uncalibrated C=50.")
            C = 50.0
            is_calibrated = False
    else:
        print("⚠️ No calibration provided. Using uncalibrated C=50.")
        C = 50.0
        is_calibrated = False

    # === Load monitored file ===
    x, Fs = _read_audio_best_channel(fname)
    time_vector = np.arange(0, len(x)) / Fs
    duration = 0.05  # 20 Hz analysis step

    # === Per-frame SPL with calibration ===
    SPL_mean, SPL_std, dB, windowTime = SPL_fast_C_TH(x, Fs, C, duration)

    # === Praat pitch tracking ===
    try:
        F0, t = spPitchTrackPraat(
            x, Fs,
            frame_length=duration * 1000.0,
            frame_overlap=0.0,
            f0min=float(freq_low),
            f0max=float(freq_high),
            show=False
        )[:2]
        F0 = np.array(F0, dtype=float).flatten()
    except Exception as e:
        print("⚠️ Praat pitch failed:", e)
        F0 = np.zeros_like(dB)

    if F0 is None or F0.size == 0:
        F0 = np.zeros_like(dB)

    # === Optional CPPS per frame (connected-speech friendly spCPPS) ===
    if _HAS_CPPS:
        try:
            CPPS, _ = spCPPS(
                x, Fs,
                frame_len_s=duration,
                hop_s=duration,
                f0min=float(freq_low),
                f0max=float(freq_high),
                fft_size=None,
                freq_smooth_hz=500.0,
                quef_smooth_s=0.010
            )
        except Exception as e:
            print("⚠️ CPPS computation failed:", e)
            CPPS = np.zeros_like(dB)
    else:
        CPPS = np.zeros_like(dB)

    # === Align lengths ===
    limit = min(len(dB), len(F0), len(windowTime), len(CPPS))
    dB = dB[:limit]; windowTime = windowTime[:limit]; F0 = F0[:limit]; CPPS = CPPS[:limit]

    # === F0 limits & distance normalization ===
    F0 = np.where((F0 < freq_low) | (F0 > freq_high), 0.0, F0)

    # Distance-correct SPL to the target distance
    target_distance_m = float(max(target_distance_m, 1e-9))
    dB = dB - 20.0 * np.log10(max(distance_cal, 1e-9) / target_distance_m)

    # === Background noise threshold ===
    dB = np.where(dB < 50.0, 0.0, dB)

    # === Clean invalid frames where either SPL or F0 == 0 ===
    mask = (F0 == 0.0) | (dB == 0.0)
    F0[mask] = 0.0
    dB[mask] = 0.0
    CPPS[mask] = 0.0

    # === Sliding “means over time” (ignore zeros) ===
    win_f0 = int(round(f0_mean_win_s / duration))
    win_cpps = int(round(cpps_mean_win_s / duration))
    F0_mean_t = _moving_mean_ignore_zeros(F0, max(1, win_f0))
    CPPS_mean_t = _moving_mean_ignore_zeros(CPPS, max(1, win_cpps))

    # === Save per-frame results (with units; CPPS included) ===
    base_dir = os.path.dirname(os.path.abspath(fname))  # folder of the input audio
    base_name = os.path.splitext(os.path.basename(fname))[0]  # file name without extension
    base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)  # sanitize the NAME only
    base = os.path.join(base_dir, base_name)  # full path without extension

    dist_cm = int(round(target_distance_m * 100))

    df = pd.DataFrame({
        "Time (s)": windowTime,
        f"SPL (dBA) @ {dist_cm} cm": dB,
        "F0 (Hz)": F0,
        "F0 mov.avg (Hz)": F0_mean_t,
        "CPPS (dB)": CPPS,
        "CPPS mov.avg (dB)": CPPS_mean_t
    })
    df.to_excel(f"{base}.xlsx", index=False)

    # === Doses ===
    A = np.column_stack((windowTime, dB, F0))
    dose = DOSI(A, gender_mode)
    dose_df = pd.DataFrame([dose], columns=[
        "Dt (s)", "VLI (kcycles)", "Dd (m)", "De (J)", "Dr (J)",
        "Dt_p (%)", "Dd_n (m/s)", "De_n (J/s)", "Dr_n (J/s)",
        "SPL_mean (dBA)", "F0_mean (Hz)", "SPL_sd (dBA)", "F0_sd (Hz)"
    ])
    dose_df.to_excel(f"{base}_VocalDoses.xlsx", index=False)

    # === Write the 8×panel Summary PNG so the GUI can relocate it ===
    try:
        from voxdose_reports.analyze_plots import render_summary_figure
        render_summary_figure(
            time_vector=time_vector,
            x=x,
            windowTime=windowTime,
            dB=dB,
            F0=F0,
            F0_mean_t=F0_mean_t,
            CPPS=CPPS,
            CPPS_mean_t=CPPS_mean_t,
            dist_cm=dist_cm,
            distance_cal=distance_cal,
            is_calibrated=is_calibrated,
            dose=dose,
            base=base
        )
    except Exception as e:
        # If plotting module isn’t available, don’t fail the analysis.
        print(f"⚠️ Summary figure not written ({e}).")

    return A, dose
