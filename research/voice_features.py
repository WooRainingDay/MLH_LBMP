"""Extract acoustic features from VOC-ALS recordings, one row per file.

Labels come from the filename prefix: PZ = ALS patient (1), CT = control (0).
F0 SD is the strongest single ALS discriminator in the VOC-ALS paper.

    from voice_features import extract_features
    extract_features(y, sr)  # y, sr from librosa.load(...)

CLI: python research/voice_features.py
     -> writes data/external/voc_als_features.csv
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import parselmouth
from parselmouth.praat import call

VOC_ALS_DIR = Path(__file__).parent.parent / "data" / "external" / "voc-als"
OUT_CSV = Path(__file__).parent.parent / "data" / "external" / "voc_als_features.csv"
NAME_RE = re.compile(r"^(?P<subject>[A-Z]+\d+)_(?P<task>\w+)\.wav$")
N_MFCC = 13


def label_from_subject(subject: str) -> int | None:
    if subject.startswith("PZ"):
        return 1
    if subject.startswith("CT"):
        return 0
    return None


def extract_features(y: np.ndarray, sr: int) -> dict:
    """Pitch, jitter, shimmer, HNR, formants (Praat) + MFCC stats (librosa)."""
    snd = parselmouth.Sound(y.astype(np.float64), sampling_frequency=sr)
    pitch = snd.to_pitch()
    f0 = pitch.selected_array["frequency"]
    f0 = f0[f0 > 0]

    point_process = call(snd, "To PointProcess (periodic, cc)", 75, 500)
    jitter_local = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
    shimmer_local = call(
        [snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
    )
    hnr_mean = call(snd.to_harmonicity(), "Get mean", 0, 0)

    formant = snd.to_formant_burg()
    ts = pitch.ts()
    f1 = np.array([formant.get_value_at_time(1, t) for t in ts])
    f2 = np.array([formant.get_value_at_time(2, t) for t in ts])
    f3 = np.array([formant.get_value_at_time(3, t) for t in ts])
    f1, f2, f3 = (a[~np.isnan(a)] for a in (f1, f2, f3))

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC).mean(axis=1)

    def _stat(a: np.ndarray, fn):
        return float(fn(a)) if len(a) else None

    def _nan_to_none(v: float) -> float | None:
        return None if v != v else float(v)  # Praat returns NaN, not None, when undefined

    row = {
        "f0_mean": _stat(f0, np.mean),
        "f0_sd": _stat(f0, np.std),
        "jitter_local": _nan_to_none(jitter_local),
        "shimmer_local": _nan_to_none(shimmer_local),
        "hnr_mean": _nan_to_none(hnr_mean),
        "f1_mean": _stat(f1, np.mean),
        "f1_sd": _stat(f1, np.std),
        "f2_mean": _stat(f2, np.mean),
        "f2_sd": _stat(f2, np.std),
        "f3_mean": _stat(f3, np.mean),
        "f3_sd": _stat(f3, np.std),
    }
    for i, v in enumerate(mfcc, start=1):
        row[f"mfcc{i}_mean"] = float(v)
    return row


def extract_one(path: Path) -> dict | None:
    m = NAME_RE.match(path.name)
    if not m:
        return None
    label = label_from_subject(m["subject"])
    if label is None:
        return None
    y, sr = librosa.load(str(path), sr=None)
    row = extract_features(y, sr)
    return {"subject": m["subject"], "task": m["task"], "label": label, **row}


def main() -> None:
    files = sorted(VOC_ALS_DIR.glob("*.wav"))
    if not files:
        sys.exit(f"No .wav files in {VOC_ALS_DIR} — run research/fetch_data.py first")

    rows = []
    for i, path in enumerate(files, start=1):
        row = extract_one(path)
        if row is None:
            print(f"skip (unrecognized name): {path.name}")
            continue
        rows.append(row)
        if i % 100 == 0:
            print(f"{i}/{len(files)}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(df)} rows to {OUT_CSV}")
    print(df["label"].value_counts().to_dict())


def demo() -> None:
    sr = 22050
    t = np.linspace(0, 1.0, int(sr * 1.0), endpoint=False)

    steady = extract_features(0.5 * np.sin(2 * np.pi * 150 * t), sr)
    assert 140 < steady["f0_mean"] < 160, steady
    assert steady["f0_sd"] < 5, steady

    wobbly = extract_features(0.5 * np.sin(2 * np.pi * (150 + 10 * np.sin(2 * np.pi * 3 * t)) * t), sr)
    assert wobbly["f0_sd"] > steady["f0_sd"], (wobbly, steady)

    assert label_from_subject("PZ012") == 1
    assert label_from_subject("CT005") == 0
    assert label_from_subject("XX001") is None

    print("voice_features.py: all checks passed")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()
