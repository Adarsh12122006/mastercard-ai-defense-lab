"""
Orchestrates the full synthetic dataset generation:
  1. Generate base legitimate transactions + user profiles
  2. Inject each of the 8 attack types from the taxonomy
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
from generators.deepfake_voice_ato import generate_deepfake_voice_ato_attacks
from generators.phishing_ato import generate_phishing_ato_attacks
from generators.chargeback_narrative_fraud import generate_chargeback_narrative_fraud_attacks
from generators.biometric_spoofing import generate_biometric_spoofing_attacks

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def build_dataset(
    n_users=500,
    n_legit_txns=20000,
    n_behavioral_mimicry=60,
    n_card_testing_campaigns=40,
    n_synthetic_identities=50,
    n_laundering=60,
    n_deepfake_voice_ato=45,
    n_phishing_ato=45,
    n_chargeback_narrative_fraud=55,
    n_biometric_spoofing=45,
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

    print("Generating Attack 5: Deepfake Voice ATO...")
    deepfake_df = generate_deepfake_voice_ato_attacks(profiles, legit_df, n_attacks=n_deepfake_voice_ato)

    print("Generating Attack 6: Personalized Phishing ATO...")
    phishing_df = generate_phishing_ato_attacks(profiles, legit_df, n_attacks=n_phishing_ato)

    print("Generating Attack 7: Chargeback Narrative Fraud...")
    chargeback_df = generate_chargeback_narrative_fraud_attacks(profiles, legit_df, n_attacks=n_chargeback_narrative_fraud)

    print("Generating Attack 8: Biometric Spoofing...")
    biometric_df = generate_biometric_spoofing_attacks(profiles, legit_df, n_attacks=n_biometric_spoofing)

    full_df = pd.concat(
        [
            legit_df, mimicry_df, card_testing_df, synth_id_df, laundering_df,
            deepfake_df, phishing_df, chargeback_df, biometric_df,
        ],
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
