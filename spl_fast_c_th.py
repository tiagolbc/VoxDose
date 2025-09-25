import numpy as np
from stima_livello import stimaLivello
import matplotlib.pyplot as plt

def SPL_fast_C_TH(x, Fs, C, duration):
    """
    Fast SPL (A-weighted) calculation with calibration (TH).

    Parameters:
    - x: 1D numpy array, audio signal
    - Fs: int, sample rate
    - C: float, calibration constant
    - duration: float, analysis frame length in seconds

    Returns:
    - SPL_mean: float
    - SPL_std: float
    - dB: numpy array, SPL values per frame
    - window_time: numpy array, time values per frame
    """
    t = np.arange(0, len(x)) / Fs
    N = int(duration * Fs)
    window_start = np.arange(N, len(x) - N, N)

    dB = np.zeros(len(window_start))
    dB_partial = np.zeros(len(window_start))
    window_time = t[window_start + round((N - 1) / 2)]

    for i in range(len(window_start)):
        segment = x[window_start[i] : window_start[i] + N]
        _, dB[i] = stimaLivello(segment, Fs, C)
        dB_partial[i] = dB[i] * (window_time[1] - window_time[0])

    if len(window_time) > 0:
        denom = np.max(window_time)
    else:
        denom = 1e-9
    SPL_mean = np.sum(dB_partial) / denom

    SPL_std = np.std(dB)

    # Plot SPL
    plt.figure(3)
    plt.clf()
    plt.plot(window_time, dB, linewidth=2)
    plt.title('A-weighted Sound Level')
    plt.xlabel('Time (sec.)')
    plt.ylabel('Sound Level (dBA)')
    plt.xlim([t[0], t[-1]])
    plt.grid(True)
    plt.show()
    plt.savefig("SPL_plot.png", dpi=300, bbox_inches='tight')

    return SPL_mean, SPL_std, dB, window_time
