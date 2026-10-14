import numpy as np


def flag_extreme_prices(
    x: np.ndarray,
    threshold: float
) -> np.ndarray:

    valid = ~np.isnan(x)

    # No non-missing observations
    if not np.any(valid):
        return np.zeros(x.shape, dtype=bool)

    values = x[valid]

    mean = np.mean(values)
    std = np.std(values, ddof=0)

    # Zero population standard deviation
    if std == 0:
        return np.zeros(x.shape, dtype=bool)

    z = (x - mean) / std

    flags = np.zeros(x.shape, dtype=bool)
    flags[valid] = np.abs(z[valid]) > threshold

    return flags