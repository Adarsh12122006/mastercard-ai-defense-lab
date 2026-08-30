"""
Base synthetic transaction generator.

Produces realistic-looking LEGITIMATE payment transactions that form the
backdrop against which fraud attacks (see generators/) are injected.

Design goals for fidelity:
- Each simulated "user" has a stable behavioral profile (home location,
  preferred merchant categories, typical spend range, typical active hours,
  a small pool of known devices) so that fraud injected later can be judged
  against a believable baseline.
- Amounts follow a log-normal distribution (realistic for consumer spend:
  many small purchases, few large ones) rather than uniform random.
- Timestamps cluster around each user's typical active hours instead of
  being uniformly spread across 24 hours.
- Channel + device fields support the identity/auth-based attack families
  (deepfake voice ATO, phishing ATO, biometric spoofing) added alongside
  the original transaction-pattern attacks.
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

# transaction authorization channel — needed to represent the auth-focused
# attack families (call-center vishing, app biometric step-up, etc.)
CHANNELS = ["pos", "ecom", "app_biometric", "call_center"]


def new_device_id() -> str:
    return f"dev_{uuid.uuid4().hex[:8]}"


def make_user_profiles(n_users: int) -> pd.DataFrame:
    """Create a stable behavioral profile per simulated cardholder."""
    profiles = []
    for i in range(n_users):
        home_city = random.choice(CITIES)
        n_prefs = random.randint(3, 6)
        preferred_categories = random.sample(MERCHANT_CATEGORIES, n_prefs)
        n_devices = random.randint(2, 3)
        profiles.append({
            "user_id": f"user_{i:05d}",
            "home_city": home_city[0],
            "home_lat": home_city[1],
            "home_lon": home_city[2],
            "preferred_categories": preferred_categories,
            "avg_spend": float(np.random.lognormal(mean=3.5, sigma=0.6)),
            "active_hour_center": random.randint(8, 22),
            "card_age_days": random.randint(30, 3000),
            "device_pool": [new_device_id() for _ in range(n_devices)],
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

        amount = round(float(np.random.lognormal(
            mean=np.log(max(profile["avg_spend"], 1.0)), sigma=0.5
        )), 2)
        amount = min(amount, 5000.0)

        day_offset = random.randint(0, max(days - 1, 0))
        hour = int(np.clip(
            np.random.normal(loc=profile["active_hour_center"], scale=2.5), 0, 23
        ))
        minute = random.randint(0, 59)
        ts = start_date + timedelta(days=day_offset, hours=hour, minutes=minute)

        lat = profile["home_lat"] + np.random.normal(0, 0.05)
        lon = profile["home_lon"] + np.random.normal(0, 0.05)

        # legit purchases mostly reuse one of the user's small known-device
        # pool, and skew toward in-person / normal ecom channels. A small
        # slice legitimately call in (phone orders) or use the app's
        # biometric step-up -- these channels aren't EXCLUSIVE to fraud,
        # they're just disproportionately used by it, which is what makes
        # channel alone an imperfect signal and forces the model to combine
        # it with auth_confidence/device/dispute signals instead.
        channel = random.choices(
            ["pos", "ecom", "app_biometric", "call_center"],
            weights=[0.52, 0.38, 0.07, 0.03],
        )[0]
        device_id = random.choice(profile["device_pool"])

        # rare genuine dispute (defective item, didn't recognize merchant
        # name, etc.) -- filed less impulsively than fraud rings, and the
        # narrative doesn't cluster near the GenAI-template fingerprints
        dispute_filed = 1 if random.random() < 0.015 else 0
        dispute_similarity = round(float(np.random.uniform(0.02, 0.35)), 4) if dispute_filed else 0.0

        # rare legitimate OTP bypass (lost phone, verified another way)
        otp_override = 1 if random.random() < 0.004 else 0

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "card_age_days_at_tx": profile["card_age_days"],
            "channel": channel,
            "device_id": device_id,
            "auth_confidence": round(float(np.random.uniform(0.86, 0.999)), 4),
            "dispute_filed": dispute_filed,
            "dispute_narrative_similarity": dispute_similarity,
            "otp_override": otp_override,
            "is_fraud": 0,
            "attack_type": "none",
        })

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return df


if __name__ == "__main__":
    import os
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(out_dir, exist_ok=True)

    profiles = make_user_profiles(n_users=500)
    profiles.drop(columns=["device_pool"]).to_csv(os.path.join(out_dir, "user_profiles.csv"), index=False)

    legit_df = generate_legit_transactions(
        profiles,
        n_transactions=20000,
        start_date=datetime(2026, 6, 1),
        days=60,
    )
    legit_df.to_csv(os.path.join(out_dir, "legit_transactions.csv"), index=False)
    print(f"Generated {len(profiles)} user profiles and {len(legit_df)} legit transactions.")
    print(legit_df.head())
