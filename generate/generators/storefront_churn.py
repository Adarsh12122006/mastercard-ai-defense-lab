"""
Attack 8: Autonomous Storefront Churn

Extends transaction laundering: instead of a single laundering transaction,
an AI agent spins up a fake storefront (auto-generated listings, reviews,
fake customer service), processes a short burst of transactions through it
within a narrow time window, then tears it down before it accumulates
enough disputes/chargebacks to get flagged by merchant-risk monitoring --
and repeats with a new fake storefront identity.

Signature: a merchant_id that appears for a very short lifespan (all its
transactions cluster within a few hours or 1-2 days) and processes an
unusually high transaction count in that window relative to its lifespan,
compared to legitimate merchants which show sustained activity over weeks.
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

FRONT_CATEGORIES = ["home_goods", "electronics", "clothing", "digital_goods"]


def generate_storefront_churn_attacks(
    profiles: pd.DataFrame,
    legit_df: pd.DataFrame,
    n_storefronts: int = 20,
    txns_per_storefront_range=(8, 20),
) -> pd.DataFrame:
    rows = []
    profiles_list = profiles.to_dict("records")
    min_ts = legit_df["timestamp"].min()
    max_ts = legit_df["timestamp"].max()
    span_days = max((max_ts - min_ts).days, 1)

    for i in range(n_storefronts):
        storefront_id = f"churnfront_{i:04d}"
        category = random.choice(FRONT_CATEGORIES)
        n_txns = random.randint(*txns_per_storefront_range)

        # storefront lives for a very short window: a few hours to ~1 day
        day_offset = random.randint(0, span_days - 1)
        storefront_birth = min_ts + timedelta(days=day_offset, hours=random.randint(0, 23))
        lifespan_hours = random.uniform(2, 20)

        # different "victims" (cardholders) hit this storefront in its brief life
        victims = random.sample(profiles_list, min(n_txns, len(profiles_list)))

        for victim in victims:
            offset_hours = random.uniform(0, lifespan_hours)
            ts = storefront_birth + timedelta(hours=offset_hours)
            amount = round(random.uniform(80, 600), 2)

            rows.append({
                "transaction_id": str(uuid.uuid4()),
                "user_id": victim["user_id"],
                "timestamp": ts,
                "amount": amount,
                "merchant_category": category,
                "merchant_id": storefront_id,
                "memo": "",
                "latitude": round(random.uniform(-60, 60), 4),
                "longitude": round(random.uniform(-150, 150), 4),
                "card_age_days_at_tx": victim["card_age_days"],
                "is_fraud": 1,
                "attack_type": "storefront_churn",
            })

    return pd.DataFrame(rows)
