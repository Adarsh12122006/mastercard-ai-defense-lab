"""
Orchestrates the full synthetic dataset generation:
  1. Generate base legitimate transactions + user profiles
  2. Inject each of the 4 attack types
  3. Combine into a single labeled dataset (data/synthetic_dataset.csv)

Run from the project root:
    python3 generate/run_generation.py
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pandas as pd

from base_transactions import make_user_profiles, generate_legit_transactions
from generators.behavioral_mimicry import generate_behavioral_mimicry_attacks
from generators.card_testing import generate_card_testing_attacks
from generators.synthetic_identity import generate_synthetic_identity_attacks
from generators.transaction_laundering import generate_transaction_laundering_attacks
from generators.prompt_injection import generate_prompt_injection_attacks
from generators.generative_synthetic_fraud import generate_gmm_synthetic_fraud
from generators.storefront_churn import generate_storefront_churn_attacks
from generators.loyalty_abuse import generate_loyalty_abuse_attacks

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def build_dataset(
    n_users=500,
    n_legit_txns=20000,
    n_behavioral_mimicry=60,
    n_card_testing_campaigns=40,
    n_synthetic_identities=50,
    n_laundering=60,
    n_prompt_injection=35,
    n_generative_fraud=45,
    n_storefronts=20,
    n_loyalty_bot_accounts=60,
    seed_days=60,
):
    print("Generating user profiles...")
    profiles = make_user_profiles(n_users=n_users)

    print("Generating legitimate baseline transactions...")
    legit_df = generate_legit_transactions(
        profiles, n_transactions=n_legit_txns,
        start_date=datetime(2026, 6, 1), days=seed_days,
    )

    print("Generating Attack 1: Behavioral Mimicry...")
    mimicry_df = generate_behavioral_mimicry_attacks(profiles, legit_df, n_attacks=n_behavioral_mimicry)

    print("Generating Attack 2: Card Testing...")
    card_testing_df = generate_card_testing_attacks(profiles, legit_df, n_campaigns=n_card_testing_campaigns)

    print("Generating Attack 3: Synthetic Identity...")
    synth_id_df = generate_synthetic_identity_attacks(legit_df, n_identities=n_synthetic_identities)

    print("Generating Attack 4: Transaction Laundering...")
    laundering_df = generate_transaction_laundering_attacks(profiles, legit_df, n_attacks=n_laundering)

    print("Generating Attack 6: Prompt Injection (fraud-ops AI targeting)...")
    injection_df = generate_prompt_injection_attacks(profiles, legit_df, n_attacks=n_prompt_injection)

    print("Generating Attack 7: Generative-Model-Based Synthetic Fraud...")
    generative_df = generate_gmm_synthetic_fraud(profiles, legit_df, n_attacks=n_generative_fraud)

    print("Generating Attack 8: Autonomous Storefront Churn...")
    churn_df = generate_storefront_churn_attacks(profiles, legit_df, n_storefronts=n_storefronts)

    print("Generating Attack 9: Loyalty/Rewards Program Abuse...")
    loyalty_df = generate_loyalty_abuse_attacks(legit_df, n_bot_accounts=n_loyalty_bot_accounts)

    full_df = pd.concat(
        [legit_df, mimicry_df, card_testing_df, synth_id_df, laundering_df,
         injection_df, generative_df, churn_df, loyalty_df],
        ignore_index=True,
    ).sort_values("timestamp").reset_index(drop=True)

    return full_df, profiles


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    full_df, profiles = build_dataset()

    out_path = os.path.join(DATA_DIR, "synthetic_dataset.csv")
    full_df.to_csv(out_path, index=False)

    print("\n=== Dataset Summary ===")
    print(f"Total transactions: {len(full_df)}")
    print(f"Fraud rate: {full_df['is_fraud'].mean():.3%}")
    print("\nBreakdown by attack type:")
    print(full_df["attack_type"].value_counts())
    print(f"\nSaved to: {out_path}")
