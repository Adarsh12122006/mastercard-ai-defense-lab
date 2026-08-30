"""
Attack 2: AI-Paced Card Testing / BIN Attack

Simulates an attacker (or compromised card) being probed with a rapid
sequence of small-value authorizations across DIFFERENT merchants, with
AI-driven pacing designed to mimic human timing variance and evade
simple rate-limit rules. Signature: high transaction velocity in a short
window, small/round-ish amounts, category diversity inconsistent with
the user's normal preferences, minimal geo consistency.
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

ALL_CATEGORIES = [
    "grocery", "restaurant", "gas_station", "electronics", "clothing",
    "pharmacy", "streaming", "ride_share", "travel", "home_goods",
    "utilities", "entertainment", "digital_goods", "gift_cards",
]


def generate_card_testing_attacks(
    profiles: pd.DataFrame,
    legit_df: pd.DataFrame,
    n_campaigns: int,
    txns_per_campaign_range=(6, 15),
) -> pd.DataFrame:
    rows = []
    profiles_list = profiles.to_dict("records")
    min_ts = legit_df["timestamp"].min()
    max_ts = legit_df["timestamp"].max()
    span_days = max((max_ts - min_ts).days, 1)

    targets = random.sample(profiles_list, min(n_campaigns, len(profiles_list)))

    for profile in targets:
        n_txns = random.randint(*txns_per_campaign_range)
        # entire probing campaign runs from a single attacker-controlled device
        campaign_device_id = f"dev_{uuid.uuid4().hex[:8]}"
        day_offset = random.randint(0, span_days - 1)
        # campaign starts at a random moment
        campaign_start = min_ts + timedelta(
            days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59)
        )
        # AI paces attempts with human-like variable gaps (not perfectly uniform)
        current_ts = campaign_start
        for _ in range(n_txns):
            # small test amounts, often just under common auth thresholds
            amount = round(random.choice([1.00, 1.50, 2.00, 0.50, 4.99, 9.99, random.uniform(1, 15)]), 2)
            category = random.choice(ALL_CATEGORIES)  # scattershot across categories

            # small geo jitter simulating different merchant processors, not the user's home
            lat = profile["home_lat"] + np.random.normal(0, 1.5)
            lon = profile["home_lon"] + np.random.normal(0, 1.5)

            rows.append({
                "transaction_id": str(uuid.uuid4()),
                "user_id": profile["user_id"],
                "timestamp": current_ts,
                "amount": amount,
                "merchant_category": category,
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "card_age_days_at_tx": profile["card_age_days"],
                "channel": "ecom",
            "device_id": campaign_device_id,
            "auth_confidence": round(float(np.random.uniform(0.5, 0.85)), 4),
            "dispute_filed": 0,
            "dispute_narrative_similarity": 0.0,
            "otp_override": 0,
            "is_fraud": 1,
                "attack_type": "card_testing",
            })

            # AI-paced human-like gap: mostly short (30s-4min), occasional longer pause
            gap_seconds = random.choice([
                random.uniform(20, 90),
                random.uniform(90, 240),
                random.uniform(240, 900),  # occasional longer pause to evade velocity rules
            ])
            current_ts = current_ts + timedelta(seconds=gap_seconds)

    return pd.DataFrame(rows)
