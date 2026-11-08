"""CV finger-tap motor test: real MediaPipe hand-landmark tracking.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §1 — Upper Motor
Neuron Sign: Spasticity & Micro-Tremors), not part of ALS RedFlag's clinical
scoring (schema.py / score.py / rules.json are untouched). Measures frequency
jitter, micro-hesitations, and rhythm degradation in a thumb-to-index tapping
trial — upper motor neuron disinhibition can show up as rhythm degradation
before raw strength loss is obvious.

    from motor_cv import load_hand_landmarks, tap_rhythm
    samples = load_hand_landmarks("clip.mp4")  # [(thumb_x, index_x, t_s), ...]
    tap_rhythm(samples)
"""
from __future__ import annotations

import statistics
import urllib.request
from pathlib import Path

from scipy.signal import find_peaks

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)
MODEL_PATH = Path(".cache/models/hand_landmarker.task")

THUMB_TIP = 4
INDEX_TIP = 8


def _ensure_model() -> Path:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        except OSError as e:
            raise RuntimeError(
                f"Could not download the MediaPipe hand model ({MODEL_URL}). "
                "Run this once with network access before judging to warm the cache."
            ) from e
    return MODEL_PATH


def extract_hand_sample(result, timestamp_s: float) -> tuple[float, float, float] | None:
    """Pulls (thumb_tip_x, index_tip_x, timestamp_s) out of one HandLandmarker result,
    or None if no hand was detected this frame. Shared by the upload (file) path and the
    live-camera path so both feed identical samples into tap_rhythm()."""
    if not result.hand_landmarks:
        return None
    hand = result.hand_landmarks[0]
    return (hand[THUMB_TIP].x, hand[INDEX_TIP].x, timestamp_s)


def new_landmarker(running_mode):
    """A ready-to-use HandLandmarker for the given running_mode. Both the upload path
    and the live-camera path use VIDEO mode (see motor_live.py)."""
    import mediapipe as mp

    return mp.tasks.vision.HandLandmarker.create_from_options(
        mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(_ensure_model())),
            running_mode=running_mode,
            num_hands=1,
        )
    )


def load_hand_landmarks(video_path: str) -> list[tuple[float, float, float]]:
    """Returns (thumb_tip_x, index_tip_x, timestamp_s) per frame with a detected hand."""
    import cv2
    import mediapipe as mp

    samples: list[tuple[float, float, float]] = []
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    with new_landmarker(mp.tasks.vision.RunningMode.VIDEO) as landmarker:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            timestamp_ms = int(frame_idx / fps * 1000)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            sample = extract_hand_sample(result, timestamp_ms / 1000)
            if sample:
                samples.append(sample)
            frame_idx += 1
    cap.release()
    return samples


def tap_rhythm(samples: list[tuple[float, float, float]]) -> dict:
    """samples: (thumb_tip_x, index_tip_x, timestamp_s) per frame, oldest first.

    A "tap" is a local minimum in thumb-index distance (fingers closing together).
    Returns {"intervals_ms", "jitter_cv", "hesitation_count", "slope_ms_per_tap",
    "interpretation"}.
    """
    if len(samples) < 10:
        return _empty("Need at least 10 frames with a detected hand.")

    times = [s[2] for s in samples]
    distances = [abs(s[0] - s[1]) for s in samples]
    peak_idx, _ = find_peaks([-d for d in distances], distance=3)
    if len(peak_idx) < 3:
        return _empty("Could not detect at least 3 taps in this clip.")

    tap_times = [times[i] for i in peak_idx]
    intervals_ms = [(tap_times[i] - tap_times[i - 1]) * 1000 for i in range(1, len(tap_times))]
    return _score(intervals_ms)


def _empty(reason: str) -> dict:
    return {
        "intervals_ms": [],
        "jitter_cv": None,
        "hesitation_count": 0,
        "slope_ms_per_tap": None,
        "interpretation": reason,
    }


def _score(intervals_ms: list[float]) -> dict:
    n = len(intervals_ms)
    mean_interval = statistics.mean(intervals_ms)
    jitter_cv = (statistics.pstdev(intervals_ms) / mean_interval) if mean_interval else 0.0
    median_interval = statistics.median(intervals_ms)
    hesitation_count = sum(1 for v in intervals_ms if v > 1.5 * median_interval)

    xs = list(range(n))
    mean_x = sum(xs) / n
    num = sum((x - mean_x) * (y - mean_interval) for x, y in zip(xs, intervals_ms))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den else 0.0

    # ponytail: thresholds below are an unvalidated heuristic, not a clinical cutoff
    # (no UPDRS-style tapping norms baked in). Upgrade path: calibrate against real
    # finger-tapping-test data before using for anything beyond an exploratory demo.
    flags = []
    if jitter_cv > 0.3:
        flags.append("high tap-to-tap jitter")
    if hesitation_count > 0:
        flags.append(f"{hesitation_count} micro-hesitation(s)")
    if slope > 15:
        flags.append("rhythm slowed over the trial")
    interpretation = "; ".join(flags) if flags else "Rhythm stayed steady, low jitter, no hesitations."

    return {
        "intervals_ms": [round(v, 1) for v in intervals_ms],
        "jitter_cv": round(jitter_cv, 3),
        "hesitation_count": hesitation_count,
        "slope_ms_per_tap": round(slope, 1),
        "interpretation": interpretation,
    }


def _synthetic_samples(tap_times: list[float], fps: float = 100.0) -> list[tuple[float, float, float]]:
    """Build a frame-level thumb-index distance signal with minima exactly at tap_times."""
    import math

    n_frames = int((tap_times[-1] + 0.3) * fps)
    samples = []
    for f in range(n_frames):
        t = f / fps
        prev_t = max((tt for tt in tap_times if tt <= t), default=tap_times[0])
        next_t = min((tt for tt in tap_times if tt >= t), default=tap_times[-1])
        phase = 0.0 if next_t == prev_t else (t - prev_t) / (next_t - prev_t)
        distance = 0.02 + 0.02 * math.sin(math.pi * phase) ** 2
        samples.append((0.0, distance, t))
    return samples


def demo() -> None:
    steady = tap_rhythm(_synthetic_samples([0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4, 2.8]))
    assert steady["jitter_cv"] < 0.1, steady
    assert steady["hesitation_count"] == 0, steady
    assert "steady" in steady["interpretation"], steady

    slowing = tap_rhythm(_synthetic_samples([0.0, 0.35, 0.75, 1.2, 1.7, 2.3, 3.0, 3.8]))
    assert slowing["slope_ms_per_tap"] > 15, slowing
    assert "slowed" in slowing["interpretation"], slowing

    too_few = tap_rhythm([(0.0, 0.0, 0.0)] * 5)
    assert too_few["slope_ms_per_tap"] is None, too_few

    print("motor_cv.py: all checks passed")


if __name__ == "__main__":
    demo()
