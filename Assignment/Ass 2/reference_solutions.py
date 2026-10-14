from __future__ import annotations

import re
import unicodedata
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial import distance
from scipy.stats import zscore
from sklearn.covariance import MinCovDet
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, PowerTransformer, RobustScaler, StandardScaler

# IterativeImputer is still marked experimental in scikit-learn.
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer

from rapidfuzz.distance import JaroWinkler, Levenshtein


# -----------------------------------------------------------------------------
# Small compatibility helpers
# -----------------------------------------------------------------------------

def _simple_imputer(strategy: str) -> SimpleImputer:
    try:
        return SimpleImputer(strategy=strategy, keep_empty_features=True)
    except TypeError:  # older scikit-learn
        return SimpleImputer(strategy=strategy)


def _knn_imputer(k: int) -> KNNImputer:
    try:
        return KNNImputer(n_neighbors=k, keep_empty_features=True)
    except TypeError:
        return KNNImputer(n_neighbors=k)


def _one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _normalized_text(value: Any, lower: bool = False) -> Any:
    if pd.isna(value):
        return np.nan
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower() if lower else text


def _exact_agree(a: Any, b: Any) -> float:
    if pd.isna(a) or pd.isna(b):
        return np.nan
    return float(a == b)


# -----------------------------------------------------------------------------
# Part I — toolbox/library exercises
# -----------------------------------------------------------------------------
def profile_column(frame: pd.DataFrame, column: str) -> dict:
    s = frame[column]

    out = {
        "non_missing": int(s.notna().sum()),
        "missing": int(s.isna().sum()),
        "distinct": int(s.nunique(dropna=True)),
        "min": np.nan,
        "max": np.nan,
        "mean": np.nan,
        "median": np.nan,
        "q1": np.nan,
        "q3": np.nan,
    }

    non_missing = s.dropna()

    if len(non_missing) == 0:
        return out

    # Minimum and maximum are calculated normally.
    try:
        out["min"] = non_missing.min()
        out["max"] = non_missing.max()
    except (TypeError, ValueError):
        pass

    # Mean, median, and quartiles are defined only for numerical columns.
    if pd.api.types.is_numeric_dtype(s):
        out["mean"] = float(s.mean())
        out["median"] = float(s.median())
        out["q1"] = float(s.quantile(0.25))
        out["q3"] = float(s.quantile(0.75))

    return out

def top_category_frequencies(frame: pd.DataFrame, column: str, k: int) -> pd.DataFrame:
    counts = frame[column].dropna().value_counts()
    temp = counts.rename_axis("value").reset_index(name="count")
    temp["_sort"] = temp["value"].astype(str)
    temp = temp.sort_values(["count", "_sort"], ascending=[False, True], kind="mergesort")
    return temp.head(k).drop(columns="_sort").reset_index(drop=True)


def numeric_distances(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return float(distance.euclidean(x, y)), float(distance.cityblock(x, y))


def binary_similarities(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x).astype(bool)
    y = np.asarray(y).astype(bool)
    jaccard = 1.0 - float(distance.jaccard(x, y))
    nx = float(np.linalg.norm(x.astype(float)))
    ny = float(np.linalg.norm(y.astype(float)))
    if nx == 0 and ny == 0:
        cosine = 1.0
    elif nx == 0 or ny == 0:
        cosine = 0.0
    else:
        cosine = float(np.dot(x, y) / (nx * ny))
    return jaccard, cosine


def levenshtein_pair(a: str, b: str) -> tuple[int, float]:
    return int(Levenshtein.distance(a, b)), float(Levenshtein.normalized_similarity(a, b))


def jaro_winkler_pair(a: str, b: str) -> float:
    return float(JaroWinkler.normalized_similarity(a, b))


def token_set_jaccard(a: str, b: str) -> float:
    A = {tok for tok in re.split(r"\s+", a.lower().strip()) if tok}
    B = {tok for tok in re.split(r"\s+", b.lower().strip()) if tok}
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    return float(len(A & B) / len(A | B))


def simple_imputation_library(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    X = np.asarray(X, dtype=float)
    mean_imp = _simple_imputer("mean").fit_transform(X)
    median_imp = _simple_imputer("median").fit_transform(X)
    return np.asarray(mean_imp, dtype=float), np.asarray(median_imp, dtype=float)


def knn_imputation_library(X: np.ndarray, k: int) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    return np.asarray(_knn_imputer(k).fit_transform(X), dtype=float)

def univariate_outlier_helpers(x: np.ndarray) -> dict:

    x = np.asarray(x, dtype=float)
    observed = np.isfinite(x)

    # Ordinary z-scores
    z = np.full_like(x, np.nan, dtype=float)

    if observed.any():
        mean = np.mean(x[observed])
        std = np.std(x[observed])

        if std > 0:
            z[observed] = (x[observed] - mean) / std
        else:
            z[observed] = 0.0

    # Modified z-scores
    modified = np.full_like(x, np.nan, dtype=float)

    if observed.any():
        med = np.median(x[observed])
        mad = np.median(np.abs(x[observed] - med))

        if mad > 0:
            modified[observed] = (
                0.6745 * (x[observed] - med) / mad
            )
        else:
            modified[observed] = 0.0
    else:
        med = np.nan
        mad = np.nan

    # Tukey fences
    if observed.any():
        q1 = np.quantile(x[observed], 0.25)
        q3 = np.quantile(x[observed], 0.75)

        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
    else:
        lower = np.nan
        upper = np.nan

    return {
        "z": z,
        "modified_z": modified,
        "iqr_lower": float(lower),
        "iqr_upper": float(upper),
    }


def multivariate_outlier_scores(X: np.ndarray, n_neighbors: int) -> dict:
    X = np.asarray(X, dtype=float)
    Xi = _simple_imputer("median").fit_transform(X)
    mu = Xi.mean(axis=0)
    cov = np.cov(Xi, rowvar=False)
    cov = np.atleast_2d(cov)
    inv = np.linalg.pinv(cov)
    dif = Xi - mu
    mahal_sq = np.einsum("ij,jk,ik->i", dif, inv, dif)
    mahal = np.sqrt(np.maximum(mahal_sq, 0.0))
    lof_model = LocalOutlierFactor(n_neighbors=int(n_neighbors))
    lof_model.fit_predict(Xi)
    lof = -lof_model.negative_outlier_factor_
    return {"mahalanobis": mahal.astype(float), "lof": lof.astype(float)}


def transformation_library_bundle(X: np.ndarray) -> dict:
    X = np.asarray(X, dtype=float)
    Xi = _simple_imputer("median").fit_transform(X)
    return {
        "minmax": MinMaxScaler().fit_transform(Xi),
        "zscore": StandardScaler().fit_transform(Xi),
        "robust": RobustScaler().fit_transform(Xi),
        "yeojohnson": PowerTransformer(method="yeo-johnson", standardize=False).fit_transform(Xi),
    }


# -----------------------------------------------------------------------------
# Part II — integrated database cleaning
# -----------------------------------------------------------------------------

def build_database_profile(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    contacts: pd.DataFrame,
    params: dict,
) -> dict:
    tables = {"customers": customers, "transactions": transactions, "contacts": contacts}
    table_rows = {name: int(len(df)) for name, df in tables.items()}
    missing_counts = {name: {c: int(df[c].isna().sum()) for c in df.columns} for name, df in tables.items()}
    distinct_counts = {name: {c: int(df[c].nunique(dropna=True)) for c in df.columns} for name, df in tables.items()}
    exact_duplicate_counts = {name: int(df.duplicated().sum()) for name, df in tables.items()}

    valid_age = params.get("valid_age_range", [0, 120])
    age = pd.to_numeric(customers.get("age"), errors="coerce")
    bad_age = customers.index[age.notna() & ~age.between(valid_age[0], valid_age[1])].to_numpy(int)

    bad_customer_dates = np.zeros(len(customers), dtype=bool)
    for col in ["dob", "signup_date"]:
        if col in customers:
            s = customers[col]
            bad_customer_dates |= s.notna().to_numpy() & pd.to_datetime(s, errors="coerce").isna().to_numpy()

    email_regex = re.compile(params.get("valid_email_regex", r"^[^\s@]+@[^\s@]+\.[^\s@]+$"))
    if "email" in customers:
        email = customers["email"]
        bad_email = email.notna() & ~email.map(
            lambda x: bool(email_regex.match(str(x).strip())) if pd.notna(x) else False
        )
    else:
        bad_email = pd.Series(False, index=customers.index)

    invalid_customer_rows = np.unique(np.concatenate([
        bad_age,
        customers.index[bad_customer_dates].to_numpy(int),
        customers.index[bad_email].to_numpy(int),
    ])).astype(int)

    bad_tx = np.zeros(len(transactions), dtype=bool)
    if "amount" in transactions:
        amt = pd.to_numeric(transactions["amount"], errors="coerce")
        bad_tx |= (amt.notna() & (amt < 0)).to_numpy()
    if "transaction_date" in transactions:
        s = transactions["transaction_date"]
        bad_tx |= s.notna().to_numpy() & pd.to_datetime(s, errors="coerce").isna().to_numpy()
    invalid_transaction_rows = transactions.index[bad_tx].to_numpy(int)

    customer_ids = set(customers["customer_id"].dropna().astype(str))
    tx_fk = transactions.index[~transactions["customer_id"].astype(str).isin(customer_ids)].to_numpy(int)
    contact_fk = contacts.index[~contacts["customer_id"].astype(str).isin(customer_ids)].to_numpy(int)

    return {
        "table_rows": table_rows,
        "missing_counts": missing_counts,
        "distinct_counts": distinct_counts,
        "exact_duplicate_counts": exact_duplicate_counts,
        "invalid_customer_rows": np.sort(invalid_customer_rows),
        "invalid_transaction_rows": np.sort(invalid_transaction_rows),
        "foreign_key_violations": {
            "transactions": np.sort(tx_fk),
            "contacts": np.sort(contact_fk),
        },
    }


def standardize_customer_records(frame: pd.DataFrame, city_aliases: dict[str, str]) -> pd.DataFrame:
    out = frame.copy(deep=True)
    alias_map = {str(k).strip().lower(): v for k, v in city_aliases.items()}

    if "name" in out:
        out["name"] = out["name"].map(lambda v: _normalized_text(v, lower=True))
    if "email" in out:
        out["email"] = out["email"].map(lambda v: _normalized_text(v, lower=True))
    if "phone" in out:
        def phone_norm(v: Any) -> Any:
            if pd.isna(v):
                return np.nan
            digits = re.sub(r"\D", "", unicodedata.normalize("NFKC", str(v)))
            return digits[-10:] if digits else np.nan
        out["phone"] = out["phone"].map(phone_norm)
    if "city" in out:
        def city_norm(v: Any) -> Any:
            if pd.isna(v):
                return np.nan
            text = _normalized_text(v, lower=False)
            return alias_map.get(str(text).strip().lower(), str(text).strip())
        out["city"] = out["city"].map(city_norm)
    for col in ["dob", "signup_date"]:
        if col in out:
            parsed = pd.to_datetime(out[col], errors="coerce")
            out[col] = parsed.dt.strftime("%Y-%m-%d")
            out.loc[parsed.isna(), col] = np.nan
    return out


def generate_candidate_pairs(customers_std: pd.DataFrame) -> np.ndarray:
    pairs: set[tuple[int, int]] = set()

    # Pass 1: same canonical city and same birth year.
    dob = pd.to_datetime(customers_std.get("dob"), errors="coerce")
    years = dob.dt.year
    groups: dict[tuple[str, int], list[int]] = {}
    for i in range(len(customers_std)):
        city = customers_std.iloc[i].get("city", np.nan)
        year = years.iloc[i] if i < len(years) else np.nan
        if pd.isna(city) or pd.isna(year):
            continue
        groups.setdefault((str(city), int(year)), []).append(i)
    for members in groups.values():
        for a, b in combinations(members, 2):
            pairs.add((min(a, b), max(a, b)))

    # Pass 2: same final four phone digits.
    groups2: dict[str, list[int]] = {}
    if "phone" in customers_std:
        for i, v in enumerate(customers_std["phone"].tolist()):
            if pd.isna(v):
                continue
            digits = re.sub(r"\D", "", str(v))
            if len(digits) >= 4:
                groups2.setdefault(digits[-4:], []).append(i)
    for members in groups2.values():
        for a, b in combinations(members, 2):
            pairs.add((min(a, b), max(a, b)))

    if not pairs:
        return np.empty((0, 2), dtype=int)
    return np.asarray(sorted(pairs), dtype=int)


def compare_candidate_pairs(customers_std: pd.DataFrame, pairs: np.ndarray) -> pd.DataFrame:
    rows = []
    for a, b in np.asarray(pairs, dtype=int):
        ra = customers_std.iloc[int(a)]
        rb = customers_std.iloc[int(b)]

        if pd.isna(ra.get("name")) or pd.isna(rb.get("name")):
            name_sim = np.nan
        else:
            name_sim = float(JaroWinkler.normalized_similarity(str(ra["name"]), str(rb["name"])))

        if pd.isna(ra.get("email")) or pd.isna(rb.get("email")):
            email_sim = np.nan
        else:
            email_sim = float(Levenshtein.normalized_similarity(str(ra["email"]), str(rb["email"])))

        rows.append({
            "i": int(a),
            "j": int(b),
            "name_sim": name_sim,
            "email_sim": email_sim,
            "phone_agree": _exact_agree(ra.get("phone"), rb.get("phone")),
            "city_agree": _exact_agree(ra.get("city"), rb.get("city")),
            "dob_agree": _exact_agree(ra.get("dob"), rb.get("dob")),
        })
    return pd.DataFrame(rows, columns=["i", "j", "name_sim", "email_sim", "phone_agree", "city_agree", "dob_agree"])


def classify_candidate_pairs(
    comparisons: pd.DataFrame,
    weights: dict[str, float],
    lower_threshold: float,
    upper_threshold: float,
) -> pd.DataFrame:
    fields = ["name_sim", "email_sim", "phone_agree", "city_agree", "dob_agree"]
    scores = []
    decisions = []
    for _, row in comparisons.iterrows():
        num = 0.0
        den = 0.0
        for f in fields:
            val = row.get(f, np.nan)
            if pd.notna(val) and f in weights:
                w = float(weights[f])
                num += w * float(val)
                den += w
        score = num / den if den > 0 else np.nan
        scores.append(score)
        if not np.isfinite(score):
            decisions.append("review")
        elif score >= upper_threshold:
            decisions.append("match")
        elif score < lower_threshold:
            decisions.append("nonmatch")
        else:
            decisions.append("review")
    return pd.DataFrame({
        "i": comparisons["i"].astype(int).to_numpy(),
        "j": comparisons["j"].astype(int).to_numpy(),
        "score": np.asarray(scores, dtype=float),
        "decision": decisions,
    })


def resolve_customer_entities(
    customers_std: pd.DataFrame,
    pair_decisions: pd.DataFrame,
) -> tuple[np.ndarray, pd.DataFrame]:
    n = len(customers_std)
    parent = np.arange(n, dtype=int)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = int(parent[x])
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if ra < rb:
            parent[rb] = ra
        else:
            parent[ra] = rb

    for _, r in pair_decisions.iterrows():
        if r["decision"] == "match":
            union(int(r["i"]), int(r["j"]))

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    components = sorted(groups.values(), key=lambda g: min(g))

    labels = np.empty(n, dtype=int)
    golden_rows = []
    for label, members in enumerate(components):
        labels[members] = label
        sub = customers_std.iloc[members]
        record: dict[str, Any] = {}
        for col in customers_std.columns:
            s = sub[col]
            if pd.api.types.is_numeric_dtype(s):
                vals = pd.to_numeric(s, errors="coerce")
                record[col] = float(vals.median()) if vals.notna().any() else np.nan
            else:
                vals = s.dropna().astype(str)
                if len(vals) == 0:
                    record[col] = np.nan
                else:
                    vc = vals.value_counts()
                    max_count = int(vc.max())
                    candidates = [v for v, c in vc.items() if int(c) == max_count]
                    candidates.sort(key=lambda v: (-len(v), v))
                    record[col] = candidates[0]
        record["cluster_size"] = int(len(members))
        record["source_row_ids"] = list(map(int, members))
        golden_rows.append(record)

    golden = pd.DataFrame(golden_rows)
    return labels, golden


def missingness_diagnostics(
    frame: pd.DataFrame,
    target_column: str,
    conditioning_columns: list[str],
) -> pd.DataFrame:
    target_missing = frame[target_column].isna()
    rows = []
    for col in conditioning_columns:
        s = frame[col]
        numeric = pd.to_numeric(s, errors="coerce")
        if numeric.notna().sum() == s.notna().sum() and s.notna().sum() > 0:
            a = numeric[target_missing].mean()
            b = numeric[~target_missing].mean()
            value = float(a - b) if pd.notna(a) and pd.notna(b) else np.nan
            statistic = "mean_difference"
        else:
            tmp = pd.DataFrame({"cond": s, "target_missing": target_missing}).dropna(subset=["cond"])
            if len(tmp) == 0:
                value = np.nan
            else:
                rates = tmp.groupby("cond", dropna=False)["target_missing"].mean()
                value = float(rates.max() - rates.min()) if len(rates) else np.nan
            statistic = "target_missing_rate_range"
        rows.append({"conditioning_column": col, "statistic": statistic, "value": value})
    return pd.DataFrame(rows).sort_values("conditioning_column").reset_index(drop=True)


def evaluate_imputation_methods(
    X_complete_subset: np.ndarray,
    evaluation_mask: np.ndarray,
    k: int,
    random_state: int,
) -> pd.DataFrame:
    X = np.asarray(X_complete_subset, dtype=float)
    mask = np.asarray(evaluation_mask, dtype=bool)
    if X.shape != mask.shape:
        raise ValueError("evaluation_mask must have the same shape as X_complete_subset")
    Xmasked = X.copy()
    Xmasked[mask] = np.nan

    methods = {
        "KNN": _knn_imputer(k).fit_transform(Xmasked),
        "ITERATIVE": IterativeImputer(random_state=random_state, max_iter=10).fit_transform(Xmasked),
        "MEDIAN": _simple_imputer("median").fit_transform(Xmasked),
    }
    out = []
    for method, Xi in methods.items():
        Xi = np.asarray(Xi, dtype=float)
        for j in range(X.shape[1]):
            m = mask[:, j]
            rmse = float(np.sqrt(np.mean((Xi[m, j] - X[m, j]) ** 2))) if m.any() else np.nan
            out.append({"method": method, "column": str(j), "rmse": rmse})
        if mask.any():
            overall = float(np.sqrt(np.mean((Xi[mask] - X[mask]) ** 2)))
        else:
            overall = np.nan
        out.append({"method": method, "column": "OVERALL", "rmse": overall})
    return pd.DataFrame(out).sort_values(["method", "column"]).reset_index(drop=True)


def build_imputation_audit(
    original: pd.DataFrame,
    imputed: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    augmented = imputed.copy(deep=True)
    audit_rows = []
    for col in columns:
        was_missing = original[col].isna()
        augmented[f"{col}_was_missing"] = was_missing.to_numpy(bool)
        for idx in original.index[was_missing]:
            audit_rows.append({
                "row_index": int(idx),
                "column": col,
                "old_value": original.at[idx, col],
                "new_value": imputed.at[idx, col],
            })
    audit = pd.DataFrame(audit_rows, columns=["row_index", "column", "old_value", "new_value"])
    if len(audit):
        audit = audit.sort_values(["row_index", "column"]).reset_index(drop=True)
    return augmented, audit


def detect_database_outliers(
    customers_numeric: pd.DataFrame,
    transaction_amounts: pd.Series,
    contamination: float,
    n_neighbors: int,
) -> dict:
    X = customers_numeric.apply(pd.to_numeric, errors="coerce").to_numpy(float)
    Xi = _simple_imputer("median").fit_transform(X)

    med = np.median(Xi, axis=0)
    mad = np.median(np.abs(Xi - med), axis=0)
    modified = np.zeros_like(Xi, dtype=float)
    nonzero = mad > 0
    modified[:, nonzero] = 0.6745 * (Xi[:, nonzero] - med[nonzero]) / mad[nonzero]
    customer_mad_flags = np.abs(modified) > 3.5

    q1 = np.quantile(Xi, 0.25, axis=0)
    q3 = np.quantile(Xi, 0.75, axis=0)
    iqr = q3 - q1
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    customer_iqr_flags = (Xi < lo) | (Xi > hi)

    tx = pd.to_numeric(transaction_amounts, errors="coerce").to_numpy(float)
    obs = np.isfinite(tx)
    tx_med = np.nanmedian(tx)
    tx_mad = np.nanmedian(np.abs(tx - tx_med))
    tx_mad_flags = np.zeros(len(tx), dtype=bool)
    if np.isfinite(tx_mad) and tx_mad > 0:
        tx_mod = np.full(len(tx), np.nan)
        tx_mod[obs] = 0.6745 * (tx[obs] - tx_med) / tx_mad
        tx_mad_flags[obs] = np.abs(tx_mod[obs]) > 3.5
    tq1, tq3 = np.nanquantile(tx, [0.25, 0.75])
    tiqr = tq3 - tq1
    tx_iqr_flags = np.zeros(len(tx), dtype=bool)
    tx_iqr_flags[obs] = (tx[obs] < tq1 - 1.5 * tiqr) | (tx[obs] > tq3 + 1.5 * tiqr)

    # Remove constant columns for robust covariance and LOF.
    keep = np.nanstd(Xi, axis=0) > 0
    Xk = Xi[:, keep] if keep.any() else np.zeros((len(Xi), 1), dtype=float)
    try:
        mcd = MinCovDet().fit(Xk)
        mahal = np.sqrt(np.maximum(mcd.mahalanobis(Xk), 0.0))
    except Exception:
        mu = Xk.mean(axis=0)
        cov = np.atleast_2d(np.cov(Xk, rowvar=False))
        inv = np.linalg.pinv(cov)
        d = Xk - mu
        mahal = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", d, inv, d), 0.0))

    nn = max(2, min(int(n_neighbors), max(2, len(Xk) - 1)))
    lof_model = LocalOutlierFactor(n_neighbors=nn, contamination=contamination)
    lof_model.fit_predict(Xk)
    lof = -lof_model.negative_outlier_factor_

    return {
        "customer_mad_flags": customer_mad_flags,
        "customer_iqr_flags": customer_iqr_flags,
        "transaction_mad_flags": tx_mad_flags,
        "transaction_iqr_flags": tx_iqr_flags,
        "mahalanobis_scores": np.asarray(mahal, dtype=float),
        "lof_scores": np.asarray(lof, dtype=float),
    }


def build_model_ready_matrices(
    frame: pd.DataFrame,
    numeric_columns: list[str],
    categorical_columns: list[str],
    train_indices: np.ndarray,
    test_indices: np.ndarray,
) -> dict:
    train = frame.iloc[np.asarray(train_indices, dtype=int)]
    test = frame.iloc[np.asarray(test_indices, dtype=int)]

    num_train_raw = train[numeric_columns].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    num_test_raw = test[numeric_columns].apply(pd.to_numeric, errors="coerce").to_numpy(float)

    imp = _simple_imputer("median")
    num_train = imp.fit_transform(num_train_raw)
    num_test = imp.transform(num_test_raw)
    medians = np.asarray(imp.statistics_, dtype=float)

    # Two deterministic engineered features after imputation.
    train_row_mean = np.mean(num_train, axis=1, keepdims=True)
    test_row_mean = np.mean(num_test, axis=1, keepdims=True)
    if num_train.shape[1] >= 2:
        train_interaction = (num_train[:, [0]] * num_train[:, [1]])
        test_interaction = (num_test[:, [0]] * num_test[:, [1]])
    else:
        train_interaction = num_train[:, [0]] ** 2
        test_interaction = num_test[:, [0]] ** 2
    num_train_aug = np.hstack([num_train, train_row_mean, train_interaction])
    num_test_aug = np.hstack([num_test, test_row_mean, test_interaction])

    scaler = StandardScaler()
    num_train_scaled = scaler.fit_transform(num_train_aug)
    num_test_scaled = scaler.transform(num_test_aug)

    # Categorical fill values learned only from training rows.
    cat_train = train[categorical_columns].copy()
    cat_test = test[categorical_columns].copy()
    for col in categorical_columns:
        mode = cat_train[col].dropna().mode()
        fill = str(mode.iloc[0]) if len(mode) else "__MISSING__"
        cat_train[col] = cat_train[col].astype(object).where(cat_train[col].notna(), fill).astype(str)
        cat_test[col] = cat_test[col].astype(object).where(cat_test[col].notna(), fill).astype(str)

    enc = _one_hot_encoder()
    cat_train_enc = enc.fit_transform(cat_train)
    cat_test_enc = enc.transform(cat_test)

    X_train = np.hstack([num_train_scaled, np.asarray(cat_train_enc, dtype=float)])
    X_test = np.hstack([num_test_scaled, np.asarray(cat_test_enc, dtype=float)])

    num_names = list(numeric_columns) + ["constructed__row_mean", "constructed__interaction_0_1"]
    cat_names = list(enc.get_feature_names_out(categorical_columns))
    feature_names = num_names + cat_names

    return {
        "X_train": X_train,
        "X_test": X_test,
        "feature_names": feature_names,
        "train_medians": {c: float(v) for c, v in zip(numeric_columns, medians)},
        "train_scaler_center": np.asarray(scaler.mean_, dtype=float),
    }


def summarize_cleaning_audit(
    baseline_profile: dict,
    candidate_pairs: np.ndarray,
    pair_decisions: pd.DataFrame,
    golden_records: pd.DataFrame,
    imputation_audit: pd.DataFrame,
    outlier_results: dict,
    model_matrix_info: dict,
) -> dict:
    baseline_rows = int(sum(baseline_profile.get("table_rows", {}).values()))
    match_count = int((pair_decisions["decision"] == "match").sum()) if len(pair_decisions) else 0
    review_count = int((pair_decisions["decision"] == "review").sum()) if len(pair_decisions) else 0

    cust_mad = np.asarray(outlier_results.get("customer_mad_flags", []), dtype=bool)
    cust_iqr = np.asarray(outlier_results.get("customer_iqr_flags", []), dtype=bool)
    tx_mad = np.asarray(outlier_results.get("transaction_mad_flags", []), dtype=bool)
    tx_iqr = np.asarray(outlier_results.get("transaction_iqr_flags", []), dtype=bool)
    cust_rows = 0
    tx_rows = 0
    if cust_mad.size or cust_iqr.size:
        a = cust_mad.any(axis=1) if cust_mad.ndim == 2 else cust_mad
        b = cust_iqr.any(axis=1) if cust_iqr.ndim == 2 else cust_iqr
        cust_rows = int(np.logical_or(a, b).sum())
    if tx_mad.size or tx_iqr.size:
        tx_rows = int(np.logical_or(tx_mad, tx_iqr).sum())

    feature_names = model_matrix_info.get("feature_names", [])
    return {
        "baseline_rows": baseline_rows,
        "candidate_pair_count": int(len(candidate_pairs)),
        "match_pair_count": match_count,
        "review_pair_count": review_count,
        "golden_entity_count": int(len(golden_records)),
        "imputed_cell_count": int(len(imputation_audit)),
        "flagged_outlier_count": int(cust_rows + tx_rows),
        "model_feature_count": int(len(feature_names)),
    }
