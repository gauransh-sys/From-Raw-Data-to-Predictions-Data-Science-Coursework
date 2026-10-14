
import re

import numpy as np
import pandas as pd


def _name_key(value):
    """Maximal runs of [a-z0-9], de-duplicated, sorted, space-joined."""
    if pd.isna(value):
        return None
    tokens = re.findall(r"[a-z0-9]+", str(value))
    if not tokens:
        return None
    return " ".join(sorted(set(tokens)))


def _pairs_from_keys(keys):
    """All within-block pairs (i, j) with i < j; None keys are skipped."""
    blocks = {}
    for row, key in enumerate(keys):
        if key is None:
            continue
        blocks.setdefault(key, []).append(row)

    pairs = set()
    for members in blocks.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                pairs.add((members[a], members[b]))
    return pairs


def generate_product_candidate_pairs(products_std: pd.DataFrame) -> np.ndarray:
    brand = products_std["brand"].tolist()
    category = products_std["category"].tolist()
    name = products_std["product_name"].tolist()

    # Pass 1: same standardized brand AND same standardized category.
    pass_one = [
        None if (pd.isna(b) or pd.isna(c)) else (str(b), str(c))
        for b, c in zip(brand, category)
    ]

    # Pass 2: same name key.
    pass_two = [_name_key(v) for v in name]

    pairs = _pairs_from_keys(pass_one) | _pairs_from_keys(pass_two)

    if not pairs:
        return np.zeros((0, 2), dtype=int)

    return np.array(sorted(pairs), dtype=int)
