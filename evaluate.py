"""Print the numbers that go in the README, UI and pitch: Alex's first-HIGH-risk date
and how every mimic note (data/mimics/) scores. Nothing else may quote a number this
script didn't print (CLAUDE.md rule).

    python evaluate.py              # Gemini if GEMINI_API_KEY is set, else keyword fallback
    python evaluate.py --offline    # keyword fallback always; deterministic, used for grading
    python evaluate.py --diagnosis=YYYY-MM-DD

Exit 0 normally; exit 1 if any mimic note scores above low.
"""
from __future__ import annotations

import sys
from pathlib import Path

from extract import extract_findings
from score import score
from timeline import first_flag, months_between, run_timeline

ROOT = Path(__file__).parent
ALEX_DIR = ROOT / "data" / "alex"
MIMICS_DIR = ROOT / "data" / "mimics"
DIAGNOSIS_DATE = "2026-07-14"  # Neurology Outpatient Clinic diagnosis letter, case PDF p.13


def evaluate_mimics(offline: bool | None) -> list[dict]:
    if not MIMICS_DIR.is_dir():
        return []
    results = []
    for path in sorted(MIMICS_DIR.glob("*.txt")):
        findings = extract_findings(path.read_text(encoding="utf-8"), offline=offline)
        results.append({"file": path.name, "risk": score(findings)["risk"]})
    return results


def main() -> int:
    offline = True if "--offline" in sys.argv else None
    diagnosis = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--diagnosis=")), DIAGNOSIS_DATE)

    print(f"Mode: {'offline keyword extractor' if offline else 'Gemini if GEMINI_API_KEY is set, else offline'}")

    try:
        flag = first_flag(run_timeline(ALEX_DIR, offline=offline))
        mimics = evaluate_mimics(offline)
    except Exception as exc:  # Gemini is a network/auth boundary; don't crash the demo on it
        print(f"\nGemini call failed ({exc}). Re-run with --offline.")
        return 1

    print("\nAlex Chen timeline:")
    if flag and flag["date"]:
        months = months_between(flag["date"], diagnosis)
        print(f"  First HIGH risk: {flag['date']} ({flag['file']}), {months} months before diagnosis ({diagnosis})")
    else:
        print("  Never reached HIGH risk.")

    print("\nMimic cases (must all score low):")
    if not mimics:
        print("  none in data/mimics/ yet (TASKS.md row 8)")
        return 0
    for m in mimics:
        print(f"  [{'ok' if m['risk'] == 'low' else 'FAIL'}] {m['file']}: {m['risk']}")
    return 1 if any(m["risk"] != "low" for m in mimics) else 0


if __name__ == "__main__":
    raise SystemExit(main())
