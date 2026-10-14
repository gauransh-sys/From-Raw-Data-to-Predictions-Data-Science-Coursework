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


def detect_contextual_outliers(
    products: pd.DataFrame,
    listings: pd.DataFrame,
) -> pd.DataFrame:
    """Return the contextual outlier table."""
    raise NotImplementedError
