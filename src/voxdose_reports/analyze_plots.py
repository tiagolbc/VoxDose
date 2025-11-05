# voxdose_reports/analyze_plots.py
import numpy as np
import matplotlib.pyplot as plt
from voxdose_core.analyze_wav_spl_f0 import _moving_leq_dB

def render_summary_figure(
    time_vector, x,
    windowTime, dB,
    F0, F0_mean_t,
    CPPS, CPPS_mean_t,
    dist_cm,
    distance_cal,
    is_calibrated,
    dose,
    base
):
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

    # --- FIX: cap window length and align lengths ---
    nwin = int(round(60.0 / 0.05))
    nwin = max(1, min(nwin, int(dB.size)))  # cap to series length
    leq60 = _moving_leq_dB(dB, nwin)

    # If helper returns a different length, align conservatively
    min_len = min(leq60.size, windowTime.size)
    leq60 = leq60[:min_len]
    wt_for_leq = windowTime[:min_len]

    leq_mask = np.isfinite(leq60) & (leq60 > 0.0)
    if np.any(leq_mask):
        ax2.plot(wt_for_leq[leq_mask], leq60[leq_mask], linewidth=2.0,
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

    # 4) F0 timeline
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

    # 6) CPPS timeline
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

    # 8) Results table
    ax8 = fig.add_subplot(4, 2, 8)
    ax8.axis("off")

    dB_mean = float(np.mean(spl_valid)) if spl_valid.size else 0.0
    f0_mean_txt = float(np.mean(f0_valid)) if f0_valid.size else 0.0
    cpps_mean = float(np.mean(cpps_valid)) if cpps_valid.size else 0.0

    distance_value = (f"{int(distance_cal * 100)} → {dist_cm} cm"
                      if is_calibrated else "Uncalibrated (C=50)")

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
        cellText=rows, colLabels=["Metric", "Value"],
        cellLoc="center", colLoc="center",
        colWidths=[0.76, 0.24], bbox=[0.01, 0.00, 0.98, 0.98]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.25, 2.25)

    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_text_props(weight='bold')
            cell.set_facecolor((0.96, 0.96, 0.96))
        cell.set_edgecolor((0, 0, 0, 0.35))
        cell.set_linewidth(0.6)

    ROW_SPACING = 1.25
    for r in range(1, len(rows) + 1):
        for c in (0, 1):
            cell = table[r, c]
            cell.set_height(cell.get_height() * ROW_SPACING)

    for r in range(1, len(rows) + 1):
        table[r, 0].set_text_props(ha="left")

    fig.tight_layout()
    fig.savefig(f"{base}_Summary_{dist_cm}cm.png", dpi=300, bbox_inches='tight')
    plt.close(fig)
