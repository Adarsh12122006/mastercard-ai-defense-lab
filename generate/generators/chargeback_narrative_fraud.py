"""
Attack 7: Refund/Chargeback Narrative Fraud

Simulates a cardholder who makes a perfectly ordinary-looking purchase
and then files a dispute with a GenAI-generated narrative claiming the
charge was unauthorized/item not received/etc. The GenAI angle: an LLM
can churn out thousands of superficially varied dispute narratives, but
because they're all generated from the same handful of prompt templates,
they cluster much more tightly around a small set of "narrative fingerprints"
than genuinely independent human-written disputes do -- a text-similarity
model scoring a new dispute against known fraud-narrative clusters would
see a high similarity score even though the wording looks different each
time.

Since this project's pipeline is transaction-level (not free-text), we
represent the narrative-similarity signal directly as a numeric feature
(`dispute_narrative_similarity`) rather than generating literal text --
this is the same simplification the project already documents for the
other non-tabular attack families, just now made model-ready instead of
staying "documented only."

Signature:
- dispute_filed = 1, dispute_narrative_similarity is HIGH (close to
  known fraud-narrative template clusters)
- the underlying transaction itself often looks unremarkable (normal
  amount, normal category) -- the fraud signal lives almost entirely in
  the dispute, not the purchase
- disputes are filed unusually soon after the purchase (GenAI-assisted
  fraud rings operationalize the dispute-filing step itself, so there's
  little of the natural human delay/hesitation before disputing)
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd


def generate_chargeback_narrative_fraud_attacks(
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
        # the purchase itself is deliberately unremarkable -- category the
        # user actually likes, amount close to their normal range
        category = random.choice(profile["preferred_categories"])
        amount = round(profile["avg_spend"] * random.uniform(0.8, 1.6), 2)

        day_offset = random.randint(0, span_days - 1)
        ts = min_ts + timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        lat = profile["home_lat"] + np.random.normal(0, 0.1)
        lon = profile["home_lon"] + np.random.normal(0, 0.1)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": profile["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "card_age_days_at_tx": profile["card_age_days"],
            "channel": "ecom",
            "device_id": random.choice(profile["device_pool"]) if isinstance(profile.get("device_pool"), list) else f"dev_{uuid.uuid4().hex[:8]}",
            "auth_confidence": round(float(np.random.uniform(0.85, 0.98)), 4),
            "dispute_filed": 1,
            "dispute_narrative_similarity": round(float(np.random.uniform(0.78, 0.97)), 4),
            "otp_override": 0,
            "is_fraud": 1,
            "attack_type": "chargeback_narrative_fraud",
        })

    return pd.DataFrame(rows)
