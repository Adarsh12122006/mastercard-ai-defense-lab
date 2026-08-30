"""
Attack 5: Adversarial Evasion of the Deployed Classifier

This is the "attack the AI itself" vector: rather than inventing a new fraud
pattern from scratch, the attacker treats our own trained detector as a
black box, repeatedly probes it with candidate transactions, and uses the
model's own output (fraud probability) to binary-search for the amount that
sits *just* under the decision threshold for a given user/category — i.e.
a transaction crafted to look "just legitimate enough" to this specific model.

This also doubles as a simplified stand-in for model/API extraction (an
attacker repeatedly querying a fraud-scoring endpoint to reconstruct its
decision boundary) since the technique is identical.

Because this attack requires a TRAINED model to probe, it must be run
AFTER an initial model exists (see loop/adversarial_loop.py, which
orchestrates: train baseline -> generate adversarial evasions against it ->
retrain with adversarial examples included -> re-evaluate).
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd


def _score_candidate(model, feature_cols, feature_row: dict) -> float:
    """Score a single candidate transaction's fraud probability using the model."""
    import pandas as pd
    X = pd.DataFrame([feature_row])[feature_cols].fillna(0)
    return float(model.predict_proba(X)[:, 1][0])


def generate_adversarial_evasion_attacks(
    profiles: pd.DataFrame,
    legit_df: pd.DataFrame,
    model,
    feature_cols,
    engineer_features_fn,
    n_attacks: int = 40,
    search_steps: int = 8,
) -> pd.DataFrame:
    """
    For each targeted user, binary-search the transaction amount to find the
    largest amount that still scores BELOW the model's fraud threshold (0.5),
    simulating an attacker who has learned to query the model and craft
    transactions that hug the decision boundary from the legitimate side,
    then nudges 5-15% past it to attempt maximum extraction while evading.
    """
    rows = []
    profiles_list = profiles.to_dict("records")
    min_ts = legit_df["timestamp"].min()
    max_ts = legit_df["timestamp"].max()
    span_days = max((max_ts - min_ts).days, 1)

    targets = random.sample(profiles_list, min(n_attacks, len(profiles_list)))

    for profile in targets:
        category = random.choice(profile["preferred_categories"])
        day_offset = random.randint(0, span_days - 1)
        ts = min_ts + timedelta(days=day_offset, hours=profile["active_hour_center"], minutes=random.randint(0, 59))

        # binary search bounds: start well within normal range, up to a large multiple
        lo, hi = profile["avg_spend"] * 0.5, profile["avg_spend"] * 15
        boundary_amount = lo

        for _ in range(search_steps):
            mid = (lo + hi) / 2
            candidate_raw = pd.DataFrame([{
                "transaction_id": "probe",
                "user_id": profile["user_id"],
                "timestamp": ts,
                "amount": round(mid, 2),
                "merchant_category": category,
                "merchant_id": f"merch_{category}_001",
                "memo": "",
                "latitude": profile["home_lat"],
                "longitude": profile["home_lon"],
                "card_age_days_at_tx": profile["card_age_days"],
                "is_fraud": 0,
                "attack_type": "none",
            }])
            # need context (other user txns) for feature engineering to compute z-scores etc;
            # append to a slice of legit history for this user to get realistic stats
            user_hist = legit_df[legit_df["user_id"] == profile["user_id"]]
            probe_context = pd.concat([user_hist, candidate_raw], ignore_index=True)
            engineered = engineer_features_fn(probe_context)
            cat_cols = [c for c in engineered.columns if c.startswith("cat_")]
            probe_row = engineered.iloc[[-1]]
            for c in feature_cols:
                if c not in probe_row.columns:
                    probe_row[c] = 0
            score = float(model.predict_proba(probe_row[feature_cols].fillna(0))[:, 1][0])

            if score < 0.5:
                boundary_amount = mid
                lo = mid  # push higher, still evading
            else:
                hi = mid  # too high, pull back

        # attacker pushes slightly past the found boundary to maximize extraction
        final_amount = round(boundary_amount * random.uniform(1.0, 1.1), 2)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": final_amount,
            "merchant_category": category,
            "merchant_id": f"merch_{category}_{random.randint(1,120):03d}",
            "memo": "",
            "latitude": profile["home_lat"],
            "longitude": profile["home_lon"],
            "card_age_days_at_tx": profile["card_age_days"],
            "is_fraud": 1,
            "attack_type": "adversarial_evasion",
        })

    return pd.DataFrame(rows)
