import numpy as np
import pandas as pd


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def build_missingness_and_validity_report(
    products: pd.DataFrame,
    orders: pd.DataFrame,
    listings: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    p, o, s = products.copy(), orders.copy(), listings.copy()
    ids = set(p["product_id"].dropna())
    rules = [
        ("products", "unit_price", p, _num(p["unit_price"]) <= 0),
        ("orders", "quantity", o, (_num(o["quantity"]) <= 0) | (_num(o["quantity"]) > 10)),
        ("orders", "order_amount", o, _num(o["order_amount"]) <= 0),
        ("orders", "product_id", o, o["product_id"].notna() & ~o["product_id"].isin(ids)),
        ("supplier_listings", "supplier_price", s, _num(s["supplier_price"]) <= 0),
    ]
    rows = []
    for table, column, frame, invalid in rules:
        before = int(frame[column].isna().sum())
        frame.loc[invalid.fillna(False), column] = np.nan
        after = int(frame[column].isna().sum())
        rate = after / len(frame) if len(frame) else np.nan
        rows.append([table, column, before, after - before, after, rate])

    columns = [
        "table", "column", "n_missing_before", "n_invalid_converted",
        "n_missing_after", "missing_rate_after",
    ]
    report = (
        pd.DataFrame(rows, columns=columns)
        .sort_values(["table", "column"])
        .reset_index(drop=True)
    )
    cleaned = {"products": p, "orders": o, "supplier_listings": s}
    return report, cleaned
