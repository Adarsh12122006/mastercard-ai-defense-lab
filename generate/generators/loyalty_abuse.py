"""
Attack 9: Loyalty / Rewards Program Abuse (Bot Network)

An AI-orchestrated bot network creates many low-value, reward-triggering
transactions across a cluster of synthetic accounts to farm signup bonuses
or reward points at scale. Signature: many brand-new accounts (like
synthetic identity) transacting at the SAME small set of reward-eligible
merchants, within a short time window, from a narrow geographic cluster
(the bot farm's actual infrastructure location) despite claiming different
"home" identities.
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

REWARD_CATEGORIES = ["streaming", "digital_goods", "gift_cards", "ride_share"]


def generate_loyalty_abuse_attacks(
    legit_df: pd.DataFrame,
    n_bot_accounts: int = 60,
    n_clusters: int = 3,
) -> pd.DataFrame:
    rows = []
    min_ts = legit_df["timestamp"].min()
    max_ts = legit_df["timestamp"].max()
    span_days = max((max_ts - min_ts).days, 1)

    # bot farm infrastructure: a small number of real-world geo clusters
    # the accounts all quietly share, despite each claiming a unique identity
    cluster_locations = [
        (round(random.uniform(-60, 60), 2), round(random.uniform(-150, 150), 2))
        for _ in range(n_clusters)
    ]

    accounts_per_cluster = n_bot_accounts // n_clusters
    for cluster_lat, cluster_lon in cluster_locations:
        campaign_start = min_ts + timedelta(days=random.randint(0, span_days - 2))

        for i in range(accounts_per_cluster):
            bot_user_id = f"bot_{cluster_lat}_{cluster_lon}_{i:03d}"
            card_age_days = random.randint(0, 5)  # extremely new
            category = random.choice(REWARD_CATEGORIES)

            # small reward-triggering purchase, tight geo cluster (bot farm's actual location)
            amount = round(random.uniform(1.0, 15.0), 2)
            ts = campaign_start + timedelta(
                hours=random.uniform(0, 48), minutes=random.randint(0, 59)
            )
            lat = cluster_lat + np.random.normal(0, 0.02)  # bots share near-identical geo
            lon = cluster_lon + np.random.normal(0, 0.02)

            rows.append({
                "transaction_id": str(uuid.uuid4()),
                "user_id": bot_user_id,
                "timestamp": ts,
                "amount": amount,
                "merchant_category": category,
                "merchant_id": f"merch_{category}_{random.randint(1,20):03d}",
                "memo": "",
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "card_age_days_at_tx": card_age_days,
                "is_fraud": 1,
                "attack_type": "loyalty_abuse",
            })

    return pd.DataFrame(rows)
