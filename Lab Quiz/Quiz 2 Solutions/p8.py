import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.neighbors import LocalOutlierFactor


def most_anomalous_products(
    X: np.ndarray,
    n_neighbors: int,
    m: int
) -> np.ndarray:

    # Median imputation
    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)

    # Fit LOF
    lof = LocalOutlierFactor(
        n_neighbors=n_neighbors
    )
    lof.fit_predict(X_imputed)

    # More negative score = more anomalous
    scores = lof.negative_outlier_factor_

    # Primary key: score ascending
    # Secondary key: row index ascending
    indices = np.arange(len(scores))
    order = np.lexsort((indices, scores))

    return order[:m]