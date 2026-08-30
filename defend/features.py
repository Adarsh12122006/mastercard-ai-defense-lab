"""
Feature engineering for fraud detection.

Turns raw transaction rows into model-ready features that target the
specific signatures of each attack family in the taxonomy:

- Velocity features (card_testing: many txns in a short window)
- Amount deviation from user's personal history (behavioral_mimicry)
- Account-age / history-thinness features (synthetic_identity)
- Merchant-category amount deviation (transaction_laundering)
- Geo deviation from home location
- Device-familiarity features (deepfake_voice_ato, phishing_ato,
  biometric_spoofing -- all three route the attack through a device or
  channel the user hasn't used before)
- Auth-confidence features (deepfake_voice_ato, biometric_spoofing --
  both attacks pass a step-up/verification check, but with a lower
  match confidence than a genuine authorization)
- Channel one-hot flags (call_center / app_biometric channels are
  disproportionately used by the identity-based attack families)
- Dispute/narrative features (chargeback_narrative_fraud -- the fraud
  signal lives in the dispute rather than the original purchase)
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

    # --- device-familiarity: has this user transacted from this device before? ---
    # (walks the sorted history per user; the first time a device appears for
    # a given user it counts as "new", same logic a real device-fingerprinting
    # system would use)
    if "device_id" in df.columns:
        df["is_new_device"] = 0
        for uid, group in df.groupby("user_id"):
            seen = set()
            flags = []
            for dev in group["device_id"]:
                flags.append(0 if dev in seen else 1)
                seen.add(dev)
            df.loc[group.index, "is_new_device"] = flags
    else:
        df["is_new_device"] = 0

    # --- auth-confidence: how confident was the verification/step-up check? ---
    if "auth_confidence" in df.columns:
        df["auth_confidence"] = df["auth_confidence"].fillna(0.95)
        df["low_auth_confidence"] = (df["auth_confidence"] < 0.8).astype(int)
    else:
        df["auth_confidence"] = 0.95
        df["low_auth_confidence"] = 0

    # --- channel flags: identity-based attacks concentrate in specific channels ---
    if "channel" in df.columns:
        df["is_call_center_channel"] = (df["channel"] == "call_center").astype(int)
        df["is_app_biometric_channel"] = (df["channel"] == "app_biometric").astype(int)
    else:
        df["is_call_center_channel"] = 0
        df["is_app_biometric_channel"] = 0

    # --- OTP/step-up bypass flag (deepfake voice ATO talks agents into this) ---
    df["otp_override"] = df["otp_override"].fillna(0).astype(int) if "otp_override" in df.columns else 0

    # --- dispute/narrative features (chargeback narrative fraud) ---
    if "dispute_filed" in df.columns:
        df["dispute_filed"] = df["dispute_filed"].fillna(0).astype(int)
    else:
        df["dispute_filed"] = 0
    if "dispute_narrative_similarity" in df.columns:
        df["dispute_narrative_similarity"] = df["dispute_narrative_similarity"].fillna(0.0)
    else:
        df["dispute_narrative_similarity"] = 0.0

    # merchant category encoded
    df = pd.get_dummies(df, columns=["merchant_category"], prefix="cat")

    return df


FEATURE_COLUMNS = [
    "amount", "amount_zscore", "geo_deviation", "time_since_prev_txn_sec",
    "txns_last_10min", "amount_over_category_ceiling", "is_round_amount",
    "is_new_account", "card_age_days_at_tx", "user_txn_count",
    "is_new_device", "auth_confidence", "low_auth_confidence",
    "is_call_center_channel", "is_app_biometric_channel", "otp_override",
    "dispute_filed", "dispute_narrative_similarity",
]
