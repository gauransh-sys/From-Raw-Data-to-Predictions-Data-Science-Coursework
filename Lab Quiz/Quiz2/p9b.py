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


def impute_contextually(
    products: pd.DataFrame,
    orders: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return the imputed products, imputed orders, and audit table."""
    raise NotImplementedError
