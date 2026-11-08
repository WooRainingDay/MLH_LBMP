"""Streamlit UI for ALS RedFlag. Steps through a patient's notes in date order, shows
findings with quoted evidence, and flags the first note that crosses urgent-referral risk.
Supports clinical decisions; it does not diagnose.

    streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from elevenlabs_alert import generate_alert
from score import load_rules
from timeline import first_flag, months_between, run_timeline

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_DIAGNOSIS = "2026-07-14"
RISK_COLOR = {"low": "green", "medium": "orange", "high": "red"}

st.set_page_config(page_title="ALS RedFlag", page_icon="🧠")


@st.cache_data(show_spinner="Reading notes...")
def _run_timeline(notes_dir: str, offline: bool, dir_mtime: float) -> list[dict]:
    return run_timeline(notes_dir, offline=offline)


def _dir_mtime(path: Path) -> float:
    return max((p.stat().st_mtime for p in path.glob("*.txt")), default=0.0)


patients = sorted(p.name for p in DATA_DIR.iterdir() if p.is_dir() and any(p.glob("*.txt")))

st.sidebar.title("ALS RedFlag")
patient = st.sidebar.selectbox("Patient notes", patients, index=patients.index("alex") if "alex" in patients else 0)
offline = st.sidebar.toggle("Offline mode (no Gemini key spent)", value=True)
diagnosis = st.sidebar.text_input("Diagnosis date (for months-before calc)", DEFAULT_DIAGNOSIS)
st.sidebar.caption("Supports clinical decisions. It does not diagnose.")

notes_dir = DATA_DIR / patient
steps = _run_timeline(str(notes_dir), offline, _dir_mtime(notes_dir))
flag = first_flag(steps)
rules = load_rules()

st.title(f"Timeline: {patient}")

if flag and flag["date"]:
    months = months_between(flag["date"], diagnosis) if diagnosis else None
    st.error(
        f"**First HIGH-risk flag: {flag['date']}** ({flag['file']})"
        + (f" — {months} months before diagnosis ({diagnosis})" if months is not None else ""),
        icon="🚩",
    )
    with st.expander("Why this note flags HIGH", expanded=True):
        st.write(f"**{flag['points']} points.** Gold Coast pattern: {'yes' if flag['gold_coast'] else 'no'}")
        for reason in flag["reasons"]:
            st.markdown(f"- {reason}")
        st.info(rules["advice"]["high"])

    alert_audio = generate_alert(flag["date"], months, flag["gold_coast"])
    if alert_audio is not None:
        st.audio(alert_audio, format="audio/mp3", autoplay=True)
        st.caption("The call that never came - played aloud, same numbers as the banner above.")
else:
    st.success("Never reached HIGH risk in this note set.", icon="✅")

st.divider()
st.subheader("Notes, oldest first")

for step in steps:
    label = f"{step['date'] or '?'} — {step['file']}"
    with st.expander(label, expanded=(step is flag)):
        color = RISK_COLOR.get(step["risk"], "gray")
        st.markdown(f":{color}[**{step['risk'].upper()}**] — {step['points']} points")
        if step["new_findings"]:
            st.write("New this note: " + ", ".join(step["new_findings"]))
            for q in step["findings"].get("evidence", []):
                st.markdown(f"> *{q['quote']}* — `{q['field']}`")
        else:
            st.write("No new findings.")
