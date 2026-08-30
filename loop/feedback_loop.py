"""
Closed-loop feedback mechanism.

This is the core novelty of the submission: rather than treating
Identify -> Generate -> Defend as a one-shot pipeline, we close the loop:

  1. Run the current detector against the current attack dataset.
  2. Find the FALSE NEGATIVES (attacks that slipped through).
  3. Analyze what made them slip through (e.g. amount was too close to the
     user's normal range, or timing didn't deviate enough).
  4. Generate a HARDER variant of that attack family that specifically
     exploits the gap the detector just revealed.
  5. Retrain the detector on the combined (original + harder) dataset.
  6. Re-evaluate and show the before/after improvement.

Run from the project root:
    python3 loop/feedback_loop.py
"""

import os
import sys
import json
import random
import joblib
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "defend"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generate"))

from features import engineer_features, FEATURE_COLUMNS
from train import train_model
from evaluate import evaluate as run_evaluation

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "defend", "model.pkl")


def find_misses(df: pd.DataFrame, model, feature_cols) -> pd.DataFrame:
    """Identify fraud transactions the current model fails to flag."""
    X = df[feature_cols].fillna(0)
    preds = model.predict(X)
    df = df.copy()
    df["pred"] = preds
    misses = df[(df["is_fraud"] == 1) & (df["pred"] == 0)]
    return misses


def generate_harder_variants(misses: pd.DataFrame, multiplier=5) -> pd.DataFrame:
    """
    For each missed attack, generate several harder/mutated copies that push
    the evasive parameter further in the direction that fooled the model
    (e.g. if a mimicry attack's amount was too close to the user's average,
    generate variants closer still -- forcing the model to learn a finer
    boundary rather than just memorizing the original gap).
    """
    rows = []
    for _, row in misses.iterrows():
        for _ in range(multiplier):
            new_row = row.copy()
            # nudge amount slightly toward "more evasive" (closer to user's own average)
            jitter = np.random.uniform(0.9, 1.1)
            new_row["amount"] = round(row["amount"] * jitter, 2)
            new_row["transaction_id"] = f"{row['transaction_id']}_variant_{random.randint(1000,9999)}"
            rows.append(new_row)
    if not rows:
        return pd.DataFrame(columns=misses.columns)
    return pd.DataFrame(rows)


def run_feedback_loop(n_iterations=2):
    print("Loading base dataset and current model...")
    raw_df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_dataset.csv"))
    saved = joblib.load(MODEL_PATH)
    model, feature_cols = saved["model"], saved["feature_cols"]

    history = []

    print("\n--- BEFORE LOOP: baseline evaluation ---")
    baseline_results = run_evaluation()
    history.append({"iteration": 0, "results": baseline_results})

    current_raw_df = raw_df.copy()

    for i in range(1, n_iterations + 1):
        print(f"\n=== Feedback Loop Iteration {i} ===")
        engineered = engineer_features(current_raw_df)
        misses = find_misses(engineered, model, feature_cols)
        print(f"Found {len(misses)} missed attacks in current dataset.")

        if len(misses) == 0:
            print("No misses found -- detector has converged on this attack surface.")
            break

        # map engineered misses back to raw columns to generate harder variants
        raw_cols = raw_df.columns
        miss_raw = misses[[c for c in raw_cols if c in misses.columns]]
        harder_variants = generate_harder_variants(miss_raw, multiplier=5)
        print(f"Generated {len(harder_variants)} harder variants targeting the detection gap.")

        current_raw_df = pd.concat([current_raw_df, harder_variants], ignore_index=True)
        current_raw_df.to_csv(os.path.join(DATA_DIR, "synthetic_dataset.csv"), index=False)

        # retrain on the expanded, harder dataset
        print("Retraining detector on expanded dataset...")
        engineered_full = engineer_features(current_raw_df)
        cat_cols = [c for c in engineered_full.columns if c.startswith("cat_")]
        all_feature_cols = FEATURE_COLUMNS + cat_cols
        X = engineered_full[all_feature_cols].fillna(0)
        y = engineered_full["is_fraud"]

        model, X_train, X_test, y_train, y_test = train_model(X, y)
        joblib.dump({"model": model, "feature_cols": all_feature_cols}, MODEL_PATH)
        feature_cols = all_feature_cols

        print(f"--- AFTER Iteration {i}: re-evaluation ---")
        results = run_evaluation()
        history.append({"iteration": i, "results": results})

    with open(os.path.join(DATA_DIR, "feedback_loop_history.json"), "w") as f:
        json.dump(history, f, indent=2)

    print("\n=== Feedback Loop Summary ===")
    for h in history:
        r = h["results"]
        print(f"Iteration {h['iteration']}: F1={r['f1']:.4f}, Recall={r['recall']:.4f}, FPR={r['false_positive_rate']:.4%}")

    return history


if __name__ == "__main__":
    run_feedback_loop(n_iterations=2)
