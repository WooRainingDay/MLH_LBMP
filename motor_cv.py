"""CV finger-tap motor test: real MediaPipe hand-landmark tracking.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §1 — Upper Motor
Neuron Sign: Spasticity & Micro-Tremors), not part of ALS RedFlag's clinical
scoring (schema.py / score.py / rules.json are untouched). Measures frequency
jitter, micro-hesitations, and rhythm degradation in a thumb-to-index tapping
trial — upper motor neuron disinhibition can show up as rhythm degradation
before raw strength loss is obvious.

    from motor_cv import tap_rhythm
    tap_rhythm(samples)  # samples from extract_hand_sample(), live-camera only
"""
from __future__ import annotations

import math
import statistics
import urllib.request
from pathlib import Path

from scipy.signal import find_peaks

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)
MODEL_PATH = Path(".cache/models/hand_landmarker.task")

WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_MCP = 9
# A real tap opens thumb-index by well over this (in hand-size units); landmark jitter
# from a hand held still stays under it. ponytail: hand-tuned, not calibrated on data.
MIN_TAP_PROMINENCE = 0.15


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


def extract_hand_sample(result, timestamp_s: float) -> tuple[float, float] | None:
    """Pulls (pinch_distance, timestamp_s) out of one HandLandmarker result, or None if
    no hand was detected. pinch_distance is the 2D thumb-tip to index-tip distance divided
    by hand size (wrist to middle knuckle), so it doesn't change with distance from the
    camera."""
    if not result.hand_landmarks:
        return None
    hand = result.hand_landmarks[0]
    size = math.dist((hand[WRIST].x, hand[WRIST].y), (hand[MIDDLE_MCP].x, hand[MIDDLE_MCP].y))
    if size == 0:
        return None
    pinch = math.dist((hand[THUMB_TIP].x, hand[THUMB_TIP].y), (hand[INDEX_TIP].x, hand[INDEX_TIP].y))
    return (pinch / size, timestamp_s)


def new_landmarker(running_mode):
    """A ready-to-use HandLandmarker for the given running_mode (live-camera uses VIDEO)."""
    import mediapipe as mp

    return mp.tasks.vision.HandLandmarker.create_from_options(
        mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(_ensure_model())),
            running_mode=running_mode,
            num_hands=1,
        )
    )


def detect_taps(samples: list[tuple[float, float]]) -> list[float]:
    """samples: (pinch_distance, timestamp_s) per frame, oldest first, hand-size-normalized
    (see extract_hand_sample). A tap is a local minimum in pinch distance deep enough to
    clear MIN_TAP_PROMINENCE — real pinch-closes swing ~0.8 of this normalized unit, while
    landmark-tracking jitter from a hand held still stays well under the 0.15 floor.
    Returns tap timestamps in seconds. Needs >=10 frames to be meaningful.
    """
    if len(samples) < 10:
        return []
    times = [s[1] for s in samples]
    distances = [s[0] for s in samples]
    peak_idx, _ = find_peaks([-d for d in distances], distance=3, prominence=MIN_TAP_PROMINENCE)
    return [times[i] for i in peak_idx]


def tap_rhythm(samples: list[tuple[float, float]]) -> dict:
    """samples: (pinch_distance, timestamp_s) per frame, oldest first (see
    extract_hand_sample). Returns {"intervals_ms", "jitter_cv", "hesitation_count",
    "slope_ms_per_tap", "interpretation"}.
    """
    if len(samples) < 10:
        return _empty("Need at least 10 frames with a detected hand.")

    tap_times = detect_taps(samples)
    if len(tap_times) < 3:
        return _empty("Could not detect at least 3 taps in this clip.")

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
    # (no UPDRS-style tapping norms baked in). The jitter_cv *method* is validated on
    # real ALS gait data (ALS 0.429 vs control 0.044, research/calibrate_motor.py) -
    # but that's stride interval, not finger tap. Upgrade path: calibrate the 0.3/15
    # cutoffs against real finger-tapping-test data (Answer ALS / DNE-113, access
    # pending per docs/plans/als-data-models.md) before using beyond an exploratory demo.
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


def _synthetic_samples(tap_times: list[float], fps: float = 100.0) -> list[tuple[float, float]]:
    """Build a frame-level pinch-distance signal (hand-size-normalized) with minima
    (taps) exactly at tap_times, swinging between a closed pinch (~0.05) and an open
    hand (~0.85) — a realistic amplitude, well above MIN_TAP_PROMINENCE."""
    n_frames = int((tap_times[-1] + 0.3) * fps)
    samples = []
    for f in range(n_frames):
        t = f / fps
        prev_t = max((tt for tt in tap_times if tt <= t), default=tap_times[0])
        next_t = min((tt for tt in tap_times if tt >= t), default=tap_times[-1])
        phase = 0.0 if next_t == prev_t else (t - prev_t) / (next_t - prev_t)
        pinch = 0.05 + 0.8 * math.sin(math.pi * phase) ** 2
        samples.append((pinch, t))
    return samples


def demo() -> None:
    steady = tap_rhythm(_synthetic_samples([0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4, 2.8]))
    assert steady["jitter_cv"] < 0.1, steady
    assert steady["hesitation_count"] == 0, steady
    assert "steady" in steady["interpretation"], steady

    slowing = tap_rhythm(_synthetic_samples([0.0, 0.35, 0.75, 1.2, 1.7, 2.3, 3.0, 3.8]))
    assert slowing["slope_ms_per_tap"] > 15, slowing
    assert "slowed" in slowing["interpretation"], slowing

    too_few = tap_rhythm([(0.05, 0.0)] * 5)
    assert too_few["slope_ms_per_tap"] is None, too_few

    # Regression test: a hand held still (small, slow jitter well under MIN_TAP_PROMINENCE)
    # must not register any taps.
    jitter_only = [(0.5 + 0.05 * math.sin(2 * math.pi * f / 20), f / 100) for f in range(200)]
    still = tap_rhythm(jitter_only)
    assert still["slope_ms_per_tap"] is None, still
    assert "Could not detect" in still["interpretation"], still

    print("motor_cv.py: all checks passed")


if __name__ == "__main__":
    demo()
