import pandas as pd
from rapidfuzz.distance import Levenshtein


def choose_name_match(
    listing_name: str,
    candidate_a_id: str,
    candidate_b_id: str,
    products: pd.DataFrame
) -> float:

    product_a = products[
        products["product_id"] == candidate_a_id
    ].iloc[0]

    product_b = products[
        products["product_id"] == candidate_b_id
    ].iloc[0]

    sim_a = Levenshtein.normalized_similarity(
        listing_name,
        product_a["product_name"]
    )

    sim_b = Levenshtein.normalized_similarity(
        listing_name,
        product_b["product_name"]
    )

    if sim_a == sim_b:
        return 0.0

    if sim_a > sim_b:
        selected = product_a
    else:
        selected = product_b

    if (
        pd.isna(selected["unit_price"])
        or pd.isna(selected["weight_kg"])
        or selected["weight_kg"] == 0
    ):
        return 0.0

    return float(selected["unit_price"] / selected["weight_kg"])