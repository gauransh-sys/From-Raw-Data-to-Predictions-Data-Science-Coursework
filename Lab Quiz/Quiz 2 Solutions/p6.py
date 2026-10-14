import pandas as pd


def median_supplier_prices(
    listings: pd.DataFrame
) -> pd.DataFrame:

    result = (
        listings
        .groupby("product_id")["supplier_price"]
        .median()
        .reset_index()
        .rename(columns={
            "supplier_price": "median_supplier_price"
        })
        .sort_values("product_id")
        .reset_index(drop=True)
    )

    return result