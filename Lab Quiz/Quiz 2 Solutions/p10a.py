
import re
import unicodedata

import numpy as np
import pandas as pd


DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")


def _text_field(value):
    """NFKC, collapse whitespace runs, strip, lowercase; '' -> missing."""
    if pd.isna(value):
        return np.nan
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    if text == "":
        return np.nan
    return text.lower()


def _standard_category(value, category_aliases):
    """Strip only (no whitespace collapsing), then alias lookup or title."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text == "":
        return np.nan
    return category_aliases.get(text.lower(), text.title())


def _iso_date(value):
    """Trim, then parse with the three accepted formats, in order."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text == "":
        return np.nan
    for fmt in DATE_FORMATS:
        stamp = pd.to_datetime(text, format=fmt, errors="coerce")
        if pd.notna(stamp):
            return stamp.strftime("%Y-%m-%d")
    return np.nan


def standardize_product_records(
    frame: pd.DataFrame,
    category_aliases: dict,
) -> pd.DataFrame:
    out = frame.copy()

    out["product_name"] = [_text_field(v) for v in out["product_name"]]
    out["brand"] = [_text_field(v) for v in out["brand"]]
    out["category"] = [
        _standard_category(v, category_aliases) for v in out["category"]
    ]
    out["launch_date"] = [_iso_date(v) for v in out["launch_date"]]

    return out
