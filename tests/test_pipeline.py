"""Offline tests: no API key needed.  Run: python -m pytest -q"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from extract import extract_offline  # noqa: E402
from score import body_regions, combine, score  # noqa: E402
from timeline import first_flag, run_timeline  # noqa: E402


def test_true_false_null():
    f = extract_offline("Weak right hand. No fasciculations. Sensation intact.")
    assert f["fasciculations"] is False
    assert f["sensory_symptoms"] is False
    assert f["wasting"] is None
    assert f["weakness_regions"] == ["right hand"]


def test_carpal_tunnel_mimic_is_low():
    note = ("Numbness and tingling in the right thumb and index finger, worse at night, painful wrist. "
            "Mild weakness of right thumb. Positive Phalen's test. Reflexes normal.")
    assert score(extract_offline(note))["risk"] == "low"


def test_classic_als_note_is_high():
    note = ("Painless weakness of the right hand, now also tripping over the left foot. "
            "Wasting of right thenar muscles. Fasciculations in right arm and left calf. "
            "Brisk reflexes and positive Hoffmann sign. Sensation normal.")
    r = score(extract_offline(note))
    assert r["risk"] == "high" and r["gold_coast"]


def test_body_regions():
    assert body_regions(["right hand", "left foot", "speech"]) == ["right arm", "left leg", "bulbar"]


def test_combine_adds_up_and_latest_sensory_wins():
    a = {"date": "2024-06-01", "weakness_regions": ["right hand"], "sensory_symptoms": True, "wasting": None}
    b = {"date": "2024-10-14", "weakness_regions": ["right foot"], "sensory_symptoms": False, "wasting": True}
    c = combine([b, a])  # out of order on purpose
    assert c["sensory_symptoms"] is False
    assert c["wasting"] is True
    assert c["weakness_regions"] == ["right hand", "right foot"]


def test_sample_timeline_flags_before_neurology():
    steps = run_timeline(ROOT / "data" / "sample", offline=True)
    assert [s["date"] for s in steps] == sorted(s["date"] for s in steps)
    assert set(steps[0]) >= {"date", "risk", "points"}
    flag = first_flag(steps)
    assert flag is not None and flag["date"] < "2025-03-18"


def test_hand_surgery_wording():
    """Alex's Dec 2024 and Apr 2025 notes, as the hand surgeon wrote them."""
    dec = extract_offline("Six months of right hand weakness affecting fine tasks, no sensory symptoms. "
                          "Nerve conduction across the right wrist: median sensory and motor latencies within "
                          "normal limits; no slowing across the carpal tunnel. Visible wasting of the right thenar "
                          "muscles. Grip 4 out of 5 on the right.")
    assert dec["normal_sensory_nerve_tests"] is True
    assert dec["sensory_symptoms"] is False
    apr = extract_offline("Surgery 20 January 2025, uncomplicated. He reports no improvement. "
                          "He has also begun to mention his right foot catching on stairs.")
    assert apr["failed_local_treatment"] is True
    assert "right foot" in apr["weakness_regions"]


def test_real_carpal_tunnel_nerve_test_is_not_normal():
    f = extract_offline("Numbness in the right thumb at night. Median sensory latency prolonged at the wrist, "
                        "with slowing across the carpal tunnel.")
    assert f["normal_sensory_nerve_tests"] is False
    assert score(f)["risk"] == "low"
