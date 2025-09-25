import numpy as np
from stima_livello import stimaLivello
import matplotlib.pyplot as plt

def SPL_fast(x, Fs):
    """
    Fast SPL (A-weighted) calculation without external calibration.

    Parameters:
    - x: 1D numpy array, audio signal
    - Fs: int, sample rate

    Returns:
    - SPL_mean: float, mean SPL
    - SPL_std: float, std of SPL
    """
    C = 50
    duration = 0.05  # seconds

    t = np.arange(len(x)) / Fs
    N = int(np.ceil(duration * Fs))
    N = 2 ** int(np.ceil(np.log2(N)))
    window_start = np.arange(0, len(x) - N + 1, N)  # Corrigido para +1
    dBA = np.zeros(len(window_start))
    dBA_partial = np.zeros(len(window_start))
    window_time = t[window_start + int(round((N - 1) / 2))]

    for i, start in enumerate(window_start):
        segment = x[start : start + N]
        _, dBA[i] = stimaLivello(segment, Fs, C)
        # Evita erro se só tem 1 frame
        if len(window_time) > 1:
            delta_t = window_time[1] - window_time[0]
        else:
            delta_t = duration
        dBA_partial[i] = dBA[i] * delta_t

    SPL_mean = np.sum(dBA_partial) / (window_time[-1] if len(window_time) > 1 else window_time[0])
    SPL_std = np.std(dBA)

    # Plotting dBA
    plt.figure(3)
    plt.clf()
    plt.plot(window_time, dBA, linewidth=2)
    plt.title('A-weighted Sound Level')
    plt.xlabel('Time (sec.)')
    plt.ylabel('Sound Level (dBA)')
    plt.xlim([t[0], t[-1]])
    plt.grid(True)
    plt.savefig("SPL_dBA_plot.png", dpi=300, bbox_inches='tight')
    plt.show()

    print("Number of frames:", len(window_start))
    print("window_time max:", np.max(window_time))
    print("Total duration (s):", len(x) / Fs)

    return SPL_mean, SPL_std
