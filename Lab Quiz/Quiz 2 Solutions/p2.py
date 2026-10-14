import numpy as np
from scipy.spatial import distance


def closest_product_pair(X: np.ndarray) -> tuple[int, int, float]:
    D = distance.cdist(X, X, metric="euclidean")

    np.fill_diagonal(D, np.inf)

    i, j = np.unravel_index(np.argmin(D), D.shape)

    return int(i), int(j), float(D[i, j])