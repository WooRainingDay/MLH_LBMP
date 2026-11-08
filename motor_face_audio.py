"""Bulbar/voice test: facial lip-corner velocity + vocal pitch/formant analysis.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §2 — Bulbar
Micro-Movement & Audio Dynamics), not part of ALS RedFlag's clinical scoring
(schema.py / score.py / rules.json are untouched). Tracks lip-corner velocity
during speech (MediaPipe FaceLandmarker) and pitch perturbation + formant
stability in a sustained-vowel recording (librosa).

    from motor_face_audio import load_face_landmarks, lip_velocity, voice_jitter_and_formants
    lip_velocity(load_face_landmarks("speech.mp4"))
    voice_jitter_and_formants(y, sr)  # y, sr from librosa.load(...)
"""
from __future__ import annotations

import math
import statistics
import urllib.request
from pathlib import Path

import librosa
import numpy as np

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)
MODEL_PATH = Path(".cache/models/face_landmarker.task")

LEFT_LIP_CORNER = 61
RIGHT_LIP_CORNER = 291


def _ensure_model() -> Path:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        except OSError as e:
            raise RuntimeError(
                f"Could not download the MediaPipe face model ({MODEL_URL}). "
                "Run this once with network access before judging to warm the cache."
            ) from e
    return MODEL_PATH


def extract_lip_sample(result, timestamp_s: float) -> tuple[float, float, float, float, float] | None:
    """Pulls (timestamp_s, left_corner_x, left_corner_y, right_corner_x, right_corner_y)
    out of one FaceLandmarker result, or None if no face was detected this frame. Shared
    by the upload (file) path and the live-camera path."""
    if not result.face_landmarks:
        return None
    face = result.face_landmarks[0]
    left, right = face[LEFT_LIP_CORNER], face[RIGHT_LIP_CORNER]
    return (timestamp_s, left.x, left.y, right.x, right.y)


def new_face_landmarker(running_mode):
    """A ready-to-use FaceLandmarker for the given running_mode. Both the upload path
    and the live-camera path use VIDEO mode (see motor_live.py)."""
    import mediapipe as mp

    return mp.tasks.vision.FaceLandmarker.create_from_options(
        mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(_ensure_model())),
            running_mode=running_mode,
            num_faces=1,
        )
    )


def load_face_landmarks(video_path: str) -> list[tuple[float, float, float, float, float]]:
    """Returns (timestamp_s, left_corner_x, left_corner_y, right_corner_x, right_corner_y)
    per frame with a detected face."""
    import cv2
    import mediapipe as mp

    samples: list[tuple[float, float, float, float, float]] = []
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    with new_face_landmarker(mp.tasks.vision.RunningMode.VIDEO) as landmarker:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            timestamp_ms = int(frame_idx / fps * 1000)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            sample = extract_lip_sample(result, timestamp_ms / 1000)
            if sample:
                samples.append(sample)
            frame_idx += 1
    cap.release()
    return samples


def lip_velocity(samples: list[tuple[float, float, float, float, float]]) -> dict:
    """samples: (timestamp_s, left_x, left_y, right_x, right_y) per frame, oldest first.

    Returns {"velocities", "mean_velocity", "velocity_cv", "interpretation"}, averaging
    the two lip corners' frame-to-frame displacement speed (normalized units / s).
    """
    if len(samples) < 5:
        return _empty_lip("Need at least 5 frames with a detected face.")

    velocities = []
    for (t0, lx0, ly0, rx0, ry0), (t1, lx1, ly1, rx1, ry1) in zip(samples, samples[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        left_v = math.hypot(lx1 - lx0, ly1 - ly0) / dt
        right_v = math.hypot(rx1 - rx0, ry1 - ry0) / dt
        velocities.append((left_v + right_v) / 2)

    if len(velocities) < 3:
        return _empty_lip("Not enough consecutive frames to measure velocity.")

    mean_v = statistics.mean(velocities)
    cv = (statistics.pstdev(velocities) / mean_v) if mean_v else 0.0

    # ponytail: threshold below is an unvalidated heuristic, not a clinical cutoff.
    # Upgrade path: calibrate against real speech lip-tracking norms.
    interpretation = (
        "Lip-corner movement variability is elevated." if cv > 0.6
        else "Lip-corner movement stayed within a typical range."
    )
    return {
        "velocities": [round(v, 3) for v in velocities],
        "mean_velocity": round(mean_v, 3),
        "velocity_cv": round(cv, 3),
        "interpretation": interpretation,
    }


def _empty_lip(reason: str) -> dict:
    return {"velocities": [], "mean_velocity": None, "velocity_cv": None, "interpretation": reason}


def voice_jitter_and_formants(y: np.ndarray, sr: int) -> dict:
    """y, sr: a sustained-vowel recording from librosa.load(...).

    Returns {"jitter_pct", "f0_sd", "formant_stability_cv", "interpretation"}. Jitter is the
    mean relative frame-to-frame change in pitch period (librosa.pyin). f0_sd is the pitch
    standard deviation in Hz, the strongest single ALS discriminator in the VOC-ALS study
    (research/voice_features.py). Formant stability is the frame-to-frame variability of the
    two lowest LPC-root resonances (F1/F2 proxy).
    """
    f0, voiced_flag, _ = librosa.pyin(y, sr=sr, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"))
    voiced_f0 = f0[voiced_flag]
    if len(voiced_f0) < 5:
        return _empty_voice("Not enough sustained voiced sound detected in this clip.")

    f0_sd = float(np.std(voiced_f0))
    diffs = np.abs(np.diff(voiced_f0))
    jitter_pct = float(np.mean(diffs / voiced_f0[:-1]) * 100)

    frame_len, hop, order = int(0.03 * sr), int(0.01 * sr), 2 + sr // 1000
    f1s, f2s = [], []
    window = np.hamming(frame_len)
    for start in range(0, len(y) - frame_len, hop):
        formants = _formants_from_frame(y[start:start + frame_len] * window, sr, order)
        if len(formants) >= 2:
            f1s.append(formants[0])
            f2s.append(formants[1])

    formant_stability = None
    note = ""
    if len(f1s) >= 3:
        f1_cv = statistics.pstdev(f1s) / statistics.mean(f1s)
        f2_cv = statistics.pstdev(f2s) / statistics.mean(f2s)
        formant_stability = round((f1_cv + f2_cv) / 2, 3)
    else:
        note = " (not enough voiced frames to estimate formant stability)"

    # ponytail: thresholds below are unvalidated heuristics, not clinical cutoffs.
    # Upgrade path: calibrate against real sustained-vowel voice-pathology norms.
    flags = []
    if jitter_pct > 1.0:
        flags.append("elevated pitch jitter")
    if formant_stability is not None and formant_stability > 0.15:
        flags.append("unstable formants")
    interpretation = ("; ".join(flags) if flags else "Pitch and formants stayed stable.") + note

    return {
        "jitter_pct": round(jitter_pct, 2),
        "f0_sd": round(f0_sd, 1),
        "formant_stability_cv": formant_stability,
        "interpretation": interpretation,
    }


def _empty_voice(reason: str) -> dict:
    return {"jitter_pct": None, "f0_sd": None, "formant_stability_cv": None, "interpretation": reason}


_VOICE_MODEL_PATH = Path(__file__).parent / "models" / "voice_baseline.joblib"
_voice_model_cache: dict | None = None


def voice_tier_b(y: np.ndarray, sr: int) -> dict | None:
    """Tier B: VOC-ALS-trained voice model (research/train_voice.py). Returns None if
    models/voice_baseline.joblib is missing (e.g. a fresh clone/deploy) - callers must
    fall back to voice_jitter_and_formants (Tier C heuristic) in that case."""
    global _voice_model_cache
    if _voice_model_cache is None:
        if not _VOICE_MODEL_PATH.exists():
            return None
        import joblib

        # joblib.load is pickle-based; safe here because this file is produced locally
        # by research/train_voice.py (gitignored, never user-uploaded or fetched over the network).
        _voice_model_cache = joblib.load(_VOICE_MODEL_PATH)

    from research.voice_features import extract_features

    feats = extract_features(y, sr)
    cols = _voice_model_cache["feature_cols"]
    if any(feats[c] is None for c in cols):
        return None
    x = np.array([[feats[c] for c in cols]])
    proba = float(_voice_model_cache["model"].predict_proba(x)[0, 1])
    return {
        "risk_probability": round(proba, 3),
        "tier": "B",
        "source": "VOC-ALS n=1224, subject-level CV AUC 0.64 (research/train_voice.py)",
    }


def _formants_from_frame(frame: np.ndarray, sr: int, order: int) -> list[float]:
    """LPC-root formant estimate for one audio frame. Returns ascending frequencies (Hz)."""
    if not np.any(frame):
        return []
    try:
        a = librosa.lpc(frame.astype(float), order=order)
    except FloatingPointError:
        return []
    roots = np.roots(a)
    roots = roots[np.imag(roots) >= 0]
    freqs = np.arctan2(np.imag(roots), np.real(roots)) * (sr / (2 * np.pi))
    return sorted(f for f in freqs if 90 < f < sr / 2)


def demo() -> None:
    sr = 22050
    t = np.linspace(0, 1.0, int(sr * 1.0), endpoint=False)

    steady = voice_jitter_and_formants(0.5 * np.sin(2 * np.pi * 150 * t), sr)
    assert steady["jitter_pct"] < 1.0, steady
    assert steady["f0_sd"] < 5, steady
    assert "stable" in steady["interpretation"], steady

    wobbly = voice_jitter_and_formants(0.5 * np.sin(2 * np.pi * (150 + 3 * np.sin(2 * np.pi * 10 * t)) * t), sr)
    assert wobbly["jitter_pct"] > steady["jitter_pct"], wobbly
    assert wobbly["f0_sd"] > steady["f0_sd"], wobbly

    tier_b = voice_tier_b(0.5 * np.sin(2 * np.pi * 150 * t), sr)
    if _VOICE_MODEL_PATH.exists():
        assert tier_b is not None and 0 <= tier_b["risk_probability"] <= 1, tier_b
    else:
        assert tier_b is None, tier_b

    steady_lips = lip_velocity([(i * 0.03, 0.3, 0.5, 0.7, 0.5) for i in range(10)])
    assert steady_lips["mean_velocity"] == 0.0, steady_lips

    moving_lips = lip_velocity([(i * 0.03, 0.3 + 0.02 * (i % 2), 0.5, 0.7, 0.5) for i in range(10)])
    assert moving_lips["mean_velocity"] > 0, moving_lips

    too_few = lip_velocity([(0.0, 0.0, 0.0, 0.0, 0.0)])
    assert too_few["mean_velocity"] is None, too_few

    print("motor_face_audio.py: all checks passed")


if __name__ == "__main__":
    demo()
