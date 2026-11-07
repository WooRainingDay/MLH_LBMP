"""Optional stretch-goal page: a finger-tapping fatigue-slope test.

Exploratory only — not part of ALS RedFlag's red-flag scoring, not validated.
See context/Biohack- LBMP.md for the original idea; this is a deliberately
simplified, dependency-free version (tap rhythm, not camera/CV).
"""
from __future__ import annotations

import time

import streamlit as st

from motor_test import fatigue_slope

TARGET_TAPS = 15

st.set_page_config(page_title="Motor test", page_icon="🖐️")
st.title("Finger-tapping fatigue test (exploratory)")
st.caption(
    "Stretch goal, not part of ALS RedFlag's scoring. Tap the button at a steady pace; "
    "we look at whether your rhythm slows over the trial. Not a validated clinical test."
)

if "tap_times" not in st.session_state:
    st.session_state.tap_times = []

n = len(st.session_state.tap_times)

col1, col2 = st.columns(2)
with col1:
    if st.button("Tap", use_container_width=True, disabled=n >= TARGET_TAPS):
        st.session_state.tap_times.append(time.time())
        st.rerun()
with col2:
    if st.button("Reset", use_container_width=True):
        st.session_state.tap_times = []
        st.rerun()

st.progress(min(n / TARGET_TAPS, 1.0), text=f"{n} / {TARGET_TAPS} taps")

if n >= 3:
    result = fatigue_slope(st.session_state.tap_times)
    st.line_chart(result["intervals_ms"])
    st.metric("Fatigue slope", f"{result['slope_ms_per_tap']} ms/tap")
    st.write(result["interpretation"])

if n >= TARGET_TAPS:
    st.success("Trial complete. Hit Reset to try again.")
