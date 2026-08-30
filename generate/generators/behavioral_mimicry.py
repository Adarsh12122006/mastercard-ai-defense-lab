"""
Attack 1: Behavioral Mimicry Fraud

Simulates an AI agent that has learned a victim's spending profile and
injects fraudulent transactions designed to blend in with that profile,
while still containing subtle signals a well-tuned model can pick up on:
- amount slightly higher than the user's normal range (fraudster cashes out)
- occurs just outside the user's typical active hours (agent doesn't know
  the user's exact schedule, only the aggregate pattern)
- merchant category is *plausible* for the user but not their top preference
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd


def generate_behavioral_mimicry_attacks(
    profiles: pd.DataFrame,
    legit_df: pd.DataFrame,
    n_attacks: int,
) -> pd.DataFrame:
    rows = []
    profiles_list = profiles.to_dict("records")
    min_ts = legit_df["timestamp"].min()
    max_ts = legit_df["timestamp"].max()
    span_days = max((max_ts - min_ts).days, 1)

    targets = random.sample(profiles_list, min(n_attacks, len(profiles_list)))

    for profile in targets:
        # attacker picks a category the user has used but isn't their favorite
        category = random.choice(profile["preferred_categories"])

        # amount: 1.5x-3x the user's average -> "blends in" but skews high
        amount = round(profile["avg_spend"] * random.uniform(1.5, 3.0), 2)
        amount = min(amount, 8000.0)

        # timing: offset from the user's normal active hour by several hours
        # (the agent knows the *rough* pattern but not the exact schedule)
        hour_offset = random.choice([-7, -6, 6, 7, 8])
        hour = int(np.clip(profile["active_hour_center"] + hour_offset, 0, 23))
        day_offset = random.randint(0, span_days - 1)
        ts = min_ts + timedelta(days=day_offset, hours=hour, minutes=random.randint(0, 59))

        # location: mimicry agent doesn't have precise geo, adds larger jitter
        lat = profile["home_lat"] + np.random.normal(0, 0.3)
        lon = profile["home_lon"] + np.random.normal(0, 0.3)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "card_age_days_at_tx": profile["card_age_days"],
            "is_fraud": 1,
            "attack_type": "behavioral_mimicry",
        })

    return pd.DataFrame(rows)
