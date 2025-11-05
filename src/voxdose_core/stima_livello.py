import numpy as np

def stimaLivello(x, Fs, C):
    """
    Parameters
    ----------
    x : 1D array
        Signal frame.
    Fs : int
        Sampling frequency.
    C : float
        Calibration constant.

    Returns
    -------
    X_db : ndarray
        Log-magnitude FFT spectrum (dB).
    dB : float
        SPL in dBA (with calibration constant).
    """
    x = np.asarray(x, dtype=float)

    # FFT magnitude
    X = np.abs(np.fft.fft(x))
    X[X == 0] = 1e-17  # avoid log(0)
    f = (Fs / len(X)) * np.arange(len(X))
    ind = np.where(f < Fs / 2)[0]
    f = f[ind]
    X = X[ind]

    # Power per sample
    TotalEnergy = np.sum(X ** 2) / len(X)
    MeanEnergy = TotalEnergy / ((1 / Fs) * len(x))

    # --- FIX: handle silence (zero energy) ---
    if MeanEnergy <= 1e-20:
        X_db = 20 * np.log10(X)
        return X_db, float("-inf")

    # Normal case
    dB = 10 * np.log10(MeanEnergy) + C
    X_db = 20 * np.log10(X)
    return X_db, dB

