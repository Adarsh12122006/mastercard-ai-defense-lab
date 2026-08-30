"""
Adversarial Training Orchestrator

The adversarial_evasion attack (generate/generators/adversarial_evasion.py)
needs a TRAINED model to probe before it can craft evasive transactions --
so it cannot be generated in the same pass as the other 8 attacks. This
script implements the two-phase process:

  Phase 1: train a BASELINE model on everything except adversarial evasion.
  Phase 2: use that baseline model as the attacker's target -- probe it to
           find its decision boundary per-user and craft evasive transactions.
  Phase 3: fold those adversarial examples back into the training data and
           retrain -- this is "adversarial training", a standard technique
           for hardening models against examples specifically designed to
           fool them.

Run from the project root, AFTER generate/run_generation.py and
defend/train.py have produced an initial dataset + model:

    python3 loop/adversarial_loop.py
"""

import os
import sys
import joblib
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "defend"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generate"))

from features import engineer_features, FEATURE_COLUMNS
from train import train_model
from evaluate import evaluate as run_evaluation
from generators.adversarial_evasion import generate_adversarial_evasion_attacks
from base_transactions import make_user_profiles

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "defend", "model.pkl")


def run_adversarial_training(n_evasion_attacks=40):
    print("=== Phase 1: baseline evaluation (before adversarial examples) ===")
    baseline_results = run_evaluation()

    print("\n=== Phase 2: attacker probes the baseline model to find its decision boundary ===")
    raw_df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_dataset.csv"))
    raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"], format="mixed")

    profiles = pd.read_csv(os.path.join(DATA_DIR, "user_profiles.csv"))
    profiles["preferred_categories"] = profiles["preferred_categories"].apply(eval)

    saved = joblib.load(MODEL_PATH)
    model, feature_cols = saved["model"], saved["feature_cols"]

    legit_df = raw_df[raw_df["is_fraud"] == 0]

    evasion_df = generate_adversarial_evasion_attacks(
        profiles=profiles,
        legit_df=legit_df,
        model=model,
        feature_cols=feature_cols,
        engineer_features_fn=engineer_features,
        n_attacks=n_evasion_attacks,
    )
    print(f"Generated {len(evasion_df)} adversarial evasion transactions targeting the baseline model.")

    # check how many the BASELINE model actually misses (should be most/all,
    # since they were specifically crafted to evade it)
    combined_for_check = pd.concat([raw_df, evasion_df], ignore_index=True)
    engineered_check = engineer_features(combined_for_check)
    cat_cols = [c for c in engineered_check.columns if c.startswith("cat_")]
    check_feature_cols = FEATURE_COLUMNS + cat_cols
    for c in check_feature_cols:
        if c not in engineered_check.columns:
            engineered_check[c] = 0
    evasion_mask = engineered_check["attack_type"] == "adversarial_evasion"
    X_evasion = engineered_check.loc[evasion_mask, check_feature_cols].fillna(0)
    baseline_catches = model.predict(X_evasion).sum()
    print(f"Baseline model caught {baseline_catches}/{len(X_evasion)} of these BEFORE adversarial training "
          f"(expected to be low -- that's the point of the attack).")

    print("\n=== Phase 3: adversarial retraining (fold evasion examples into training data) ===")
    full_df = pd.concat([raw_df, evasion_df], ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    full_df.to_csv(os.path.join(DATA_DIR, "synthetic_dataset.csv"), index=False)

    engineered_full = engineer_features(full_df)
    cat_cols = [c for c in engineered_full.columns if c.startswith("cat_")]
    all_feature_cols = FEATURE_COLUMNS + cat_cols
    X = engineered_full[all_feature_cols].fillna(0)
    y = engineered_full["is_fraud"]

    new_model, X_train, X_test, y_train, y_test = train_model(X, y)
    joblib.dump({"model": new_model, "feature_cols": all_feature_cols}, MODEL_PATH)

    print("\n=== Post-adversarial-training evaluation ===")
    post_results = run_evaluation()

    print("\n=== Adversarial Training Summary ===")
    print(f"Baseline F1: {baseline_results['f1']:.4f} | Post-adversarial-training F1: {post_results['f1']:.4f}")
    ae_detection = post_results["per_attack_type"].get("adversarial_evasion", {})
    print(f"Adversarial evasion detection rate BEFORE hardening: "
          f"{baseline_catches}/{len(X_evasion)} ({baseline_catches/max(len(X_evasion),1):.1%})")
    print(f"Adversarial evasion detection rate AFTER hardening: "
          f"{ae_detection.get('detected', 0)}/{ae_detection.get('total', 0)} "
          f"({ae_detection.get('detection_rate', 0):.1%})")

    return {"baseline": baseline_results, "post_adversarial_training": post_results,
            "pre_hardening_evasion_catches": int(baseline_catches), "pre_hardening_evasion_total": int(len(X_evasion))}


if __name__ == "__main__":
    run_adversarial_training()
