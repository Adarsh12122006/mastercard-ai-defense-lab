"""
Data Poisoning: Attack and Defense Demonstration

Simulates an attacker who has compromised part of the label-feedback
pipeline (e.g. a "mark as false positive" button abused at scale) to
slowly flip fraud labels to "legitimate" in the training data, degrading
the model over time without touching a single transaction's actual
features.

This script demonstrates both sides:
  1. ATTACK: flip a percentage of fraud labels in the training set and
     show how much detection recall degrades as a result.
  2. DEFENSE: a simple label-noise filter -- train a preliminary model,
     find training examples where the model's confident prediction
     strongly disagrees with the given label (likely mislabeled/poisoned),
     remove them, and retrain. Show the recovery.

Run from the project root, after generate/run_generation.py has produced
a dataset:
    python3 defend/poisoning_demo.py
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from features import engineer_features, FEATURE_COLUMNS
from train import train_model

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def evaluate_split(model, X, y):
    preds = model.predict(X)
    return {
        "precision": precision_score(y, preds, zero_division=0),
        "recall": recall_score(y, preds, zero_division=0),
        "f1": f1_score(y, preds, zero_division=0),
    }


def run_poisoning_demo(poison_fraction=0.40, confidence_threshold=0.3):
    print("Loading data and engineering features...")
    raw_df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_dataset.csv"))
    df = engineer_features(raw_df)
    cat_cols = [c for c in df.columns if c.startswith("cat_")]
    feature_cols = FEATURE_COLUMNS + cat_cols
    X = df[feature_cols].fillna(0)
    y = df["is_fraud"].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # --- Baseline: clean training data ---
    print("\n=== Baseline: training on clean data ===")
    clean_model, *_ = train_model(pd.concat([X_train, X_test]), pd.concat([y_train, y_test]))
    # retrain fairly on just X_train/y_train for apples-to-apples comparison
    from xgboost import XGBClassifier
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    clean_model = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, scale_pos_weight=scale_pos_weight,
        eval_metric="logloss", random_state=42,
    )
    clean_model.fit(X_train, y_train)
    clean_results = evaluate_split(clean_model, X_test, y_test)
    print(f"Clean model -> Precision: {clean_results['precision']:.4f}, "
          f"Recall: {clean_results['recall']:.4f}, F1: {clean_results['f1']:.4f}")

    # --- Attack: poison a fraction of fraud labels in the TRAINING set ---
    print(f"\n=== Attack: flipping {poison_fraction:.0%} of fraud labels in training data to 'legitimate' ===")
    y_train_poisoned = y_train.copy()
    fraud_indices = y_train[y_train == 1].index
    n_to_poison = int(len(fraud_indices) * poison_fraction)
    rng = np.random.RandomState(42)
    poisoned_indices = rng.choice(fraud_indices, size=n_to_poison, replace=False)
    y_train_poisoned.loc[poisoned_indices] = 0
    print(f"Poisoned {n_to_poison} of {len(fraud_indices)} fraud training labels.")

    scale_pos_weight_poisoned = (y_train_poisoned == 0).sum() / max((y_train_poisoned == 1).sum(), 1)
    poisoned_model = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, scale_pos_weight=scale_pos_weight_poisoned,
        eval_metric="logloss", random_state=42,
    )
    poisoned_model.fit(X_train, y_train_poisoned)
    poisoned_results = evaluate_split(poisoned_model, X_test, y_test)
    print(f"Poisoned model -> Precision: {poisoned_results['precision']:.4f}, "
          f"Recall: {poisoned_results['recall']:.4f}, F1: {poisoned_results['f1']:.4f}")
    print(f"Recall dropped by {clean_results['recall'] - poisoned_results['recall']:.4f} "
          f"due to the poisoning attack.")

    # --- Defense: label-noise filtering ---
    print(f"\n=== Defense: label-noise filter (confidence threshold {confidence_threshold}) ===")
    # Train a preliminary model on the poisoned data, then find points where
    # the model is highly confident the label is wrong (predicted fraud
    # probability is high but the given label says "legitimate" -- a strong
    # signal that label was flipped by the poisoning attack).
    prelim_proba = poisoned_model.predict_proba(X_train)[:, 1]
    suspicious_mask = (y_train_poisoned == 0) & (prelim_proba > confidence_threshold)
    n_flagged = suspicious_mask.sum()
    n_correctly_flagged = len(set(X_train[suspicious_mask].index) & set(poisoned_indices))
    print(f"Flagged {n_flagged} suspicious training examples as likely poisoned/mislabeled.")
    print(f"Of those, {n_correctly_flagged} were genuinely poisoned "
          f"({n_correctly_flagged/max(n_flagged,1):.1%} precision on the filter itself).")

    # Correct the labels rather than just dropping the rows -- dropping
    # discards the training signal entirely, while relabeling restores it,
    # which is what actually counters a label-flipping poisoning attack.
    y_train_cleaned = y_train_poisoned.copy()
    y_train_cleaned.loc[suspicious_mask[suspicious_mask].index] = 1
    X_train_cleaned = X_train

    scale_pos_weight_cleaned = (y_train_cleaned == 0).sum() / max((y_train_cleaned == 1).sum(), 1)
    defended_model = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, scale_pos_weight=scale_pos_weight_cleaned,
        eval_metric="logloss", random_state=42,
    )
    defended_model.fit(X_train_cleaned, y_train_cleaned)
    defended_results = evaluate_split(defended_model, X_test, y_test)
    print(f"Defended model -> Precision: {defended_results['precision']:.4f}, "
          f"Recall: {defended_results['recall']:.4f}, F1: {defended_results['f1']:.4f}")

    recovery_pct = (
        (defended_results["recall"] - poisoned_results["recall"]) /
        max(clean_results["recall"] - poisoned_results["recall"], 1e-6)
    )
    print(f"\nRecovered {recovery_pct:.1%} of the recall lost to the poisoning attack.")

    results = {
        "clean": clean_results,
        "poisoned": poisoned_results,
        "defended": defended_results,
        "poison_fraction": poison_fraction,
        "n_poisoned": int(n_to_poison),
        "n_flagged_by_filter": int(n_flagged),
        "n_correctly_flagged": int(n_correctly_flagged),
        "recall_recovery_pct": float(recovery_pct),
    }
    with open(os.path.join(DATA_DIR, "poisoning_demo_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {os.path.join(DATA_DIR, 'poisoning_demo_results.json')}")

    return results


if __name__ == "__main__":
    run_poisoning_demo()
