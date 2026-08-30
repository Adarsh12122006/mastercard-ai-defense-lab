"""
Attack 5: AI Voice/Deepfake Social Engineering (Account Takeover)

Simulates a deepfake voice clone impersonating a real, ESTABLISHED
cardholder to a call-center agent (or impersonating the bank to the
cardholder) in order to authorize a high-value transaction or push an
OTP override. Unlike Attacks 1-4, this attack doesn't manipulate the
transaction pattern itself so much as the AUTHORIZATION CHANNEL:

Signature:
- channel = "call_center" (the attack vector this family lives in)
- auth_confidence is borderline-low: the voiceprint/agent-verification
  match is close enough to pass a rushed or lightly-scrutinized check,
  but not as confident as a genuine live match
- otp_override = 1 (the deepfake talks the agent into bypassing normal
  step-up verification -- "I'm traveling and can't access my phone")
- device_id is brand new (the attacker isn't calling from the victim's
  known devices/lines)
- targets an established account (real card_age) since the whole point
  is impersonating someone who already has a trusted history, then
  cashing out with an unusually large single transaction
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

CASH_OUT_CATEGORIES = ["travel", "electronics", "gift_cards", "digital_goods"]


def generate_deepfake_voice_ato_attacks(
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
        category = random.choice(CASH_OUT_CATEGORIES)

        # single large cash-out authorized "over the phone"
        amount = round(random.uniform(1200, 7000), 2)

        day_offset = random.randint(0, span_days - 1)
        ts = min_ts + timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        # attacker calling in isn't physically at the victim's home location
        lat = profile["home_lat"] + np.random.normal(0, 5)
        lon = profile["home_lon"] + np.random.normal(0, 5)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "card_age_days_at_tx": profile["card_age_days"],
            "channel": "call_center",
            "device_id": f"dev_{uuid.uuid4().hex[:8]}",
            "auth_confidence": round(float(np.random.uniform(0.35, 0.62)), 4),
            "dispute_filed": 0,
            "dispute_narrative_similarity": 0.0,
            "otp_override": 1,
            "is_fraud": 1,
            "attack_type": "deepfake_voice_ato",
        })

    return pd.DataFrame(rows)
