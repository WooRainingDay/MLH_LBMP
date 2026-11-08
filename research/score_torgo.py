"""Score the frozen voice_baseline model on TORGO: an external test set, not a
retrain. Two caveats the plan requires reporting, not resampling away:
TORGO mixes ALS with cerebral palsy speakers ("dysarthric" vs control, not
ALS-specific), and its head-mounted mic is a different recording condition
than VOC-ALS's smartphone app or this app's browser mic.

CLI: python research/score_torgo.py
     -> prints TORGO AUC with the frozen VOC-ALS model, for comparison against
        the subject-level CV AUC research/train_voice.py reports
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import joblib
import librosa
import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from voice_features import extract_features  # noqa: E402

TORGO_DIR = Path(__file__).parent.parent / "data" / "external" / "torgo"
MODEL_PATH = Path(__file__).parent.parent / "models" / "voice_baseline.joblib"
SPEAKER_RE = re.compile(r"^([FM])(C?)(\d+)$")


def is_dysarthric(speaker_dir_name: str) -> bool | None:
    """Speaker folder name like F01 (dysarthric) or FC01 (control)."""
    m = SPEAKER_RE.match(speaker_dir_name)
    if not m:
        return None
    return m.group(2) == ""


def main() -> None:
    if not MODEL_PATH.exists():
        sys.exit(f"{MODEL_PATH} not found - run research/train_voice.py first")
    # joblib.load is pickle-based; safe here because this file is produced locally
    # by research/train_voice.py (gitignored, never user-uploaded or fetched over the network).
    bundle = joblib.load(MODEL_PATH)
    model, cols = bundle["model"], bundle["feature_cols"]

    speaker_dirs = sorted(d for d in TORGO_DIR.iterdir() if d.is_dir() and SPEAKER_RE.match(d.name))
    if not speaker_dirs:
        sys.exit(f"No speaker folders under {TORGO_DIR} - extract at least one TORGO archive first")

    rows = []
    for speaker_dir in speaker_dirs:
        label = is_dysarthric(speaker_dir.name)
        if label is None:
            continue
        for wav_path in speaker_dir.glob("Session*/wav_headMic/*.wav"):
            try:
                y, sr = librosa.load(str(wav_path), sr=None)
                if len(y) < sr * 0.3:
                    continue
                feats = extract_features(y, sr)
            except Exception:
                continue
            if any(feats[c] is None for c in cols):
                continue
            rows.append((speaker_dir.name, int(label), [feats[c] for c in cols]))

    if not rows:
        sys.exit("No usable TORGO recordings found")

    speakers, y_true, X = zip(*rows)
    X, y_true = np.array(X), np.array(y_true)
    proba = model.predict_proba(X)[:, 1]
    auc = roc_auc_score(y_true, proba)

    unique_speakers = set(speakers)
    n_dys = sum(1 for s in unique_speakers if is_dysarthric(s))
    n_ctrl = len(unique_speakers) - n_dys
    print(f"{len(rows)} recordings, {len(unique_speakers)} speakers ({n_dys} dysarthric, {n_ctrl} control)")
    print(f"TORGO external AUC: {auc:.3f} (frozen VOC-ALS model, no retraining)")
    print(
        "Caveats: TORGO mixes ALS + cerebral palsy speakers (dysarthric vs control, "
        "not ALS-specific); head-mounted mic, different recording condition than "
        "VOC-ALS's smartphone app or this app's browser mic."
    )


def demo() -> None:
    assert is_dysarthric("F01") is True
    assert is_dysarthric("FC01") is False
    assert is_dysarthric("M05") is True
    assert is_dysarthric("MC03") is False
    assert is_dysarthric("garbage") is None
    print("score_torgo.py: all checks passed")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()
