"""Validate motor_cv.py's jitter/slope method against real ALS motor data.

Real finger-tapping clinical data (Answer ALS, DNE-113) isn't available yet
(access pending). As a stand-in, this runs the exact same interval
jitter_cv/slope method (motor_cv._score) on PhysioNet's Gait in
Neurodegenerative Disease stride-interval data: a different body part, but
the same question (does interval variability rise in real ALS patients?).
This checks the *method*, not a finger-tap-specific cutoff.

CLI: python research/calibrate_motor.py
     -> prints per-group jitter_cv / slope means (ALS, control, Parkinson's, Huntington's)
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from motor_cv import _score  # noqa: E402 - reuse the exact method used on finger taps

GAIT_DIR = Path(__file__).parent.parent / "data" / "external" / "gait"
GROUP_PREFIXES = {"als": "ALS", "control": "control", "park": "Parkinson's", "hunt": "Huntington's"}


def group_of(stem: str) -> str | None:
    for prefix, label in GROUP_PREFIXES.items():
        if stem.startswith(prefix) and stem[len(prefix):].isdigit():
            return label
    return None


def stride_intervals_ms(ts_path: Path) -> list[float]:
    """Left stride interval, column 2 of the .ts file (seconds) -> ms."""
    out = []
    for line in ts_path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        out.append(float(parts[1]) * 1000)
    return out


def main() -> None:
    ts_dir = next(GAIT_DIR.glob("gait-in-neurodegenerative-disease-database-*"), None)
    if ts_dir is None:
        sys.exit(f"Gait dataset not found under {GAIT_DIR} - run research/fetch_data.py --gait first")

    by_group: dict[str, list[dict]] = {}
    for ts_path in sorted(ts_dir.glob("*.ts")):
        label = group_of(ts_path.stem)
        if label is None:
            continue
        intervals = stride_intervals_ms(ts_path)
        if len(intervals) < 10:
            continue
        by_group.setdefault(label, []).append(_score(intervals))

    print(f"{'group':12s} {'n':>3s}  {'jitter_cv mean':>15s}  {'slope mean':>12s}")
    for label, results in by_group.items():
        jitters = [r["jitter_cv"] for r in results]
        slopes = [r["slope_ms_per_tap"] for r in results]
        print(f"{label:12s} {len(results):3d}  {statistics.mean(jitters):15.3f}  {statistics.mean(slopes):12.2f}")

    als, ctrl = by_group.get("ALS"), by_group.get("control")
    if als and ctrl:
        als_jitter = statistics.mean(r["jitter_cv"] for r in als)
        ctrl_jitter = statistics.mean(r["jitter_cv"] for r in ctrl)
        direction = "ALS more variable (expected)" if als_jitter > ctrl_jitter else "WARNING: not in the expected direction"
        print(f"\nALS jitter_cv {als_jitter:.3f} vs control {ctrl_jitter:.3f}: {direction}")


if __name__ == "__main__":
    main()
