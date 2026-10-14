import numpy as np
from scipy.spatial import distance


def most_similar_binary_pair(
    X: np.ndarray
) -> tuple[int, int, float]:

    n = X.shape[0]

    best_i = 0
    best_j = 1
    best_similarity = -1.0

    for i in range(n):
        for j in range(i + 1, n):

            # Special case required by the question:
            # two all-zero rows have Jaccard similarity 1.0
            if np.all(X[i] == 0) and np.all(X[j] == 0):
                similarity = 1.0
            else:
                similarity = 1.0 - distance.jaccard(X[i], X[j])

            if similarity > best_similarity:
                best_similarity = similarity
                best_i = i
                best_j = j

    return int(best_i), int(best_j), float(best_similarity)