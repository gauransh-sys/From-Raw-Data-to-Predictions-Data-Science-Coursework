import numpy as np
import pandas as pd


def standardized_product_matrix(
    frame: pd.DataFrame,
    columns: list[str]
) -> np.ndarray:

    X = frame[columns].copy()

    # Median imputation
    for column in columns:
        X[column] = X[column].fillna(X[column].median())

    # Population mean and standard deviation
    means = X.mean()
    stds = X.std(ddof=0)

    # Standardize
    result = (X - means) / stds

    # Constant columns -> 0
    for column in columns:
        if stds[column] == 0:
            result[column] = 0.0

    return result.to_numpy()