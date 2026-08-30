"""
Evaluates the trained model: precision, recall, F1, AUC overall, plus a
breakdown of detection rate PER ATTACK TYPE (this is what proves diversity
of detection, not just an aggregate score).

Run from the project root:
    python3 defend/evaluate.py
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report,
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from features import engineer_features, FEATURE_COLUMNS
from train import load_and_prepare, MODEL_PATH

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "evaluation_results.json")


def evaluate():
    X, y, feature_cols, df = load_and_prepare()
    saved = joblib.load(MODEL_PATH)
    model, feature_cols = saved["model"], saved["feature_cols"]

    X = df[feature_cols].fillna(0)
    y_pred_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    precision = precision_score(y, y_pred)
    recall = recall_score(y, y_pred)
    f1 = f1_score(y, y_pred)
    auc = roc_auc_score(y, y_pred_proba)

    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    false_positive_rate = fp / (fp + tn)

    print("=== Overall Detection Performance ===")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"AUC:       {auc:.4f}")
    print(f"False Positive Rate (on legit txns): {false_positive_rate:.4%}")

    # per-attack-type detection rate (recall per attack family)
    df["pred"] = y_pred
    per_attack = {}
    print("\n=== Detection Rate by Attack Type ===")
    for attack_type in df[df["is_fraud"] == 1]["attack_type"].unique():
        subset = df[df["attack_type"] == attack_type]
        detected = subset["pred"].sum()
        total = len(subset)
        rate = detected / total if total > 0 else 0
        per_attack[attack_type] = {"detected": int(detected), "total": int(total), "detection_rate": rate}
        print(f"  {attack_type:25s}: {detected}/{total} detected ({rate:.1%})")

    results = {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc,
        "false_positive_rate": false_positive_rate,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "per_attack_type": per_attack,
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")

    return results


if __name__ == "__main__":
    evaluate()
