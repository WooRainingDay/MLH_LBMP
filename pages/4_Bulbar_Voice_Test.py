"""Bulbar/voice test: live camera + mic only.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §2), not part of
ALS RedFlag's red-flag scoring, not a validated clinical test. Needs a secure
context (HTTPS or localhost) for browser camera/mic access. Captures video +
audio from one WebRTC stream (no ffmpeg demuxing needed).
"""
from __future__ import annotations

import queue
import time

import numpy as np
import streamlit as st
from streamlit_webrtc import AudioProcessorBase, VideoProcessorBase, webrtc_streamer

from motor_face_audio import (
    _ensure_model,
    extract_lip_sample,
    lip_velocity,
    new_face_landmarker,
    voice_jitter_and_formants,
    voice_tier_b,
)

st.set_page_config(page_title="Bulbar/voice test", page_icon="🗣️")
st.title("Bulbar & voice test (exploratory)")
st.caption(
    "Stretch goal, not part of ALS RedFlag's scoring. Lip-corner tracking (facial "
    "keypoints) + pitch jitter and formant stability from a sustained vowel. "
    "Not a validated clinical test."
)


def render_lip_result(result: dict) -> None:
    if result["mean_velocity"] is None:
        st.warning(result["interpretation"])
        return
    st.line_chart(result["velocities"])
    col1, col2 = st.columns(2)
    col1.metric("Mean lip velocity", result["mean_velocity"])
    col2.metric("Velocity variability (CV)", result["velocity_cv"])
    st.write(result["interpretation"])


def render_voice_result(y: np.ndarray, sr: int) -> None:
    result = voice_jitter_and_formants(y, sr)
    if result["jitter_pct"] is None:
        st.warning(result["interpretation"])
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("Pitch jitter", f"{result['jitter_pct']}%")
    col2.metric("F0 SD (Hz)", result["f0_sd"])
    col3.metric("Formant stability (CV)", result["formant_stability_cv"])
    st.write(result["interpretation"])

    tier_b = voice_tier_b(y, sr)
    if tier_b is not None:
        st.metric("Tier B - trained-model ALS risk", tier_b["risk_probability"])
        st.caption(f"Tier B ({tier_b['source']}). Decision support only, not a diagnosis.")
        st.caption(tier_b["caveat"])
    else:
        st.caption("Tier C (heuristic only) - no trained voice model found locally.")


st.caption(
    "Needs camera + mic permission and a secure context (HTTPS or localhost) — "
    "browsers block this on plain HTTP for non-localhost URLs."
)
try:
    _ensure_model()
except RuntimeError as e:
    st.error(str(e))
    st.stop()


class LipProcessor(VideoProcessorBase):
    def __init__(self) -> None:
        import mediapipe as mp

        self.landmarker = new_face_landmarker(mp.tasks.vision.RunningMode.VIDEO)
        self.start_time = time.time()
        self.last_timestamp_ms = -1
        self.samples: queue.Queue = queue.Queue()

    def __del__(self) -> None:
        self.landmarker.close()

    def recv(self, frame):
        import cv2
        import mediapipe as mp

        img = frame.to_ndarray(format="bgr24")
        # MediaPipe VIDEO mode requires strictly increasing timestamps; wall-clock
        # alone isn't guaranteed to advance between two frames under WebRTC jitter.
        timestamp_ms = max(int((time.time() - self.start_time) * 1000), self.last_timestamp_ms + 1)
        self.last_timestamp_ms = timestamp_ms
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        sample = extract_lip_sample(result, timestamp_ms / 1000)
        if sample:
            self.samples.put(sample)
        return frame


class VoiceProcessor(AudioProcessorBase):
    def __init__(self) -> None:
        self.chunks: list[np.ndarray] = []
        self.sample_rate: int | None = None

    def recv(self, frame):
        self.sample_rate = frame.sample_rate
        arr = frame.to_ndarray()
        if arr.ndim == 2:
            arr = arr.mean(axis=0)
        if np.issubdtype(arr.dtype, np.integer):
            arr = arr.astype(np.float32) / np.iinfo(arr.dtype).max
        else:
            arr = arr.astype(np.float32)
        self.chunks.append(arr)
        return frame


ctx = webrtc_streamer(
    key="bulbar-voice-test",
    video_processor_factory=LipProcessor,
    audio_processor_factory=VoiceProcessor,
    media_stream_constraints={"video": True, "audio": True},
)
# streamlit-webrtc tears its worker down on Stop, so ctx.video_processor/audio_processor
# go back to None right when we need to read them. Keep the last live pair around instead.
if ctx.video_processor and ctx.audio_processor:
    st.session_state["bulbar_processors"] = (ctx.video_processor, ctx.audio_processor)
processors = st.session_state.get("bulbar_processors")

st.caption("Speak / sustain a vowel for ~5-10s, then click Stop above, then Analyze below.")
if processors and st.button("Analyze recording"):
    video_processor, audio_processor = processors
    face_samples = []
    while True:
        try:
            face_samples.append(video_processor.samples.get_nowait())
        except queue.Empty:
            break
    render_lip_result(lip_velocity(face_samples))

    if audio_processor.chunks:
        y = np.concatenate(audio_processor.chunks)
        render_voice_result(y, audio_processor.sample_rate)
    else:
        st.warning("No audio captured yet.")
