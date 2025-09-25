# analyze_wav_spl_f0.py
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import soundfile as sf
import re

from spl_fast import SPL_fast                 # mean SPL for a given audio; uses internal C=50
from spl_fast_c_th import SPL_fast_C_TH       # per-frame SPL with calibration constant C
from sp_pitch_track_praat import spPitchTrackPraat
from dosi import DOSI

# CPPS is optional; if module is not present, we skip it gracefully
try:
    from sp_cpps import spCPPS
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

    # === Plots (4×2 grid) ===
    fig = plt.figure(figsize=(12, 10))

    # 1) Waveform
    ax1 = fig.add_subplot(4, 2, 1)
    ax1.plot(time_vector, x, linewidth=0.8, color="#1976D2")
    ax1.set_title("Audio Waveform")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Amplitude")

    # 2) SPL with Leq(60 s)
    ax2 = fig.add_subplot(4, 2, 2)
    spl_mask = dB > 0.0
    ax2.plot(windowTime[spl_mask], dB[spl_mask], '.', markersize=3,
             label=f"SPL (dBA) @ {dist_cm} cm", color="#E53935", alpha=0.55)
    nwin = int(round(60.0 / 0.05))
    leq60 = _moving_leq_dB(dB, nwin)
    leq_mask = np.isfinite(leq60) & (leq60 > 0.0)
    ax2.plot(windowTime[leq_mask], leq60[leq_mask], linewidth=2.0,
             label=f"Leq (60 s) @ {dist_cm} cm", color="#0B5394")
    ax2.set_title(f"SPL at {dist_cm} cm with Leq(60 s)")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Level (dBA)")
    ax2.legend(loc="best")

    # 3) SPL histogram
    ax3 = fig.add_subplot(4, 2, 3)
    spl_valid = dB[dB > 0.0]
    if spl_valid.size:
        ax3.hist(spl_valid, bins=30, facecolor="#EF5350",
                 edgecolor="white", alpha=0.9)
    ax3.set_title(f"SPL Histogram (@ {dist_cm} cm)")
    ax3.set_xlabel("SPL (dBA)")
    ax3.set_ylabel("Count")

    # 4) F0 timeline — points + moving mean curve
    ax4 = fig.add_subplot(4, 2, 4)
    f0_mask = F0 > 0.0
    ax4.plot(windowTime[f0_mask], F0[f0_mask], '.', markersize=3,
             color="#26C6DA", alpha=0.55, label="F0")
    f0m_mask = F0_mean_t > 0.0
    if np.any(f0m_mask):
        ax4.plot(windowTime[f0m_mask], F0_mean_t[f0m_mask], linewidth=2.0,
                 color="#006064", label=f"F0 mov.avg (5 s)")
    ax4.set_title("F0 Timeline")
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Frequency (Hz)")
    ax4.legend(loc="best")

    # 5) F0 histogram
    ax5 = fig.add_subplot(4, 2, 5)
    f0_valid = F0[f0_mask]
    if f0_valid.size:
        ax5.hist(f0_valid, bins=30, facecolor="#26C6DA",
                 edgecolor="white", alpha=0.9)
    ax5.set_title("F0 Histogram")
    ax5.set_xlabel("F0 (Hz)")
    ax5.set_ylabel("Count")

    # 6) CPPS timeline — points + moving mean curve
    ax6 = fig.add_subplot(4, 2, 6)
    cpps_mask = CPPS > 0.0
    ax6.plot(windowTime[cpps_mask], CPPS[cpps_mask], '.', markersize=3,
             color="#8E24AA", alpha=0.60, label="CPPS")
    cpm_mask = CPPS_mean_t > 0.0
    if np.any(cpm_mask):
        ax6.plot(windowTime[cpm_mask], CPPS_mean_t[cpm_mask], linewidth=2.0,
                 color="#4A148C", label=f"CPPS mov.avg (5 s)")
    ax6.set_title("CPPS Timeline")
    ax6.set_xlabel("Time (s)")
    ax6.set_ylabel("CPPS (dB)")
    ax6.legend(loc="best")

    # 7) CPPS histogram
    ax7 = fig.add_subplot(4, 2, 7)
    cpps_valid = CPPS[cpps_mask]
    if cpps_valid.size:
        ax7.hist(cpps_valid, bins=30, facecolor="#8E24AA",
                 edgecolor="white", alpha=0.9)
    ax7.set_title("CPPS Histogram")
    ax7.set_xlabel("CPPS (dB)")
    ax7.set_ylabel("Count")

    # 8) Results table (bottom-right) — bigger box + smaller font
    ax8 = fig.add_subplot(4, 2, 8)  # make sure ax8 exists
    ax8.axis("off")

    # means for reference (you already computed spl_valid, f0_valid, cpps_valid above)
    dB_mean = float(np.mean(spl_valid)) if spl_valid.size else 0.0
    f0_mean_txt = float(np.mean(f0_valid)) if f0_valid.size else 0.0
    cpps_mean = float(np.mean(cpps_valid)) if cpps_valid.size else 0.0

    # shorter distance text to avoid wrapping
    distance_value = (f"{int(distance_cal * 100)} → {dist_cm} cm"
                      if is_calibrated else "Uncalibrated (C=50)")

    # unpack 'dose' (order kept from your code)
    (
        Dt_s, VLI_kcycles, Dd_m, De_J, Dr_J,
        Dt_pct, Dd_rate, De_rate, Dr_rate,
        SPL_mean_dBA, F0_mean_Hz, SPL_sd_dBA, F0_sd_Hz
    ) = dose

    rows = [
        ["Total phonation time (s)", f"{Dt_s:.1f}"],
        ["Vocal Loading Index (kcycles)", f"{VLI_kcycles:.2f}"],
        ["Distance dose (m)", f"{Dd_m:.2f}"],
        ["Energy dose (J)", f"{De_J:.2f}"],
        ["Radiation dose (J)", f"{Dr_J:.2f}"],
        ["Phonation time (%)", f"{Dt_pct:.1f}"],
        ["Distance dose rate (m/s)", f"{Dd_rate:.3f}"],
        ["Energy dose rate (J/s)", f"{De_rate:.3f}"],
        ["Radiation dose rate (J/s)", f"{Dr_rate:.3f}"],
        ["Mean SPL (dBA)", f"{SPL_mean_dBA:.1f}"],
        ["Mean F0 (Hz)", f"{F0_mean_Hz:.1f}"],
        ["SPL standard deviation (dBA)", f"{SPL_sd_dBA:.1f}"],
        ["F0 standard deviation (Hz)", f"{F0_sd_Hz:.1f}"],
        ["CPPS mean (dB)", f"{cpps_mean:.2f}"],
        ["Distance correction", distance_value],
    ]

    table = ax8.table(
        cellText=rows,
        colLabels=["Metric", "Value"],
        cellLoc="center",
        colLoc="center",
        colWidths=[0.76, 0.24],  # wider left column
        bbox=[0.01, 0.00, 0.98, 0.98]  # fill the subplot
    )

    # smaller font and taller rows (more vertical spacing)
    table.auto_set_font_size(False)
    table.set_fontsize(8)  # one point smaller
    table.scale(1.25, 2.25)  # ↑ increase SECOND number for more spacing

    # style header + thin borders
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_text_props(weight='bold')
            cell.set_facecolor((0.96, 0.96, 0.96))
        cell.set_edgecolor((0, 0, 0, 0.35))
        cell.set_linewidth(0.6)

    # EXTRA spacing: expand each data row's height a bit more
    ROW_SPACING = 1.25  # try 1.10–1.25 as you like
    for r in range(1, len(rows) + 1):  # skip header row (r=0)
        for c in (0, 1):
            cell = table[r, c]
            cell.set_height(cell.get_height() * ROW_SPACING)

    # left-align the "Metric" column for readability
    for r in range(1, len(rows) + 1):
        table[r, 0].set_text_props(ha="left")

    fig.tight_layout()
    fig.savefig(f"{base}_Summary_{dist_cm}cm.png", dpi=300, bbox_inches='tight')
    plt.close(fig)

    return A, dose
