"""
Attack 6: Personalized Phishing at Scale (Account Takeover via credential
harvest)

Simulates an LLM-generated, context-aware phishing message that harvests
a real cardholder's login credentials, followed by the attacker logging
in from a NEW device/browser and immediately making purchases. Unlike
deepfake voice ATO (which targets the call-center channel), this attack
targets the standard e-commerce login flow -- the tell is a brand-new,
never-seen-before device transacting on an otherwise-established account,
with a probing small purchase first (testing the stolen credentials still
work) followed quickly by a larger one.

Signature:
- channel = "ecom"
- device_id never seen before for this user (is_new_device signal)
- moderate auth_confidence (password-only login, no step-up challenge
  was triggered because the credentials were technically "correct")
- a small "probe" purchase followed shortly after by a larger payout
  purchase, both from the same new device, in a tight time window
- merchant category often off-profile for the victim (attacker doesn't
  know their taste, just their card details)
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

OFF_PROFILE_CATEGORIES = ["electronics", "gift_cards", "digital_goods", "travel", "entertainment"]


def generate_phishing_ato_attacks(
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
        attacker_device = f"dev_{uuid.uuid4().hex[:8]}"
        day_offset = random.randint(0, span_days - 1)
        harvest_ts = min_ts + timedelta(
            days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59)
        )

        # location is wherever the attacker actually is, not the victim's home
        lat = round(random.uniform(-60, 60), 4)
        lon = round(random.uniform(-150, 150), 4)

        # small probe purchase minutes after the credentials are harvested
        probe_amount = round(random.uniform(1, 25), 2)
        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": harvest_ts,
            "amount": probe_amount,
            "merchant_category": random.choice(OFF_PROFILE_CATEGORIES),
            "latitude": lat,
            "longitude": lon,
            "card_age_days_at_tx": profile["card_age_days"],
            "channel": "ecom",
            "device_id": attacker_device,
            "auth_confidence": round(float(np.random.uniform(0.55, 0.8)), 4),
            "dispute_filed": 0,
            "dispute_narrative_similarity": 0.0,
            "otp_override": 0,
            "is_fraud": 1,
            "attack_type": "phishing_ato",
        })

        # payout purchase minutes to a couple hours later, same new device
        payout_ts = harvest_ts + timedelta(minutes=random.randint(10, 120))
        payout_amount = round(random.uniform(300, 2500), 2)
        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": payout_ts,
            "amount": payout_amount,
            "merchant_category": random.choice(OFF_PROFILE_CATEGORIES),
            "latitude": lat,
            "longitude": lon,
            "card_age_days_at_tx": profile["card_age_days"],
            "channel": "ecom",
            "device_id": attacker_device,
            "auth_confidence": round(float(np.random.uniform(0.55, 0.8)), 4),
            "dispute_filed": 0,
            "dispute_narrative_similarity": 0.0,
            "otp_override": 0,
            "is_fraud": 1,
            "attack_type": "phishing_ato",
        })

    return pd.DataFrame(rows)
