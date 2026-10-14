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


def _agree(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    return 1.0 if a == b else 0.0


def _name_similarity(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    return float(JaroWinkler.similarity(str(a), str(b)))


def _price_close(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    pa, pb = float(a), float(b)
    largest = max(abs(pa), abs(pb))
    if largest == 0:
        return 1.0
    return 1.0 if abs(pa - pb) / largest <= PRICE_TOLERANCE else 0.0


def compare_and_score_product_pairs(
    products_std: pd.DataFrame,
    pairs: np.ndarray,
    weights: dict,
    lower_threshold: float,
    upper_threshold: float,
) -> pd.DataFrame:
    name = products_std["product_name"].tolist()
    brand = products_std["brand"].tolist()
    category = products_std["category"].tolist()
    date = products_std["launch_date"].tolist()
    price = products_std["unit_price"].tolist()

    pair_array = np.asarray(pairs, dtype=int).reshape(-1, 2)

    records = []
    for i, j in pair_array:
        i, j = int(i), int(j)
        records.append([
            i,
            j,
            _name_similarity(name[i], name[j]),
            _agree(brand[i], brand[j]),
            _agree(category[i], category[j]),
            _agree(date[i], date[j]),
            _price_close(price[i], price[j]),
        ])

    out = pd.DataFrame(records, columns=["i", "j"] + FIELDS)
    if len(out) == 0:
        out = pd.DataFrame({
            "i": pd.Series([], dtype=int),
            "j": pd.Series([], dtype=int),
            **{f: pd.Series([], dtype=float) for f in FIELDS},
        })

    values = out[FIELDS].to_numpy(dtype=float)
    w = np.array([float(weights.get(f, 0.0)) for f in FIELDS], dtype=float)

    available = ~np.isnan(values)
    denominator = available @ w
    numerator = np.where(available, values, 0.0) @ w

    with np.errstate(invalid="ignore", divide="ignore"):
        score = np.where(
            denominator > 0,
            numerator / np.where(denominator > 0, denominator, 1.0),
            np.nan,
        )

    out["score"] = score

    decision = np.where(
        np.isnan(score),
        "nonmatch",
        np.where(
            score >= upper_threshold,
            "match",
            np.where(score < lower_threshold, "nonmatch", "review"),
        ),
    )
    out["decision"] = decision.astype(object)

    return out[OUTPUT_COLUMNS]
