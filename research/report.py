"""Print every number the README/Devpost/UI show for the data-model work, so each
one is reproducible with a single command (same idea as evaluate.py for the
clinical pipeline). Re-runs the underlying scripts rather than caching numbers,
so a number here can never drift from what actually runs.

Extend the sections below as more plan steps land (TORGO external check,
NeuroFace calibration, Answer ALS / DNE-113 finger-tap calibration).

CLI: python research/report.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        return f"FAILED ({result.returncode}): {result.stderr.strip()[:300]}"
    return result.stdout.strip()


def main() -> None:
    print("=" * 70)
    print("VOC-ALS voice baseline (research/train_voice.py)")
    print("=" * 70)
    print(_run([sys.executable, "research/train_voice.py"]) or "(not run: features CSV missing)")

    print()
    print("=" * 70)
    print("Gait rhythm-method validation (research/calibrate_motor.py)")
    print("=" * 70)
    print(_run([sys.executable, "research/calibrate_motor.py"]) or "(not run: gait data missing)")

    print()
    print("=" * 70)
    print("TORGO external check (research/score_torgo.py)")
    print("=" * 70)
    print(_run([sys.executable, "research/score_torgo.py"]) or "(not run: TORGO data missing)")

    print()
    print("=" * 70)
    print("NOT YET RUN")
    print("=" * 70)
    print("- NeuroFace lip-velocity calibration (plan Step 5): access pending")
    print("- Answer ALS / DNE-113 finger-tap calibration (plan Step 5): access pending")


if __name__ == "__main__":
    main()
