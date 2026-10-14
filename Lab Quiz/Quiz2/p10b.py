import re

import numpy as np
import pandas as pd


def generate_product_candidate_pairs(
    products_std: pd.DataFrame,
) -> np.ndarray:
    """Return the candidate pairs (i, j) with i < j, lexicographically sorted."""
    raise NotImplementedError
