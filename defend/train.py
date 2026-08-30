"""
Trains a gradient-boosted classifier (XGBoost) to detect the fraud attacks
generated in generate/run_generation.py.

Run from the project root:
    python3 defend/train.py
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from features import engineer_features, FEATURE_COLUMNS

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "synthetic_dataset.csv")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")


def load_and_prepare(data_path=DATA_PATH):
    df = pd.read_csv(data_path)
    df = engineer_features(df)
    # merchant category dummy columns get appended dynamically; grab all "cat_*" too
    cat_cols = [c for c in df.columns if c.startswith("cat_")]
    feature_cols = FEATURE_COLUMNS + cat_cols
    X = df[feature_cols].fillna(0)
    y = df["is_fraud"]
    return X, y, feature_cols, df


def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # class imbalance: fraud is rare, so weight positives more heavily
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model, X_train, X_test, y_train, y_test


if __name__ == "__main__":
    print("Loading data and engineering features...")
    X, y, feature_cols, df = load_and_prepare()

    print(f"Dataset: {len(X)} rows, {X.shape[1]} features, fraud rate {y.mean():.3%}")

    print("Training model...")
    model, X_train, X_test, y_train, y_test = train_model(X, y)

    joblib.dump({"model": model, "feature_cols": feature_cols}, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

    # quick sanity check (full eval happens in evaluate.py)
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Train accuracy: {train_acc:.4f} | Test accuracy: {test_acc:.4f}")
