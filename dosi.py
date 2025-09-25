import numpy as np

def DOSI(data, gender_mode='male'):
    """
    Compute vocal doses from SPL and F0 data.

    Parameters
    ----------
    data : ndarray, shape (n, 3)
        Columns: [time(s), SPL(dBA), F0(Hz)], preferably at ~0.05 s step.
    gender_mode : {'male','female','other'} or {1,0}
        'male'   -> male formulation
        'female' -> female formulation
        'other'  -> mean of male and female (Pasquale's approach)
        Backward compatible: 1 -> 'male', 0 -> 'female'

    Returns
    -------
    dose : ndarray, (13,)
        [Dt, VLI, Dd, De, Dr, Dt_percentage,
         Dd_norm, De_norm, Dr_norm,
         SPL_mean, F0_mean, SPL_sd, F0_sd]
    """
    data = np.asarray(data)
    if data.ndim != 2 or data.shape[1] < 3:
        raise ValueError("DOSI expects data with shape (n,3): [time, SPL, F0].")

    # --- Backward compatibility with old int argument (1=male, 0=female)
    if isinstance(gender_mode, (int, np.integer)):
        gender_mode = 'male' if int(gender_mode) == 1 else 'female'
    gender_mode = str(gender_mode).lower()
    if gender_mode not in ('male', 'female', 'other'):
        raise ValueError("gender_mode must be 'male', 'female', or 'other'.")

    t   = data[:, 0]
    SPL = data[:, 1]
    F0  = data[:, 2]

    # --- Infer time_step (fallback 0.05 s)
    if len(t) >= 2:
        dt = np.diff(t)
        # robust estimate: median of positive diffs
        dt_pos = dt[dt > 0]
        time_step = float(np.median(dt_pos)) if dt_pos.size else 0.05
    else:
        time_step = 0.05

    n = len(t)
    kv   = (F0 > 0) & (SPL > 0)          # voiced & valid SPL
    omega = 2 * np.pi * F0

    Pth = np.zeros(n)
    Pl  = np.zeros(n)
    Aamp= np.zeros(n)   # amplitude term already time-weighted (includes time_step)
    T   = np.zeros(n)
    eta = np.zeros(n)

    Dt_partial  = np.zeros(n)
    VLI_partial = np.zeros(n)
    Dd_partial  = np.zeros(n)
    De_partial  = np.zeros(n)
    Dr_partial  = np.zeros(n)
    SPL_partial = np.zeros(n)
    F0_partial  = np.zeros(n)

    for i in range(n):
        if not kv[i]:
            continue

        f0   = float(F0[i])
        spl  = float(SPL[i])

        # --- Pasquale-style paths ---
        # Common lung pressure from SPL (same expression in all branches):
        # Pl = Pth + 10**((SPL - 72.48)/27.3)
        if gender_mode == 'male':
            Pth_i = 0.14 + 0.06 * (f0 / 120.0) ** 2
            Pl_i  = Pth_i + 10 ** ((spl - 72.48) / 27.3)
            A_i   = time_step * 0.016 * ((max((Pl_i - Pth_i) / max(Pth_i, 1e-12), 0.0)) ** 0.5)
            T_i   = 0.0158 / (1.0 + 2.15 * (f0 / 120.0) ** 0.5)
            eta_i = 5.4 / max(f0, 1e-12)

        elif gender_mode == 'female':
            Pth_i = 0.14 + 0.06 * (f0 / 190.0) ** 2
            Pl_i  = Pth_i + 10 ** ((spl - 72.48) / 27.3)
            A_i   = time_step * 0.010 * ((max((Pl_i - Pth_i) / max(Pth_i, 1e-12), 0.0)) ** 0.5)
            T_i   = 0.01063 / (1.0 + 1.69 * (f0 / 190.0) ** 0.5)
            eta_i = 1.4 / max(f0, 1e-12)

        else:  # 'other' = mean of male and female paths
            # male
            Pth_m = 0.14 + 0.06 * (f0 / 120.0) ** 2
            Pl_m  = Pth_m + 10 ** ((spl - 72.48) / 27.3)
            A_m   = time_step * 0.016 * ((max((Pl_m - Pth_m) / max(Pth_m, 1e-12), 0.0)) ** 0.5)
            T_m   = 0.0158 / (1.0 + 2.15 * (f0 / 120.0) ** 0.5)
            eta_m = 5.4 / max(f0, 1e-12)
            # female
            Pth_f = 0.14 + 0.06 * (f0 / 190.0) ** 2
            Pl_f  = Pth_f + 10 ** ((spl - 72.48) / 27.3)
            A_f   = time_step * 0.010 * ((max((Pl_f - Pth_f) / max(Pth_f, 1e-12), 0.0)) ** 0.5)
            T_f   = 0.01063 / (1.0 + 1.69 * (f0 / 190.0) ** 0.5)
            eta_f = 1.4 / max(f0, 1e-12)

            Pth_i = 0.5 * (Pth_m + Pth_f)
            Pl_i  = 0.5 * (Pl_m  + Pl_f)
            A_i   = 0.5 * (A_m   + A_f)
            T_i   = 0.5 * (T_m   + T_f)
            eta_i = 0.5 * (eta_m + eta_f)

        # store
        Pth[i], Pl[i], Aamp[i], T[i], eta[i] = Pth_i, Pl_i, A_i, T_i, eta_i

        # --- Integrands (use time_step once) ---
        Dt_partial[i]  = time_step
        VLI_partial[i] = f0 * time_step
        Dd_partial[i]  = f0 * A_i
        De_partial[i]  = eta_i * ((A_i / max(T_i, 1e-12)) ** 2) * (omega[i] ** 2) * time_step / 1000.0
        Dr_partial[i]  = (10 ** ((spl - 120.0) / 10.0)) * 1000.0 * time_step

        SPL_partial[i] = spl * time_step
        F0_partial[i]  = f0  * time_step

    # --- Totals ---
    Dt  = float(np.sum(Dt_partial))
    VLI = float(np.sum(VLI_partial) / 1000.0)
    Dd  = float(4.0 * np.sum(Dd_partial))
    De  = float(0.5 * np.sum(De_partial))
    Dr  = float(4.0 * np.pi * np.sum(Dr_partial))

    duration = float(max(t[-1] - t[0], 1e-12)) if n >= 2 else float(max(Dt, 1e-12))
    Dt_percentage = 100.0 * (Dt / duration)

    if Dt > 0:
        Dd_norm = Dd / Dt
        De_norm = De / Dt
        Dr_norm = Dr / Dt
        SPL_mean = float(np.sum(SPL_partial) / Dt)
        F0_mean  = float(np.sum(F0_partial)  / Dt)
        # simple dispersion of the time-weighted series (kept for continuity)
        SPL_sd = float(np.std(SPL_partial))
        F0_sd  = float(np.std(F0_partial))
    else:
        Dd_norm = De_norm = Dr_norm = SPL_mean = F0_mean = SPL_sd = F0_sd = 0.0

    return np.array([
        Dt, VLI, Dd, De, Dr, Dt_percentage,
        Dd_norm, De_norm, Dr_norm,
        SPL_mean, F0_mean, SPL_sd, F0_sd
    ], dtype=float)
