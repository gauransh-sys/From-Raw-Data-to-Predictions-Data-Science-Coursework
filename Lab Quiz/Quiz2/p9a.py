import numpy as np
import pandas as pd


def build_missingness_and_validity_report(
    products: pd.DataFrame,
    orders: pd.DataFrame,
    listings: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Return the validity report and cleaned copies of the three tables."""
    raise NotImplementedError
