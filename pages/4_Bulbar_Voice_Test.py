"""Bulbar/voice test: upload a speech clip and a sustained-vowel clip.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §2), not part of
ALS RedFlag's red-flag scoring, not a validated clinical test. Two separate
uploads (video for lip tracking, audio for voice) avoid an ffmpeg dependency
for demuxing audio out of a video container.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import librosa
import streamlit as st

from motor_face_audio import load_face_landmarks, lip_velocity, voice_jitter_and_formants

st.set_page_config(page_title="Bulbar/voice test", page_icon="🗣️")
st.title("Bulbar & voice test (exploratory)")
st.caption(
    "Stretch goal, not part of ALS RedFlag's scoring. Upload a short video of yourself "
    "speaking (lip-corner tracking) and a short audio clip of a sustained vowel, e.g. "
    "'ahhh' for 3-5s (pitch jitter + formant stability). Not a validated clinical test."
)

video = st.file_uploader("Upload a speech video (for lip tracking)", type=["mp4", "mov", "webm"])
if video is not None:
    with tempfile.NamedTemporaryFile(suffix=Path(video.name).suffix, delete=False) as tmp:
        tmp.write(video.read())
        video_path = tmp.name

    with st.spinner("Tracking lip landmarks..."):
        face_samples = load_face_landmarks(video_path)
    lip_result = lip_velocity(face_samples)

    if lip_result["mean_velocity"] is None:
        st.warning(lip_result["interpretation"])
    else:
        st.line_chart(lip_result["velocities"])
        col1, col2 = st.columns(2)
        col1.metric("Mean lip velocity", lip_result["mean_velocity"])
        col2.metric("Velocity variability (CV)", lip_result["velocity_cv"])
        st.write(lip_result["interpretation"])

st.divider()

audio = st.file_uploader("Upload a sustained-vowel audio clip", type=["wav", "mp3", "m4a"])
if audio is not None:
    with tempfile.NamedTemporaryFile(suffix=Path(audio.name).suffix, delete=False) as tmp:
        tmp.write(audio.read())
        audio_path = tmp.name

    with st.spinner("Analyzing pitch and formants..."):
        y, sr = librosa.load(audio_path)
        voice_result = voice_jitter_and_formants(y, sr)

    if voice_result["jitter_pct"] is None:
        st.warning(voice_result["interpretation"])
    else:
        col1, col2 = st.columns(2)
        col1.metric("Pitch jitter", f"{voice_result['jitter_pct']}%")
        col2.metric("Formant stability (CV)", voice_result["formant_stability_cv"])
        st.write(voice_result["interpretation"])
