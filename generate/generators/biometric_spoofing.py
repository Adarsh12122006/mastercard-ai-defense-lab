"""
Attack 8: Biometric Spoofing for Step-Up Authentication

Simulates a synthetic (GenAI-generated) face or voice used to defeat an
app's biometric step-up challenge, which is normally triggered for
high-value or unusual transactions. The spoof is good enough to pass a
lightly-tuned liveness/match check, but the underlying match confidence
is measurably lower than a genuine biometric match -- that gap is the
detection signal.

Signature:
- channel = "app_biometric" (this attack specifically targets the
  biometric step-up flow, not card-present or call-center)
- auth_confidence is LOW-BORDERLINE: high enough to have technically
  cleared the app's own pass/fail threshold, but well below the
  confidence of a genuine match on the same user
- triggered on a high-value transaction (step-up auth is normally only
  invoked above a value threshold -- that's *why* the attacker needed to
  defeat it in the first place)
- device is often new (spoofing kits run on attacker-controlled hardware)
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

HIGH_VALUE_CATEGORIES = ["electronics", "travel", "gift_cards", "digital_goods"]


def generate_biometric_spoofing_attacks(
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
        category = random.choice(HIGH_VALUE_CATEGORIES)
        amount = round(random.uniform(900, 5500), 2)

        day_offset = random.randint(0, span_days - 1)
        ts = min_ts + timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        lat = profile["home_lat"] + np.random.normal(0, 2)
        lon = profile["home_lon"] + np.random.normal(0, 2)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "card_age_days_at_tx": profile["card_age_days"],
            "channel": "app_biometric",
            "device_id": f"dev_{uuid.uuid4().hex[:8]}",
            "auth_confidence": round(float(np.random.uniform(0.4, 0.68)), 4),
            "dispute_filed": 0,
            "dispute_narrative_similarity": 0.0,
            "otp_override": 0,
            "is_fraud": 1,
            "attack_type": "biometric_spoofing",
        })

    return pd.DataFrame(rows)
