from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2010
OUTDIR = Path(__file__).resolve().parent
REFERENCE_DATE = pd.Timestamp("2026-01-01")

CANONICAL_CITIES = [
    "Bengaluru", "Chennai", "Delhi", "Hyderabad", "Kolkata", "Mumbai",
    "Pune", "Jaipur", "Kochi", "Ahmedabad", "Lucknow", "Bhopal"
]

CITY_VARIANTS = {
    "Bengaluru": ["Bengaluru", "Bangalore", "BENGALURU", "Bengluru", " Bangalore "],
    "Chennai": ["Chennai", "Madras", "CHENNAI", "Chennai ", "Chenai"],
    "Delhi": ["Delhi", "New Delhi", "DELHI", " Delhi ", "Dilli"],
    "Hyderabad": ["Hyderabad", "HYDERABAD", "Hyd", "Hyderbad"],
    "Kolkata": ["Kolkata", "Calcutta", "KOLKATA", "Kolkata ", "Kolkatta"],
    "Mumbai": ["Mumbai", "Bombay", "MUMBAI", " Mumbai ", "Mumbay"],
    "Pune": ["Pune", "Poona", "PUNE", " Pune ", "Puna"],
    "Jaipur": ["Jaipur", "JAIPUR", " Jaipur ", "Jaypur"],
    "Kochi": ["Kochi", "Cochin", "KOCHI", " Kochi ", "Kochin"],
    "Ahmedabad": ["Ahmedabad", "Ahemdabad", "AHMEDABAD", " Ahmedabad "],
    "Lucknow": ["Lucknow", "LUCKNOW", " Lucknow ", "Lakhnau"],
    "Bhopal": ["Bhopal", "BHOPAL", " Bhopal ", "Bhopl"],
}

CITY_ALIASES = {
    alias.strip().lower(): canonical
    for canonical, aliases in CITY_VARIANTS.items()
    for alias in aliases
}

FIRST_NAMES = [
    "Aarav", "Aditi", "Aditya", "Akshay", "Ananya", "Anika", "Arjun", "Diya",
    "Ishaan", "Ishita", "Kabir", "Kavya", "Krishna", "Meera", "Mira", "Nikhil",
    "Nisha", "Pooja", "Pranav", "Priya", "Rahul", "Rhea", "Rohan", "Saanvi",
    "Sahil", "Sanjay", "Shreya", "Sneha", "Tanvi", "Varun", "Vikram", "Zoya"
]

LAST_NAMES = [
    "Agarwal", "Banerjee", "Bose", "Chandra", "Das", "Desai", "Gupta", "Iyer",
    "Jain", "Joshi", "Kapoor", "Khan", "Kulkarni", "Mehta", "Menon", "Mishra",
    "Mukherjee", "Nair", "Patel", "Rao", "Reddy", "Roy", "Sen", "Shah",
    "Sharma", "Singh", "Sinha", "Subramanian", "Tiwari", "Verma"
]

CHANNELS = ["online", "store", "mobile", "phone"]
SOURCES = ["crm", "support", "marketing", "branch"]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", ".", s.lower()).strip(".")


def _age_from_dob(dob: pd.Timestamp) -> int:
    return int((REFERENCE_DATE - dob).days // 365.2425)


def _format_phone(phone: str, rng: np.random.Generator) -> str:
    r = rng.random()
    if r < 0.20:
        return phone
    if r < 0.40:
        return f"+91 {phone[:5]} {phone[5:]}"
    if r < 0.60:
        return f"91-{phone[:3]}-{phone[3:6]}-{phone[6:]}"
    if r < 0.80:
        return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
    return f" {phone[:5]}-{phone[5:]} "


def _name_variant(name: str, rng: np.random.Generator) -> str:
    first, last = name.split(" ", 1)
    mode = int(rng.integers(0, 6))
    if mode == 0:
        return f"{first[0]}. {last}"
    if mode == 1 and len(first) > 3:
        pos = int(rng.integers(1, len(first) - 1))
        return first[:pos] + first[pos + 1 :] + " " + last
    if mode == 2:
        return f"{first} {last[0]}."
    if mode == 3:
        return f"  {first.lower()}   {last.lower()}  "
    if mode == 4 and len(last) > 3:
        pos = int(rng.integers(1, len(last) - 1))
        last2 = last[:pos] + last[pos + 1 :]
        return f"{first} {last2}"
    return name.upper()


def _email_variant(email: str, rng: np.random.Generator) -> str:
    local, domain = email.split("@")
    mode = int(rng.integers(0, 5))
    if mode == 0:
        return email.upper()
    if mode == 1:
        return f" {email} "
    if mode == 2 and len(local) > 5:
        pos = int(rng.integers(1, len(local) - 1))
        local = local[:pos] + local[pos + 1 :]
        return f"{local}@{domain}"
    if mode == 3:
        return f"{local.replace('.', '')}@{domain}"
    return email


def _generate_customers(rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    n_entities = 5600
    rows = []
    entity_ids = []

    start = pd.Timestamp("1950-01-01")
    end = pd.Timestamp("2005-12-31")
    day_span = (end - start).days

    for i in range(n_entities):
        first = FIRST_NAMES[int(rng.integers(len(FIRST_NAMES)))]
        last = LAST_NAMES[int(rng.integers(len(LAST_NAMES)))]
        name = f"{first} {last}"
        dob = start + pd.Timedelta(days=int(rng.integers(day_span + 1)))
        age = _age_from_dob(dob)
        city = str(rng.choice(CANONICAL_CITIES))
        phone = f"{int(rng.integers(6000000000, 9999999999)):010d}"
        email = f"{_slug(name)}.{i:04d}@example.in"
        income = float(np.round(np.exp(rng.normal(np.log(850000), 0.65)), -2))
        household = int(rng.integers(1, 8))
        signup = pd.Timestamp("2015-01-01") + pd.Timedelta(days=int(rng.integers(0, 4018)))
        rows.append({
            "customer_id": f"C{i:06d}",
            "name": name,
            "dob": dob.strftime("%Y-%m-%d"),
            "age": age,
            "city": city,
            "phone": phone,
            "email": email,
            "annual_income": income,
            "household_size": household,
            "signup_date": signup.strftime("%Y-%m-%d"),
        })
        entity_ids.append(f"E{i:06d}")

    base = pd.DataFrame(rows)

    # Add 680 near-duplicate entity records.
    dup_sources = rng.choice(n_entities, size=680, replace=False)
    dup_rows = []
    dup_entity_ids = []
    for j, src_idx in enumerate(dup_sources):
        r = base.iloc[int(src_idx)].copy()
        r["customer_id"] = f"C{n_entities + j:06d}"
        r["name"] = _name_variant(str(r["name"]), rng)
        r["city"] = str(rng.choice(CITY_VARIANTS[str(r["city"])]))
        r["phone"] = _format_phone(str(r["phone"]), rng)
        r["email"] = _email_variant(str(r["email"]), rng)
        if rng.random() < 0.12:
            d = pd.Timestamp(r["dob"]) + pd.Timedelta(days=int(rng.choice([-1, 1, 7, -7])))
            r["dob"] = d.strftime("%Y-%m-%d")
        if rng.random() < 0.20:
            r["annual_income"] = float(np.round(float(r["annual_income"]) * rng.normal(1.0, 0.03), -2))
        dup_rows.append(r)
        dup_entity_ids.append(f"E{int(src_idx):06d}")

    full = pd.concat([base, pd.DataFrame(dup_rows)], ignore_index=True)
    entity_ids = np.asarray(entity_ids + dup_entity_ids, dtype="U16")

    # Add 20 exact duplicate rows (including customer_id) as explicit row duplicates.
    exact_sources = rng.choice(len(full), size=20, replace=False)
    exact = full.iloc[exact_sources].copy()
    exact_entities = entity_ids[exact_sources]
    full = pd.concat([full, exact], ignore_index=True)
    entity_ids = np.concatenate([entity_ids, exact_entities])

    # Canonical clean reference before corruptions below.
    clean = full.copy(deep=True)
    clean["city"] = [CITY_ALIASES.get(str(x).strip().lower(), str(x).strip()) for x in clean["city"]]
    clean["name"] = clean["name"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    clean["phone"] = clean["phone"].astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    clean["email"] = clean["email"].astype(str).str.strip().str.lower()

    dirty = full.copy(deep=True)

    # Field-level formatting/canonical variation, not limited to duplicated entities.
    for idx in rng.choice(len(dirty), size=int(0.22 * len(dirty)), replace=False):
        canonical = clean.at[idx, "city"]
        dirty.at[idx, "city"] = str(rng.choice(CITY_VARIANTS[canonical]))
    for idx in rng.choice(len(dirty), size=int(0.18 * len(dirty)), replace=False):
        dirty.at[idx, "phone"] = _format_phone(str(clean.at[idx, "phone"]), rng)
    for idx in rng.choice(len(dirty), size=int(0.05 * len(dirty)), replace=False):
        dirty.at[idx, "name"] = _name_variant(str(clean.at[idx, "name"]), rng)
    for idx in rng.choice(len(dirty), size=int(0.04 * len(dirty)), replace=False):
        dirty.at[idx, "email"] = _email_variant(str(clean.at[idx, "email"]), rng)

    # Invalid ages and outlying but not necessarily invalid incomes.
    invalid_age_idx = rng.choice(len(dirty), size=18, replace=False)
    dirty.loc[invalid_age_idx[:9], "age"] = rng.choice([135, 145, 240], size=9)
    dirty.loc[invalid_age_idx[9:], "age"] = rng.choice([-8, -2, -1], size=9)

    income_outlier_idx = rng.choice(len(dirty), size=30, replace=False)
    dirty.loc[income_outlier_idx, "annual_income"] *= rng.uniform(12, 35, size=30)

    # A few malformed values.
    bad_email_idx = rng.choice(len(dirty), size=24, replace=False)
    dirty.loc[bad_email_idx[:12], "email"] = "not-an-email"
    dirty.loc[bad_email_idx[12:], "email"] = dirty.loc[bad_email_idx[12:], "email"].astype(str).str.replace("@", "", regex=False)

    bad_date_idx = rng.choice(len(dirty), size=14, replace=False)
    dirty.loc[bad_date_idx[:7], "signup_date"] = "31-31-2024"
    dirty.loc[bad_date_idx[7:], "dob"] = "not-a-date"

    # Missingness mechanisms.
    n = len(dirty)
    mcar_phone = rng.random(n) < 0.055
    # MAR: missing household size depends on observed city.
    mar_prob = np.where(clean["city"].isin(["Delhi", "Mumbai", "Kolkata"]), 0.16, 0.035)
    mar_household = rng.random(n) < mar_prob
    # MNAR: high-income people are more likely to omit income.
    clean_income = pd.to_numeric(clean["annual_income"], errors="coerce").to_numpy(float)
    q75 = float(np.nanquantile(clean_income, 0.75))
    mnar_prob = np.where(clean_income >= q75, 0.23, 0.035)
    mnar_income = rng.random(n) < mnar_prob
    # Extra light MCAR email missingness.
    mcar_email = rng.random(n) < 0.025

    dirty.loc[mcar_phone, "phone"] = np.nan
    dirty.loc[mar_household, "household_size"] = np.nan
    dirty.loc[mnar_income, "annual_income"] = np.nan
    dirty.loc[mcar_email, "email"] = np.nan

    masks = np.vstack([mcar_phone, mar_household, mnar_income, mcar_email]).T
    return dirty, clean, entity_ids, masks


def _generate_transactions(customers: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = 5200
    valid_ids = customers["customer_id"].dropna().astype(str).unique()
    cids = rng.choice(valid_ids, size=n, replace=True).astype(object)
    # Deliberate referential-integrity errors.
    fk_bad = rng.choice(n, size=18, replace=False)
    for k, idx in enumerate(fk_bad):
        cids[idx] = f"C_BAD_{k:03d}"

    dates = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 730, size=n), unit="D")
    amount = np.round(np.exp(rng.normal(np.log(1800), 0.95, size=n)), 2)
    negative_idx = rng.choice(n, size=22, replace=False)
    amount[negative_idx] *= -1
    high_idx = rng.choice(n, size=20, replace=False)
    amount[high_idx] *= rng.uniform(20, 80, size=20)

    discount = np.round(rng.beta(1.2, 8.0, size=n) * 0.5, 3)
    discount[rng.random(n) < 0.08] = np.nan

    frame = pd.DataFrame({
        "transaction_id": [f"T{i:07d}" for i in range(n)],
        "customer_id": cids,
        "transaction_date": dates.strftime("%Y-%m-%d"),
        "amount": amount,
        "channel": rng.choice(CHANNELS, size=n, p=[0.43, 0.32, 0.20, 0.05]),
        "merchant_city": rng.choice(CANONICAL_CITIES, size=n),
        "items": rng.integers(1, 12, size=n),
        "discount": discount,
    })
    bad_dates = rng.choice(n, size=9, replace=False)
    frame.loc[bad_dates, "transaction_date"] = "bad-date"
    return frame


def _generate_contacts(customers_clean: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = 3000
    src = rng.choice(len(customers_clean), size=n, replace=True)
    sample = customers_clean.iloc[src].reset_index(drop=True)
    out = pd.DataFrame({
        "contact_id": [f"K{i:06d}" for i in range(n)],
        "customer_id": sample["customer_id"].astype(object),
        "name": sample["name"].astype(object),
        "phone": sample["phone"].astype(object),
        "email": sample["email"].astype(object),
        "city": sample["city"].astype(object),
        "last_verified": (pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 1095, size=n), unit="D")).strftime("%Y-%m-%d"),
        "source": rng.choice(SOURCES, size=n),
    })
    for i in rng.choice(n, size=500, replace=False):
        out.at[i, "name"] = _name_variant(str(out.at[i, "name"]), rng)
    for i in rng.choice(n, size=700, replace=False):
        out.at[i, "phone"] = _format_phone(str(out.at[i, "phone"]), rng)
    for i in rng.choice(n, size=350, replace=False):
        out.at[i, "email"] = _email_variant(str(out.at[i, "email"]), rng)
    for i in rng.choice(n, size=450, replace=False):
        canonical = str(out.at[i, "city"])
        out.at[i, "city"] = str(rng.choice(CITY_VARIANTS[canonical]))
    bad_fk = rng.choice(n, size=12, replace=False)
    for k, idx in enumerate(bad_fk):
        out.at[idx, "customer_id"] = f"C_CONTACT_BAD_{k:03d}"
    # Some missing contact details.
    out.loc[rng.random(n) < 0.06, "phone"] = np.nan
    out.loc[rng.random(n) < 0.04, "email"] = np.nan
    return out


def _duplicate_pairs(entity_ids: np.ndarray) -> np.ndarray:
    groups: dict[str, list[int]] = {}
    for i, e in enumerate(entity_ids.tolist()):
        groups.setdefault(e, []).append(i)
    pairs = []
    for members in groups.values():
        if len(members) > 1:
            pairs.extend(combinations(members, 2))
    if not pairs:
        return np.empty((0, 2), dtype=int)
    return np.asarray(sorted(pairs), dtype=int)


def main() -> None:
    rng = np.random.default_rng(SEED)
    customers, customers_clean, entity_ids, missing_masks = _generate_customers(rng)
    transactions = _generate_transactions(customers, rng)
    contacts = _generate_contacts(customers_clean, rng)
    gold_pairs = _duplicate_pairs(entity_ids)

    customers.to_csv(OUTDIR / "customers.csv", index=False)
    transactions.to_csv(OUTDIR / "transactions.csv", index=False)
    contacts.to_csv(OUTDIR / "contacts.csv", index=False)

    # --------------------------------------------------------------
    # Student-visible arrays used as explicit task inputs.
    # --------------------------------------------------------------
    numeric_cols = ["age", "annual_income", "household_size"]
    model_numeric_cols = ["age", "annual_income", "household_size"]
    model_categorical_cols = ["city"]
    outlier_numeric_cols = ["age", "annual_income", "household_size"]

    numeric_clean = (
        customers_clean[numeric_cols]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(float)
    )
    numeric_dirty = (
        customers[numeric_cols]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(float)
    )

    # Part-I library practice matrix.
    toolbox_rows = rng.choice(len(customers), size=500, replace=False)
    toolbox_numeric_X = numeric_dirty[toolbox_rows].copy()

    # Fixed binary example for Task 4.
    toolbox_binary_x = np.asarray([1, 1, 0, 0, 0, 1, 0, 0], dtype=int)
    toolbox_binary_y = np.asarray([1, 0, 1, 0, 0, 1, 0, 0], dtype=int)

    # Task 20: a complete matrix plus a separate evaluation mask.
    # This exposes only a selected evaluation subset, not the full clean table.
    eval_rows = rng.choice(len(customers_clean), size=1200, replace=False)
    imputation_complete_subset = numeric_clean[eval_rows].copy()
    imputation_evaluation_mask = (
        rng.random(imputation_complete_subset.shape) < 0.10
    )

    # Guarantee enough masked cells per column.
    for j in range(imputation_evaluation_mask.shape[1]):
        if imputation_evaluation_mask[:, j].sum() < 25:
            chosen = rng.choice(
                imputation_evaluation_mask.shape[0],
                size=25,
                replace=False,
            )
            imputation_evaluation_mask[chosen, j] = True

    # Task 23: one fixed 80/20 split supplied to students.
    perm = rng.permutation(len(customers))
    n_train = int(round(0.80 * len(customers)))
    train_indices = np.sort(perm[:n_train]).astype(int)
    test_indices = np.sort(perm[n_train:]).astype(int)

    np.savez_compressed(
        OUTDIR / "module2_inputs.npz",
        toolbox_numeric_X=toolbox_numeric_X,
        toolbox_binary_x=toolbox_binary_x,
        toolbox_binary_y=toolbox_binary_y,
        imputation_complete_subset=imputation_complete_subset,
        imputation_evaluation_mask=imputation_evaluation_mask.astype(bool),
        imputation_source_row_indices=eval_rows.astype(int),
        train_indices=train_indices,
        test_indices=test_indices,
        numeric_columns=np.asarray(numeric_cols, dtype="U32"),
        model_numeric_columns=np.asarray(model_numeric_cols, dtype="U32"),
        model_categorical_columns=np.asarray(
            model_categorical_cols, dtype="U32"
        ),
        outlier_numeric_columns=np.asarray(
            outlier_numeric_cols, dtype="U32"
        ),
    )

    # --------------------------------------------------------------
    # Exploration-only gold data.
    # --------------------------------------------------------------
    exploration_target = (
        numeric_clean[:, 1] > np.nanmedian(numeric_clean[:, 1])
    ).astype(int)

    np.savez_compressed(
        OUTDIR / "module2_gold.npz",
        customer_entity_ids=entity_ids,
        duplicate_pairs=gold_pairs,
        customer_numeric_clean=numeric_clean,
        numeric_columns=np.asarray(numeric_cols, dtype="U32"),
        missingness_masks=missing_masks.astype(bool),
        missingness_mask_names=np.asarray(
            [
                "MCAR_phone",
                "MAR_household_size",
                "MNAR_annual_income",
                "MCAR_email",
            ],
            dtype="U32",
        ),
        exploration_target=exploration_target,
    )

    # --------------------------------------------------------------
    # Named scalar/list/dictionary parameters.
    # --------------------------------------------------------------
    params = {
        "seed": SEED,
        "reference_date": REFERENCE_DATE.strftime("%Y-%m-%d"),
        "valid_age_range": [0, 120],
        "valid_email_regex": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
        "city_aliases": CITY_ALIASES,

        "toolbox": {
            "profile_columns": ["age", "annual_income", "household_size"],
            "frequency_k": 10,
            "knn_k": 5,
            "lof_neighbors": 20,
        },

        "entity_weights": {
            "name_sim": 0.30,
            "email_sim": 0.25,
            "phone_agree": 0.20,
            "city_agree": 0.10,
            "dob_agree": 0.15,
        },
        "entity_thresholds": {
            "lower": 0.58,
            "upper": 0.80,
        },

        "missingness_examples": {
            "MCAR": {
                "target": "phone",
                "conditioning": ["city", "age"],
            },
            "MAR": {
                "target": "household_size",
                "conditioning": ["city", "age"],
            },
            "MNAR": {
                "target": "annual_income",
                "conditioning": ["city", "age"],
            },
        },

        "imputation_k": 5,
        "imputation_random_state": SEED,

        "outlier_contamination": 0.02,
        "lof_neighbors": 20,
        "outlier_numeric_columns": outlier_numeric_cols,

        "model_numeric_columns": model_numeric_cols,
        "model_categorical_columns": model_categorical_cols,
        "engineered_features": [
            "row mean over the imputed numerical columns",
            "interaction between the first two imputed numerical columns",
        ],

        "input_files": {
            "customers": "customers.csv",
            "transactions": "transactions.csv",
            "contacts": "contacts.csv",
            "parameters": "module2_parameters.json",
            "student_arrays": "module2_inputs.npz",
            "exploration_gold": "module2_gold.npz",
        },

        "notes": {
            "gold_usage": (
                "module2_gold.npz is for explicitly labelled Exploration "
                "components only. Autograded functions are tested on hidden inputs."
            ),
            "blocking_pass_1": (
                "same canonical city and same birth year"
            ),
            "blocking_pass_2": (
                "same final four standardized phone digits"
            ),
            "task20": (
                "Use module2_inputs.npz keys imputation_complete_subset "
                "and imputation_evaluation_mask; k and random_state come "
                "from module2_parameters.json."
            ),
            "task23": (
                "Use module2_inputs.npz keys train_indices and test_indices; "
                "column lists come from module2_parameters.json."
            ),
        },
    }

    (OUTDIR / "module2_parameters.json").write_text(
        json.dumps(params, indent=2),
        encoding="utf-8",
    )

    print(f"Generated customers.csv: {len(customers):,} rows")
    print(f"Generated transactions.csv: {len(transactions):,} rows")
    print(f"Generated contacts.csv: {len(contacts):,} rows")
    print(
        "Total tuples: "
        f"{len(customers) + len(transactions) + len(contacts):,}"
    )
    print(f"Gold duplicate pairs: {len(gold_pairs):,}")
    print("Generated module2_parameters.json")
    print("Generated module2_inputs.npz (student-visible task inputs)")
    print("Generated module2_gold.npz (Exploration-only gold data)")


if __name__ == "__main__":
    main()
