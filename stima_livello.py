import numpy as np

def stimaLivello(x, Fs, C):
    """
    Estimate the A-weighted SPL of a segment.

    Parameters:
    - x: 1D array, signal frame
    - Fs: int, sampling frequency
    - C: float, calibration constant

    Returns:
    - X: ndarray, log-magnitude FFT spectrum
    - dB: float, SPL in dBA (with calibration)
    """
    X = np.abs(np.fft.fft(x))
    X[X == 0] = 1e-17  # Avoid log(0)
    f = (Fs / len(X)) * np.arange(len(X))
    ind = np.where(f < Fs / 2)[0]
    f = f[ind]
    X = X[ind]
    # Power per sample
    TotalEnergy = np.sum(X ** 2) / len(X)
    MeanEnergy = TotalEnergy / ((1 / Fs) * len(x))
    dB = 10 * np.log10(MeanEnergy) + C
    X_db = 20 * np.log10(X)
    return X_db, dB
