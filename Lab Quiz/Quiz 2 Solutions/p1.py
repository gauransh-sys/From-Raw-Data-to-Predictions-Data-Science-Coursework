import pandas as pd


def dominant_category(frame: pd.DataFrame) -> str:
    counts = frame["category"].dropna().value_counts()

    if counts.empty:
        return None

    max_count = counts.max()
    candidates = counts[counts == max_count].index

    return min(candidates)