import numpy as np
import pandas as pd


CAT = {
    "audio": "Audio", "sound": "Audio",
    "kitchen": "Kitchen", "kitchenware": "Kitchen",
    "outdoor": "Outdoor", "camping": "Outdoor",
    "stationery": "Stationery", "office supplies": "Stationery",
    "lighting": "Lighting", "lights": "Lighting",
    "fitness": "Fitness", "exercise": "Fitness",
    "travel": "Travel", "luggage": "Travel",
    "computing": "Computing", "computer": "Computing",
}


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def _cat(value):
    text = "" if pd.isna(value) else str(value).strip()
    return np.nan if not text else CAT.get(text.lower(), text.title())


def _mad_score(values, groups):
    x = _num(values)
    count = x.groupby(groups).transform("count")
    median = x.groupby(groups).transform("median")
    mad = (x - median).abs().groupby(groups).transform("median")
    use_global = groups.isna() | count.lt(8)
    global_median = x.median()
    median = median.mask(use_global, global_median)
    mad = mad.mask(use_global, (x - global_median).abs().median())
    return (0.6745 * (x - median) / mad).where(mad.ne(0))


def _iqr_score(values, groups):
    x = _num(values)
    count = x.groupby(groups).transform("count")
    q1 = x.groupby(groups).transform("quantile", q=.25)
    q3 = x.groupby(groups).transform("quantile", q=.75)
    use_global = groups.isna() | count.lt(8)
    q1 = q1.mask(use_global, x.quantile(.25))
    q3 = q3.mask(use_global, x.quantile(.75))
    width = q3 - q1
    lower, upper = q1 - 1.5 * width, q3 + 1.5 * width
    distance = np.maximum(lower - x, x - upper)
    flag = distance.gt(0) & width.notna() & width.ne(0)
    return flag, (distance / width).where(flag)


def detect_contextual_outliers(
    products: pd.DataFrame,
    listings: pd.DataFrame,
) -> pd.DataFrame:
    category = products["category"].map(_cat)
    prices = _num(products.set_index("product_id")["unit_price"]).to_dict()
    categories = category.groupby(products["product_id"]).first().to_dict()
    matched_price = _num(listings["product_id"].map(prices))
    markup = (_num(listings["supplier_price"]) / matched_price).replace([np.inf, -np.inf], np.nan)
    z = _mad_score(markup, listings["product_id"].map(categories))
    rows = [
        ["supplier_listings", int(i), "supplier_price_contextual", float(abs(z.at[i]))]
        for i in listings.index[z.abs() > 3.5]
    ]
    price = _num(products["unit_price"])
    flag, score = _iqr_score(price.where(price > 0), category)
    rows += [
        ["products", int(i), "product_price_contextual", float(score.at[i])]
        for i in products.index[flag]
    ]
    columns = ["table", "row_index", "outlier_type", "score"]
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values(["table", "row_index", "outlier_type"])
        .reset_index(drop=True)
    )
