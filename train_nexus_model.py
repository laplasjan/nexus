#!/usr/bin/env python3
"""Train and evaluate NEXUS AI's synthetic 24-hour reshare propensity model."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, confusion_matrix, precision_score, recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "nexus_model_data.csv"
MODEL_PATH = ROOT / "nexus_reshare_model.joblib"
METRICS_PATH = ROOT / "evaluation_metrics.json"

NUMERIC = [
    "followers", "network_degree", "prior_reshare_rate",
    "source_familiarity", "skepticism_score", "target_account_verified",
    "activity_level", "interest_bezpieczenstwo", "interest_zdrowie",
    "interest_technologia", "interest_gospodarka", "interest_spoleczenstwo",
    "interest_rozrywka", "message_emotional_intensity", "message_urgency",
    "topic_relevance", "exposure_wave", "hour_local",
]
CATEGORICAL = ["account_type", "message_topic"]
TARGET = "reshared_within_24h"
GROUP = "campaign_id"


def build_pipeline() -> Pipeline:
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    features = ColumnTransformer([
        ("numeric", numeric, NUMERIC),
        ("categorical", categorical, CATEGORICAL),
    ])
    return Pipeline([
        ("features", features),
        ("classifier", LogisticRegression(C=1.0, max_iter=2000, random_state=42)),
    ])


def prepare_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply training-time transforms to raw event rows before prediction."""
    prepared = frame.copy()
    prepared["followers"] = pd.to_numeric(prepared["followers"], errors="coerce")
    prepared["followers"] = np.log1p(prepared["followers"].clip(lower=0))
    prepared["hour_local"] = pd.to_numeric(prepared["hour_local"], errors="coerce")
    return prepared[NUMERIC + CATEGORICAL]


def safe_metric(fn, y, pred):
    try:
        return float(fn(y, pred))
    except ValueError:
        return None


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    # The target is meaningful only for confirmed exposures with an observed
    # 24-hour outcome. Unknown exposure is kept out of this supervised task.
    eligible = df[
        (df["exposure_status"] == "confirmed")
        & df[TARGET].notna()
        & df["campaign_id"].notna()
    ].copy()
    eligible[TARGET] = eligible[TARGET].astype(int)
    X = prepare_features(eligible)
    y = eligible[TARGET].to_numpy()
    groups = eligible[GROUP].astype(str).to_numpy()
    if len(eligible) == 0 or len(np.unique(y)) < 2:
        raise ValueError("Need eligible examples from both target classes.")

    # Leave-one-campaign-out predictions keep each held-out campaign unseen
    # during fitting, reducing leakage from campaign-specific patterns.
    oof_prob = np.full(len(eligible), np.nan)
    fold_details = []
    for campaign in sorted(np.unique(groups)):
        test = groups == campaign
        train = ~test
        if len(np.unique(y[train])) < 2:
            continue
        model = build_pipeline()
        model.fit(X.loc[train], y[train])
        p = model.predict_proba(X.loc[test])[:, 1]
        oof_prob[test] = p
        yt = y[test]
        fold_details.append({
            "held_out_campaign": campaign,
            "n_test": int(test.sum()),
            "positive_rate": float(yt.mean()),
            "roc_auc": safe_metric(roc_auc_score, yt, p),
            "pr_auc": safe_metric(average_precision_score, yt, p),
            "brier_score": safe_metric(brier_score_loss, yt, p),
        })

    valid = ~np.isnan(oof_prob)
    y_eval = y[valid]
    p_eval = oof_prob[valid]
    y_hat = (p_eval >= 0.5).astype(int)
    metrics = {
        "task": "Predict whether a confirmed exposed account reshared within 24 hours",
        "dataset_type": "synthetic",
        "eligible_rows": int(len(eligible)),
        "excluded_unknown_exposure_rows": int((df["exposure_status"] == "unknown").sum()),
        "campaigns": sorted(np.unique(groups).tolist()),
        "cross_validation": "leave-one-campaign-out; pooled out-of-campaign predictions",
        "evaluated_rows": int(valid.sum()),
        "positive_rate": float(y_eval.mean()),
        "baseline_positive_rate": float(y_eval.mean()),
        "roc_auc": safe_metric(roc_auc_score, y_eval, p_eval),
        "pr_auc_average_precision": safe_metric(average_precision_score, y_eval, p_eval),
        "brier_score": safe_metric(brier_score_loss, y_eval, p_eval),
        "accuracy_at_0_5": float(accuracy_score(y_eval, y_hat)),
        "balanced_accuracy_at_0_5": float(balanced_accuracy_score(y_eval, y_hat)),
        "precision_at_0_5": float(precision_score(y_eval, y_hat, zero_division=0)),
        "recall_at_0_5": float(recall_score(y_eval, y_hat, zero_division=0)),
        "confusion_matrix_labels_0_1": confusion_matrix(y_eval, y_hat, labels=[0, 1]).tolist(),
        "folds": fold_details,
    }

    final_model = build_pipeline().fit(X, y)
    joblib.dump({
        "pipeline": final_model,
        "numeric_features": NUMERIC,
        "categorical_features": CATEGORICAL,
        "target": TARGET,
        "log1p_followers": True,
        "threshold": 0.5,
    }, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"\nSaved model: {MODEL_PATH.name}")


if __name__ == "__main__":
    main()
