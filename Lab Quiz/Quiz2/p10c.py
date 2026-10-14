import numpy as np
import pandas as pd
from rapidfuzz.distance import JaroWinkler


FIELDS = [
    "name_sim",
    "brand_agree",
    "category_agree",
    "date_agree",
    "price_close",
]

OUTPUT_COLUMNS = ["i", "j"] + FIELDS + ["score", "decision"]

PRICE_TOLERANCE = 0.02


def compare_and_score_product_pairs(
    products_std: pd.DataFrame,
    pairs: np.ndarray,
    weights: dict[str, float],
    lower_threshold: float,
    upper_threshold: float,
) -> pd.DataFrame:
    """Return the comparison vector, score, and decision for every pair."""
    raise NotImplementedError
