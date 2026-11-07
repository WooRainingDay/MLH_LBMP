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


def load_face_landmarks(video_path: str) -> list[tuple[float, float, float, float, float]]:
    """Returns (timestamp_s, left_corner_x, left_corner_y, right_corner_x, right_corner_y)
    per frame with a detected face."""
    import cv2
    import mediapipe as mp

    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(_ensure_model())),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_faces=1,
    )
    samples: list[tuple[float, float, float, float, float]] = []
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as landmarker:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            timestamp_ms = int(frame_idx / fps * 1000)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            if result.face_landmarks:
                face = result.face_landmarks[0]
                left, right = face[LEFT_LIP_CORNER], face[RIGHT_LIP_CORNER]
                samples.append((timestamp_ms / 1000, left.x, left.y, right.x, right.y))
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

    Returns {"jitter_pct", "formant_stability_cv", "interpretation"}. Jitter is the mean
    relative frame-to-frame change in pitch period (librosa.pyin). Formant stability is
    the frame-to-frame variability of the two lowest LPC-root resonances (F1/F2 proxy).
    """
    f0, voiced_flag, _ = librosa.pyin(y, sr=sr, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"))
    voiced_f0 = f0[voiced_flag]
    if len(voiced_f0) < 5:
        return _empty_voice("Not enough sustained voiced sound detected in this clip.")

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
        "formant_stability_cv": formant_stability,
        "interpretation": interpretation,
    }


def _empty_voice(reason: str) -> dict:
    return {"jitter_pct": None, "formant_stability_cv": None, "interpretation": reason}


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
    assert "stable" in steady["interpretation"], steady

    wobbly = voice_jitter_and_formants(0.5 * np.sin(2 * np.pi * (150 + 3 * np.sin(2 * np.pi * 10 * t)) * t), sr)
    assert wobbly["jitter_pct"] > steady["jitter_pct"], wobbly

    steady_lips = lip_velocity([(i * 0.03, 0.3, 0.5, 0.7, 0.5) for i in range(10)])
    assert steady_lips["mean_velocity"] == 0.0, steady_lips

    moving_lips = lip_velocity([(i * 0.03, 0.3 + 0.02 * (i % 2), 0.5, 0.7, 0.5) for i in range(10)])
    assert moving_lips["mean_velocity"] > 0, moving_lips

    too_few = lip_velocity([(0.0, 0.0, 0.0, 0.0, 0.0)])
    assert too_few["mean_velocity"] is None, too_few

    print("motor_face_audio.py: all checks passed")


if __name__ == "__main__":
    demo()
