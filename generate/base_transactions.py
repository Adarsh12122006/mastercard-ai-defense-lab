"""
Base synthetic transaction generator.

Produces realistic-looking LEGITIMATE payment transactions that form the
backdrop against which fraud attacks (see generators/) are injected.

Design goals for fidelity:
- Each simulated "user" has a stable behavioral profile (home location,
  preferred merchant categories, typical spend range, typical active hours)
  so that fraud injected later can be judged against a believable baseline.
- Amounts follow a log-normal distribution (realistic for consumer spend:
  many small purchases, few large ones) rather than uniform random.
- Timestamps cluster around each user's typical active hours instead of
  being uniformly spread across 24 hours.
"""

import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

MERCHANT_CATEGORIES = [
    "grocery", "restaurant", "gas_station", "electronics", "clothing",
    "pharmacy", "streaming", "ride_share", "travel", "home_goods",
    "utilities", "entertainment",
]

CITIES = [
    ("New York", 40.7128, -74.0060),
    ("Los Angeles", 34.0522, -118.2437),
    ("Chicago", 41.8781, -87.6298),
    ("Houston", 29.7604, -95.3698),
    ("Mumbai", 19.0760, 72.8777),
    ("Bengaluru", 12.9716, 77.5946),
    ("Delhi", 28.7041, 77.1025),
    ("London", 51.5074, -0.1278),
]


def make_user_profiles(n_users: int) -> pd.DataFrame:
    """Create a stable behavioral profile per simulated cardholder."""
    profiles = []
    for i in range(n_users):
        home_city = random.choice(CITIES)
        # each user has a preferred subset of merchant categories
        n_prefs = random.randint(3, 6)
        preferred_categories = random.sample(MERCHANT_CATEGORIES, n_prefs)
        profiles.append({
            "user_id": f"user_{i:05d}",
            "home_city": home_city[0],
            "home_lat": home_city[1],
            "home_lon": home_city[2],
            "preferred_categories": preferred_categories,
            # log-normal mean/std per-user -> some users spend more than others
            "avg_spend": float(np.random.lognormal(mean=3.5, sigma=0.6)),
            "active_hour_center": random.randint(8, 22),  # typical hour they transact
            "card_age_days": random.randint(30, 3000),
        })
    return pd.DataFrame(profiles)


def generate_legit_transactions(
    profiles: pd.DataFrame,
    n_transactions: int,
    start_date: datetime,
    days: int,
) -> pd.DataFrame:
    """Generate legitimate transactions consistent with each user's profile."""
    rows = []
    profiles_list = profiles.to_dict("records")

    for _ in range(n_transactions):
        profile = random.choice(profiles_list)
        category = random.choice(profile["preferred_categories"])

        # amount: log-normal around the user's personal average spend
        amount = round(float(np.random.lognormal(
            mean=np.log(max(profile["avg_spend"], 1.0)), sigma=0.5
        )), 2)
        amount = min(amount, 5000.0)  # cap extreme outliers

        # timestamp: random day in range, hour clustered near user's active hour
        day_offset = random.randint(0, max(days - 1, 0))
        hour = int(np.clip(
            np.random.normal(loc=profile["active_hour_center"], scale=2.5), 0, 23
        ))
        minute = random.randint(0, 59)
        ts = start_date + timedelta(days=day_offset, hours=hour, minutes=minute)

        # location: mostly home city, occasional small jitter (local travel)
        lat = profile["home_lat"] + np.random.normal(0, 0.05)
        lon = profile["home_lon"] + np.random.normal(0, 0.05)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "merchant_id": f"merch_{category}_{random.randint(1,120):03d}",
            "memo": "",
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "card_age_days_at_tx": profile["card_age_days"],
            "is_fraud": 0,
            "attack_type": "none",
        })

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return df


if __name__ == "__main__":
    profiles = make_user_profiles(n_users=500)
    profiles.to_csv("/home/claude/mastercard-ai-defense-lab/data/user_profiles.csv", index=False)

    legit_df = generate_legit_transactions(
        profiles,
        n_transactions=20000,
        start_date=datetime(2026, 6, 1),
        days=60,
    )
    legit_df.to_csv("/home/claude/mastercard-ai-defense-lab/data/legit_transactions.csv", index=False)
    print(f"Generated {len(profiles)} user profiles and {len(legit_df)} legit transactions.")
    print(legit_df.head())
