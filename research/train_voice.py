"""Baseline ALS voice classifier on VOC-ALS features (research/voice_features.py).

Subject-level stratified k-fold only. A subject has up to 8 recordings; a
recording-level split leaks the speaker into the test set and inflates
accuracy (the likely cause of 98-99% figures in some papers).

CLI: python research/train_voice.py
     -> prints CV AUC/sensitivity/specificity (95% CI) for F0 SD alone
        (sanity check against the VOC-ALS paper), logistic regression and
        random forest on all features, and saves the better model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
N_SPLITS = 5
FEATURES_CSV = Path(__file__).parent.parent / "data" / "external" / "voc_als_features.csv"
MODEL_PATH = Path(__file__).parent.parent / "models" / "voice_baseline.joblib"
FEATURE_COLS = [
    "f0_mean", "f0_sd", "jitter_local", "shimmer_local", "hnr_mean",
    "f1_mean", "f1_sd", "f2_mean", "f2_sd", "f3_mean", "f3_sd",
] + [f"mfcc{i}_mean" for i in range(1, 14)]


def _ci95(values) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    se = arr.std(ddof=1) / np.sqrt(len(arr)) if len(arr) > 1 else 0.0
    return mean, mean - 1.96 * se, mean + 1.96 * se


def cross_validate(X: np.ndarray, y: np.ndarray, groups: np.ndarray, make_model) -> dict:
    """Subject-level stratified CV. Returns mean AUC/sensitivity/specificity + AUC 95% CI."""
    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    aucs, sens, spec = [], [], []
    for train_idx, test_idx in cv.split(X, y, groups):
        model = make_model()
        model.fit(X[train_idx], y[train_idx])
        proba = model.predict_proba(X[test_idx])[:, 1]
        yt = y[test_idx]
        aucs.append(roc_auc_score(yt, proba))
        pred = (proba >= 0.5).astype(int)
        tp, fn = ((pred == 1) & (yt == 1)).sum(), ((pred == 0) & (yt == 1)).sum()
        tn, fp = ((pred == 0) & (yt == 0)).sum(), ((pred == 1) & (yt == 0)).sum()
        sens.append(tp / (tp + fn) if (tp + fn) else np.nan)
        spec.append(tn / (tn + fp) if (tn + fp) else np.nan)
    auc_mean, auc_lo, auc_hi = _ci95(aucs)
    return {
        "auc_mean": auc_mean,
        "auc_ci": (auc_lo, auc_hi),
        "sens_mean": float(np.nanmean(sens)),
        "spec_mean": float(np.nanmean(spec)),
    }


def _report(name: str, result: dict) -> None:
    lo, hi = result["auc_ci"]
    print(
        f"{name:20s} AUC {result['auc_mean']:.3f} (95% CI {lo:.3f}-{hi:.3f})"
        f"  sens {result['sens_mean']:.2f}  spec {result['spec_mean']:.2f}"
    )


def main() -> None:
    if not FEATURES_CSV.exists():
        sys.exit(f"{FEATURES_CSV} not found - run research/voice_features.py first")

    df = pd.read_csv(FEATURES_CSV).dropna(subset=FEATURE_COLS)
    X, y, groups = df[FEATURE_COLS].to_numpy(), df["label"].to_numpy(), df["subject"].to_numpy()

    n_als = df.loc[df["label"] == 1, "subject"].nunique()
    n_ctrl = df.loc[df["label"] == 0, "subject"].nunique()
    print(f"{len(df)} recordings, {df['subject'].nunique()} subjects ({n_als} ALS, {n_ctrl} control)")

    f0sd_result = cross_validate(
        df[["f0_sd"]].to_numpy(), y, groups,
        lambda: make_pipeline(StandardScaler(), LogisticRegression(random_state=SEED)),
    )
    _report("F0 SD alone", f0sd_result)
    if f0sd_result["auc_mean"] <= 0.55:
        print("WARNING: F0 SD alone AUC is not clearly above 0.5 - check the pipeline before trusting the full model.")

    candidates = {
        "logistic_regression": lambda: make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEED)
        ),
        "random_forest": lambda: RandomForestClassifier(n_estimators=300, random_state=SEED),
    }
    best_name, best_auc, best_factory = None, -1.0, None
    for name, factory in candidates.items():
        result = cross_validate(X, y, groups, factory)
        _report(name, result)
        if result["auc_mean"] > best_auc:
            best_name, best_auc, best_factory = name, result["auc_mean"], factory

    final_model = best_factory()
    final_model.fit(X, y)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"model": final_model, "feature_cols": FEATURE_COLS}, MODEL_PATH)
    print(f"Saved best model ({best_name}, AUC {best_auc:.3f}) to {MODEL_PATH}")


def demo() -> None:
    mean, lo, hi = _ci95([0.80, 0.82, 0.78, 0.81, 0.79])
    assert lo < mean < hi, (lo, mean, hi)
    print("train_voice.py: all checks passed")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()
