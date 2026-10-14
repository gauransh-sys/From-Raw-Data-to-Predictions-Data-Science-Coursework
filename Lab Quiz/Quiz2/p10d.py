import numpy as np
import pandas as pd


STRING_COLUMNS = ["product_name", "brand", "category", "launch_date"]

NUMERIC_COLUMNS = [
    "unit_price",
    "stock_count",
    "rating",
    "warranty_years",
    "weight_kg",
]

GOLDEN_COLUMNS = (
    ["entity_id", "product_id"]
    + STRING_COLUMNS
    + NUMERIC_COLUMNS
    + ["cluster_size", "source_product_ids"]
)


def resolve_product_entities(
    products_std: pd.DataFrame,
    pair_decisions: pd.DataFrame,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Return the cluster labels and the golden records."""
    raise NotImplementedError
