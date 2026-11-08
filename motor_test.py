"""Fatigue-slope motor test: finger-tapping rhythm check.

Exploratory stretch goal, not part of ALS RedFlag's clinical scoring (schema.py /
score.py / rules.json are untouched). Measures whether tap rhythm slows over a
trial — upper motor neuron disinhibition can show up as rhythm degradation
before raw strength loss is obvious (see context/Biohack- LBMP.md).

    from motor_test import fatigue_slope
    fatigue_slope([1.0, 1.4, 1.9, 2.5, ...])  # tap() timestamps, oldest first
"""
from __future__ import annotations


def fatigue_slope(tap_times: list[float]) -> dict:
    """tap_times: seconds (e.g. time.time()), oldest first, >=3 taps to be meaningful.

    Returns {"intervals_ms", "slope_ms_per_tap", "interpretation"}. Slope is the
    least-squares trend of inter-tap interval vs. tap index: positive means taps
    got slower over the trial.
    """
    if len(tap_times) < 3:
        return {"intervals_ms": [], "slope_ms_per_tap": None, "interpretation": "Need at least 3 taps."}

    intervals_ms = [(tap_times[i] - tap_times[i - 1]) * 1000 for i in range(1, len(tap_times))]
    n = len(intervals_ms)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(intervals_ms) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, intervals_ms))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den else 0.0

    # ponytail: thresholds below are an unvalidated heuristic, not a clinical cutoff.
    # Upgrade path: calibrate against real tapping-test norms before using for anything
    # beyond an exploratory demo.
    if slope > 15:
        interpretation = "Rhythm slowed noticeably over the trial (possible fatigue)."
    elif slope > 5:
        interpretation = "Rhythm slowed slightly over the trial."
    else:
        interpretation = "Rhythm stayed roughly steady."

    return {"intervals_ms": intervals_ms, "slope_ms_per_tap": round(slope, 1), "interpretation": interpretation}


def demo() -> None:
    steady = fatigue_slope([0.0, 0.3, 0.6, 0.9, 1.2, 1.5])
    assert steady["slope_ms_per_tap"] == 0.0, steady

    slowing = fatigue_slope([0.0, 0.3, 0.65, 1.05, 1.5, 2.0])
    assert slowing["slope_ms_per_tap"] > 15, slowing
    assert "noticeably" in slowing["interpretation"]

    too_few = fatigue_slope([0.0, 0.3])
    assert too_few["slope_ms_per_tap"] is None

    print("motor_test.py: all checks passed")


if __name__ == "__main__":
    demo()
