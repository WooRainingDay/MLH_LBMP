"""Score findings against the ALS red-flag rules in rules.json.

    from score import combine, score
    merged = combine([f1, f2, f3])   # findings dicts, any order (sorted by date)
    result = score(merged)           # or score(f1) for one note

result = {
    "risk": "high" | "medium" | "low",
    "points": 14,
    "reasons": ["+3 Weakness has spread to a second region (right hand, left foot)", ...],
    "gold_coast": True,
    "advice": "Urgent referral to neurology ...",
    "evidence": [{"field": "wasting", "quote": "...", "date": "2024-10-14"}, ...],
}
Supports clinical decisions; it does not diagnose.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from schema import FLAGS, empty_findings

RULES_PATH = Path(__file__).parent / "rules.json"

# For these, the most recent note that mentions it wins. Example: early
# "tingling" put down to carpal tunnel, later "sensation intact" on exam.
# For every other finding, true in any note wins: signs add up over time.
LATEST_WINS = {"sensory_symptoms", "painless"}

UMN = ["brisk_reflexes", "upgoing_plantar_or_hoffmann"]   # upper motor neuron signs
LMN = ["wasting", "fasciculations"]                       # lower motor neuron signs


def load_rules(path: Path | str = RULES_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def combine(findings_list: list[dict]) -> dict:
    """Merge one patient's findings (one dict per note) into a single findings dict."""
    notes = sorted(findings_list, key=lambda f: (f.get("date") is None, f.get("date") or ""))
    out = empty_findings()
    out["sources"] = []
    for f in notes:
        for field in FLAGS:
            v = f.get(field)
            if v is None:
                continue
            if field in LATEST_WINS or out[field] is None or v is True:
                out[field] = v
        for r in f.get("weakness_regions") or []:
            if r.lower() not in [x.lower() for x in out["weakness_regions"]]:
                out["weakness_regions"].append(r)
        for e in f.get("evidence") or []:
            out["evidence"].append({**e, "date": e.get("date") or f.get("date")})
        out["sources"].append({"date": f.get("date"), "source": f.get("source")})
        out["date"] = f.get("date") or out["date"]
    out["source"] = f"{len(notes)} notes combined"
    return out


# Map free-text weakness places to body regions. Spread = 2+ of these.
_REGION_WORDS = [
    ("bulbar", r"speech|speak|swallow|tongue|jaw|face|facial|bulbar|voice"),
    ("trunk", r"trunk|neck|breath|chest|abdom|back"),
    ("arm", r"hand|arm|finger|thumb|wrist|grip|shoulder|elbow|forearm|upper limb"),
    ("leg", r"leg|foot|feet|ankle|toe|knee|thigh|hip|calf|gait|lower limb"),
]


def body_regions(places: list[str]) -> list[str]:
    """['right hand', 'left foot'] -> ['right arm', 'left leg']. Left and right count separately."""
    regions: list[str] = []
    for p in places:
        low = p.lower()
        for name, pat in _REGION_WORDS:
            if re.search(pat, low):
                side = "left " if "left" in low else "right " if "right" in low else ""
                region = (side + name) if name in ("arm", "leg") else name
                if region not in regions:
                    regions.append(region)
                break
    # "hand" with no side is the same limb as "right hand" if that is already known
    return [r for r in regions if r not in ("arm", "leg") or not any(x.endswith(" " + r) for x in regions)]


def score(findings: dict, rules: Optional[dict] = None) -> dict:
    rules = rules or load_rules()
    reasons: list[tuple[int, str]] = []
    points = 0
    has_weakness = bool(findings.get("weakness_regions"))

    for r in rules["rules"]:
        if findings.get(r["field"]) is r["when"]:
            if r["field"] == "painless" and not has_weakness:
                continue
            points += r["points"]
            reasons.append((r["points"], r["why"]))

    # "If it's progressive and doesn't fit - refer": motor loss that the nerve tests don't explain
    if has_weakness and findings.get("wasting") and findings.get("normal_sensory_nerve_tests") \
            and findings.get("sensory_symptoms") is not True:
        points += rules.get("unexplained_points", 0)
        reasons.append((rules.get("unexplained_points", 0), rules.get("unexplained_why", "")))

    regions = body_regions(findings.get("weakness_regions") or [])
    if findings.get("speech_or_swallow_change") and "bulbar" not in regions:
        regions.append("bulbar")
    spread = len(regions) >= 2
    if spread:
        points += rules["spread_points"]
        reasons.append((rules["spread_points"], f"{rules['spread_why']} ({', '.join(regions)})"))

    umn_lmn = any(findings.get(f) for f in UMN) and any(findings.get(f) for f in LMN)
    if umn_lmn:
        points += rules["umn_plus_lmn_points"]
        reasons.append((rules["umn_plus_lmn_points"], rules["umn_plus_lmn_why"]))

    getting_worse = spread or bool(findings.get("failed_local_treatment"))
    gold_coast = umn_lmn and getting_worse

    th = rules["risk_thresholds"]
    risk = "high" if gold_coast or points >= th["high"] else "medium" if points >= th["medium"] else "low"
    reasons.sort(key=lambda x: -x[0])
    if gold_coast:
        reasons.insert(0, (0, "Matches the Gold Coast pattern: upper + lower motor neuron signs and getting worse"))
    return {
        "risk": risk,
        "points": points,
        "reasons": [why if p == 0 else f"{p:+d} {why}" for p, why in reasons],
        "gold_coast": gold_coast,
        "regions": regions,
        "advice": rules["advice"][risk],
        "evidence": findings.get("evidence", []),
    }


if __name__ == "__main__":
    import sys
    from extract import extract_findings

    paths = [Path(p) for p in sys.argv[1:] if not p.startswith("--")]
    if not paths:
        sys.exit("usage: python score.py NOTE.txt [NOTE2.txt ...] [--offline]")
    offline = True if "--offline" in sys.argv else None
    fs = [extract_findings(p.read_text(encoding="utf-8"), offline=offline) for p in paths]
    result = score(combine(fs) if len(fs) > 1 else fs[0])
    result.pop("evidence")
    print(json.dumps(result, indent=2))
