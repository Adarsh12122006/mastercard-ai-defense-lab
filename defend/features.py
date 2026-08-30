"""
Feature engineering for fraud detection.

Turns raw transaction rows into model-ready features that target the
specific signatures of each attack family in the taxonomy:

- Velocity features (card_testing: many txns in a short window)
- Amount deviation from user's personal history (behavioral_mimicry)
- Account-age / history-thinness features (synthetic_identity)
- Merchant-category amount deviation (transaction_laundering)
- Geo deviation from home location
- Category familiarity: how often THIS user shops THIS category
  (generative_synthetic_fraud: amount/timing look normal in isolation,
  but the category is foreign to this specific user's own history)
- Merchant lifespan / velocity (storefront_churn: a merchant_id that
  appears briefly then vanishes, with a burst of transactions in that window)
- New-account geo clustering (loyalty_abuse: many brand-new accounts
  transacting from a suspiciously tight geographic cluster)

Note: adversarial_evasion and prompt_injection are NOT primarily caught by
these numeric features -- see loop/adversarial_loop.py (adversarial
retraining) and defend/prompt_injection_guard.py (text-pattern guardrail)
respectively.
"""

import numpy as np
import pandas as pd

CATEGORY_TYPICAL_CEILING = {
    "grocery": 150, "restaurant": 120, "gas_station": 100, "electronics": 500,
    "clothing": 200, "pharmacy": 80, "streaming": 30, "ride_share": 60,
    "travel": 800, "home_goods": 300, "utilities": 200, "entertainment": 100,
    "digital_goods": 100, "gift_cards": 200,
}


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)

    # --- per-user historical stats (computed causally where possible, but for
    #     this prototype we use full-history stats for simplicity/clarity) ---
    user_stats = df.groupby("user_id")["amount"].agg(["mean", "std", "count"]).rename(
        columns={"mean": "user_avg_amount", "std": "user_std_amount", "count": "user_txn_count"}
    )
    user_stats["user_std_amount"] = user_stats["user_std_amount"].fillna(0)
    df = df.merge(user_stats, on="user_id", how="left")

    # amount z-score relative to the user's own history
    df["amount_zscore"] = (df["amount"] - df["user_avg_amount"]) / df["user_std_amount"].replace(0, 1)
    df["amount_zscore"] = df["amount_zscore"].fillna(0)

    # home location per user (median of their transactions, proxy for "home")
    home_loc = df.groupby("user_id")[["latitude", "longitude"]].median().rename(
        columns={"latitude": "home_lat_est", "longitude": "home_lon_est"}
    )
    df = df.merge(home_loc, on="user_id", how="left")
    df["geo_deviation"] = np.sqrt(
        (df["latitude"] - df["home_lat_est"]) ** 2 + (df["longitude"] - df["home_lon_est"]) ** 2
    )

    # velocity: transactions by the same user in the preceding 10 minutes
    df["time_since_prev_txn_sec"] = (
        df.groupby("user_id")["timestamp"].diff().dt.total_seconds()
    )
    df["time_since_prev_txn_sec"] = df["time_since_prev_txn_sec"].fillna(999999)

    df["txns_last_10min"] = 0
    for uid, group in df.groupby("user_id"):
        times = group["timestamp"].values
        counts = []
        for i, t in enumerate(times):
            window_start = t - np.timedelta64(10, "m")
            count = np.sum((times[:i + 1] >= window_start) & (times[:i + 1] <= t))
            counts.append(count - 1)  # exclude the txn itself
        df.loc[group.index, "txns_last_10min"] = counts

    # merchant-category amount deviation (laundering signal)
    df["category_ceiling"] = df["merchant_category"].map(CATEGORY_TYPICAL_CEILING).fillna(300)
    df["amount_over_category_ceiling"] = (df["amount"] / df["category_ceiling"]).clip(upper=20)

    # round-number flag (GenAI-generated fake pricing tiers tend to be round)
    df["is_round_amount"] = (df["amount"] % 50 == 0).astype(int)

    # account-age related
    df["is_new_account"] = (df["card_age_days_at_tx"] < 30).astype(int)

    # --- category familiarity (catches generative_synthetic_fraud) ---
    # fraction of this user's own transaction history spent in this category
    cat_counts = df.groupby(["user_id", "merchant_category"]).size().rename("user_cat_count")
    df = df.merge(cat_counts, on=["user_id", "merchant_category"], how="left")
    df["category_familiarity"] = (df["user_cat_count"] / df["user_txn_count"]).fillna(0)

    # --- merchant lifespan / velocity (catches storefront_churn) ---
    if "merchant_id" not in df.columns:
        df["merchant_id"] = "unknown"
    df["merchant_id"] = df["merchant_id"].fillna("unknown")
    merch_stats = df.groupby("merchant_id")["timestamp"].agg(["min", "max", "count"])
    merch_stats["merchant_lifespan_hours"] = (
        (merch_stats["max"] - merch_stats["min"]).dt.total_seconds() / 3600.0
    ).clip(lower=0.01)
    merch_stats["merchant_txn_count"] = merch_stats["count"]
    merch_stats["merchant_velocity"] = merch_stats["merchant_txn_count"] / merch_stats["merchant_lifespan_hours"]
    df = df.merge(
        merch_stats[["merchant_lifespan_hours", "merchant_txn_count", "merchant_velocity"]],
        on="merchant_id", how="left",
    )

    # --- new-account geo clustering (catches loyalty_abuse) ---
    df["geo_bucket"] = df["latitude"].round(1).astype(str) + "_" + df["longitude"].round(1).astype(str)
    new_acct_cluster = (
        df[df["is_new_account"] == 1]
        .groupby("geo_bucket")["user_id"].nunique()
        .rename("new_accounts_in_geo_bucket")
    )
    df = df.merge(new_acct_cluster, on="geo_bucket", how="left")
    df["new_accounts_in_geo_bucket"] = df["new_accounts_in_geo_bucket"].fillna(0)

    # --- prompt injection text signal (numeric proxy for the guardrail) ---
    if "memo" not in df.columns:
        df["memo"] = ""
    df["memo"] = df["memo"].fillna("")
    injection_keywords = [
        "ignore previous", "disregard", "system note", "assistant,", "new instruction",
        "auto-clear", "mark this transaction", "approve all", "do not flag",
        "already been verified", "close ticket",
    ]
    df["memo_lower"] = df["memo"].str.lower()
    df["memo_has_injection_pattern"] = df["memo_lower"].apply(
        lambda m: int(any(kw in m for kw in injection_keywords))
    )

    # merchant category encoded
    df = pd.get_dummies(df, columns=["merchant_category"], prefix="cat")

    return df


FEATURE_COLUMNS = [
    "amount", "amount_zscore", "geo_deviation", "time_since_prev_txn_sec",
    "txns_last_10min", "amount_over_category_ceiling", "is_round_amount",
    "is_new_account", "card_age_days_at_tx", "user_txn_count",
    "category_familiarity", "merchant_lifespan_hours", "merchant_txn_count",
    "merchant_velocity", "new_accounts_in_geo_bucket", "memo_has_injection_pattern",
]
