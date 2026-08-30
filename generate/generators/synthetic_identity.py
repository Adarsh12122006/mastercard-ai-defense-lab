"""
Attack 3: Synthetic Identity Onboarding ("Bust-Out") Fraud

Simulates a GenAI-generated synthetic identity that opens an account,
builds a short, coherent, unremarkable transaction history to pass as
legitimate (an account with a NEW/low card_age), and then "busts out"
with a burst of high-value transactions before disappearing.

Signature: very low card_age_days combined with high-value transactions
that are inconsistent with the short, thin history a genuine new account
would typically show.
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd


def generate_synthetic_identity_attacks(
    legit_df: pd.DataFrame,
    n_identities: int,
    bust_out_amount_range=(800, 6000),
) -> pd.DataFrame:
    rows = []
    min_ts = legit_df["timestamp"].min()
    max_ts = legit_df["timestamp"].max()
    span_days = max((max_ts - min_ts).days, 1)

    categories = ["electronics", "gift_cards", "digital_goods", "travel", "home_goods"]

    for i in range(n_identities):
        synth_user_id = f"synthid_{i:05d}"
        card_age_days = random.randint(1, 25)  # brand-new account

        # a few small "credibility-building" transactions first
        n_building = random.randint(2, 5)
        onboarding_start = min_ts + timedelta(days=random.randint(0, span_days // 2))
        for j in range(n_building):
            amount = round(random.uniform(15, 80), 2)
            ts = onboarding_start + timedelta(days=j * random.randint(1, 3))
            rows.append({
                "transaction_id": str(uuid.uuid4()),
                "user_id": synth_user_id,
                "timestamp": ts,
                "amount": amount,
                "merchant_category": random.choice(["grocery", "gas_station", "streaming"]),
                "merchant_id": f"merch_onboard_{random.randint(1,50):03d}",
                "memo": "",
                "latitude": round(random.uniform(-60, 60), 4),
                "longitude": round(random.uniform(-150, 150), 4),
                "card_age_days_at_tx": card_age_days + j,
                "is_fraud": 1,
                "attack_type": "synthetic_identity",
            })

        # bust-out burst: 1-3 large transactions right after building trust
        bust_ts = onboarding_start + timedelta(days=n_building * 3 + random.randint(1, 3))
        n_bust = random.randint(1, 3)
        for _ in range(n_bust):
            amount = round(random.uniform(*bust_out_amount_range), 2)
            rows.append({
                "transaction_id": str(uuid.uuid4()),
                "user_id": synth_user_id,
                "timestamp": bust_ts,
                "amount": amount,
                "merchant_category": random.choice(categories),
                "merchant_id": f"merch_bustout_{random.randint(1,50):03d}",
                "memo": "",
                "latitude": round(random.uniform(-60, 60), 4),
                "longitude": round(random.uniform(-150, 150), 4),
                "card_age_days_at_tx": card_age_days + n_building + 3,
                "is_fraud": 1,
                "attack_type": "synthetic_identity",
            })

    return pd.DataFrame(rows)
