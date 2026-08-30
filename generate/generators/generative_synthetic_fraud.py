"""
Attack 7: Generative-Model-Based Synthetic Fraud

Simulates an attacker who trains a generative model on leaked/observed
transaction data to produce fraud that is STATISTICALLY indistinguishable
from legitimate transactions -- the goal behind a real GAN-based fraud
generator, but implemented here with a Gaussian Mixture Model (GMM) rather
than a full GAN. This is a deliberate scope decision: a GMM fit to the
legitimate amount/timing distribution captures the same objective (sample
from the same distribution as real data) without the training time, GPU
dependency, and instability of a real adversarial network -- appropriate
for a hackathon timeline while still representing the attack faithfully.

The resulting fraud is *not* an obvious statistical outlier like the other
attacks (no extreme z-scores, no round numbers, no velocity spikes) --
its only "tell" is that it's assigned to a DIFFERENT user than the one
whose distribution it was sampled from, i.e. it's a stolen-card-style
fraud where the transaction amount/timing pattern looks perfectly normal
in isolation, just not for THIS cardholder.
"""

import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture


def generate_gmm_synthetic_fraud(
    profiles: pd.DataFrame,
    legit_df: pd.DataFrame,
    n_attacks: int = 45,
) -> pd.DataFrame:
    rows = []
    profiles_list = profiles.to_dict("records")
    min_ts = legit_df["timestamp"].min()
    max_ts = legit_df["timestamp"].max()
    span_days = max((max_ts - min_ts).days, 1)

    # Fit a GMM on the overall legitimate amount distribution (log-space,
    # since spend is log-normal) -- this is the attacker's "trained generator".
    log_amounts = np.log(legit_df["amount"].clip(lower=1.0)).values.reshape(-1, 1)
    gmm = GaussianMixture(n_components=4, random_state=42)
    gmm.fit(log_amounts)

    # pick pairs: (victim whose card is used) x (donor profile whose amount/category
    # pattern is sampled to generate a plausible-looking but foreign transaction)
    victims = random.sample(profiles_list, min(n_attacks, len(profiles_list)))

    for victim in victims:
        donor = random.choice(profiles_list)  # different behavioral pattern
        category = random.choice(donor["preferred_categories"])

        sampled_log_amount, _ = gmm.sample(1)
        amount = round(float(np.exp(sampled_log_amount[0][0])), 2)
        amount = min(amount, 3000.0)

        day_offset = random.randint(0, span_days - 1)
        # timing sampled from donor's typical hour, not victim's -- looks
        # like a "normal shopper" pattern, just not THIS victim's pattern
        hour = int(np.clip(np.random.normal(loc=donor["active_hour_center"], scale=2.0), 0, 23))
        ts = min_ts + timedelta(days=day_offset, hours=hour, minutes=random.randint(0, 59))

        # location: near donor's home region (stolen card used in a different city)
        lat = donor["home_lat"] + np.random.normal(0, 0.1)
        lon = donor["home_lon"] + np.random.normal(0, 0.1)

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": victim["user_id"],
            "timestamp": ts,
            "amount": amount,
            "merchant_category": category,
            "merchant_id": f"merch_{category}_{random.randint(1,120):03d}",
            "memo": "",
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "card_age_days_at_tx": victim["card_age_days"],
            "is_fraud": 1,
            "attack_type": "generative_synthetic_fraud",
        })

    return pd.DataFrame(rows)
