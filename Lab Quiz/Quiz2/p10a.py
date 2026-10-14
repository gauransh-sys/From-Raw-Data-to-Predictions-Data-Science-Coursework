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


def standardize_product_records(
    frame: pd.DataFrame,
    category_aliases: dict[str, str],
) -> pd.DataFrame:
    """Return a standardized copy of the products table."""
    raise NotImplementedError
