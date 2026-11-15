# voxdose_reports/plots_pitch_block.py
import numpy as np
import matplotlib.pyplot as plt

def render_pitch_plot(x, fs, T, F0):
    N = len(x)
    t = np.arange(N) / fs
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.plot(t, x)
    plt.title("Waveform")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")

    plt.subplot(2, 1, 2)
    plt.plot(T, F0)
    plt.title("Pitch Track (Praat)")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    plt.tight_layout()
    plt.show()
