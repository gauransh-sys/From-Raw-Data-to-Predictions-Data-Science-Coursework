
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


def _modal_string(values):
    """Most frequent non-missing value; ties -> longer, then lexicographic."""
    counts = {}
    for value in values:
        if pd.isna(value):
            continue
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return np.nan
    best = max(counts.values())
    tied = [k for k, c in counts.items() if c == best]
    return sorted(tied, key=lambda s: (-len(s), s))[0]


def resolve_product_entities(
    products_std: pd.DataFrame,
    pair_decisions: pd.DataFrame,
) -> tuple[np.ndarray, pd.DataFrame]:
    n = len(products_std)

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    if len(pair_decisions) > 0:
        matched = pair_decisions.loc[
            pair_decisions["decision"] == "match", ["i", "j"]
        ]
        for i, j in matched.to_numpy().reshape(-1, 2):
            ri, rj = find(int(i)), find(int(j))
            if ri != rj:
                parent[max(ri, rj)] = min(ri, rj)

    members = {}
    for row in range(n):
        members.setdefault(find(row), []).append(row)

    # Components are numbered by the smallest row index they contain.
    roots = sorted(members, key=lambda r: members[r][0])
    label_of_root = {root: label for label, root in enumerate(roots)}

    cluster_labels = np.array(
        [label_of_root[find(row)] for row in range(n)], dtype=int
    )

    records = []
    for label, root in enumerate(roots):
        rows = members[root]
        block = products_std.iloc[rows]
        source_ids = sorted(str(v) for v in block["product_id"])

        record = {"entity_id": label, "product_id": source_ids[0]}
        for column in STRING_COLUMNS:
            record[column] = _modal_string(block[column].tolist())
        for column in NUMERIC_COLUMNS:
            numeric = pd.to_numeric(block[column], errors="coerce").dropna()
            record[column] = (
                np.nan if numeric.empty else float(numeric.median())
            )
        record["cluster_size"] = len(rows)
        record["source_product_ids"] = ",".join(source_ids)
        records.append(record)

    if records:
        golden_records = pd.DataFrame(records, columns=GOLDEN_COLUMNS)
    else:
        golden_records = pd.DataFrame(
            {c: pd.Series([], dtype=object) for c in GOLDEN_COLUMNS}
        )

    return cluster_labels, golden_records
