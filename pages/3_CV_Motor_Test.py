"""CV finger-tap motor test: upload a short clip, track hand landmarks.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §1), not part of
ALS RedFlag's red-flag scoring, not a validated clinical test. Upload-then-
analyze (no live webcam capture) for demo reliability.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from motor_cv import load_hand_landmarks, tap_rhythm

st.set_page_config(page_title="CV motor test", page_icon="🎥")
st.title("Finger-tap CV test (exploratory)")
st.caption(
    "Stretch goal, not part of ALS RedFlag's scoring. Upload a ~10-30s clip of rapid "
    "thumb-to-index tapping; MediaPipe tracks the hand and we look at tap-to-tap jitter, "
    "micro-hesitations, and whether rhythm slows over the trial. Not a validated clinical test."
)

uploaded = st.file_uploader("Upload a finger-tapping video", type=["mp4", "mov", "webm"])

if uploaded is not None:
    with tempfile.NamedTemporaryFile(suffix=Path(uploaded.name).suffix, delete=False) as tmp:
        tmp.write(uploaded.read())
        video_path = tmp.name

    with st.spinner("Tracking hand landmarks..."):
        try:
            samples = load_hand_landmarks(video_path)
        except RuntimeError as e:
            st.error(str(e))
            st.stop()
    result = tap_rhythm(samples)

    if not result["intervals_ms"]:
        st.warning(result["interpretation"])
    else:
        st.line_chart(result["intervals_ms"])
        col1, col2, col3 = st.columns(3)
        col1.metric("Jitter (CV)", result["jitter_cv"])
        col2.metric("Micro-hesitations", result["hesitation_count"])
        col3.metric("Fatigue slope", f"{result['slope_ms_per_tap']} ms/tap")
        st.write(result["interpretation"])
