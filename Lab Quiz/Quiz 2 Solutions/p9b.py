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


def _median(frame, column, group):
    return _num(frame[column]).groupby(frame[group]).transform("median")


def _fill(frame, table, column, choices, digits, audit):
    for row_index in frame.index[frame[column].isna()]:
        method, value = choices[-1][0], np.nan
        for name, values in choices:
            candidate = values.loc[row_index] if isinstance(values, pd.Series) else values
            if pd.notna(candidate):
                method, value = name, candidate
                break
        value = np.nan if pd.isna(value) else round(float(value), digits)
        frame.at[row_index, column] = value
        audit.append([table, int(row_index), column, value, method])


def impute_contextually(
    products: pd.DataFrame,
    orders: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p, o, audit = products.copy(), orders.copy(), []
    p["_category"] = p["category"].map(_cat)
    _fill(p, "products", "unit_price", [
        ("category_median", _median(p, "unit_price", "_category")),
        ("global_median", _num(p["unit_price"]).median()),
    ], 2, audit)
    _fill(o, "orders", "discount_rate", [
        ("city_median", _median(o, "discount_rate", "order_city")),
        ("global_median", _num(o["discount_rate"]).median()),
    ], 4, audit)
    prices = _num(p.set_index("product_id")["unit_price"]).to_dict()
    amount = o["product_id"].map(prices) * _num(o["quantity"]) * (1 - _num(o["discount_rate"]))
    _fill(o, "orders", "order_amount", [
        ("formula_repair", amount),
        ("city_median", _median(o, "order_amount", "order_city")),
        ("global_median", _num(o["order_amount"]).median()),
    ], 2, audit)
    columns = ["table", "row_index", "column", "new_value", "method"]
    audit_frame = (
        pd.DataFrame(audit, columns=columns)
        .sort_values(["table", "row_index", "column"])
        .reset_index(drop=True)
    )
    return p.drop(columns="_category"), o, audit_frame
