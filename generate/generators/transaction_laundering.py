"""
Attack 4: Transaction Laundering via GenAI-Generated Fake Merchants

Simulates laundering stolen card funds through GenAI-generated fake
storefronts that masquerade as an innocuous merchant category (e.g.
"home_goods") while actually processing disproportionately large,
round-number transactions that don't match the stated category's
typical price distribution.

Signature: merchant category mismatch (amount far outside what's typical
for that category), unusually round amounts (GenAI-generated fake pricing
tiers), repeated use of the same handful of fake merchant categories.
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

# categories real fraud rings favor for laundering fronts (low scrutiny, high ticket plausible)
FRONT_CATEGORIES = ["home_goods", "electronics", "travel", "clothing"]

# "typical" price ceiling per category in the legit data -- laundering blows past this
CATEGORY_TYPICAL_CEILING = {
    "home_goods": 300,
    "electronics": 500,
    "travel": 800,
    "clothing": 200,
}


def generate_transaction_laundering_attacks(
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
        category = random.choice(FRONT_CATEGORIES)
        ceiling = CATEGORY_TYPICAL_CEILING[category]

        # GenAI-generated "fake pricing tiers" -> suspiciously round, well above ceiling
        amount = random.choice([500, 750, 1000, 1500, 2000, 2500, 3000]) + ceiling * random.uniform(1.5, 4)
        amount = round(amount, 2)

        day_offset = random.randint(0, span_days - 1)
        ts = min_ts + timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        # location is often far from home (laundering fronts are usually online/remote)
        lat = round(random.uniform(-60, 60), 4)
        lon = round(random.uniform(-150, 150), 4)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "merchant_id": f"fakefront_{random.randint(1,300):04d}",
            "memo": "",
            "latitude": lat,
            "longitude": lon,
            "card_age_days_at_tx": profile["card_age_days"],
            "is_fraud": 1,
            "attack_type": "transaction_laundering",
        })

    return pd.DataFrame(rows)
