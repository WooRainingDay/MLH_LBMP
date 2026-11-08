"""CV finger-tap motor test: upload a clip or use the live camera.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §1), not part of
ALS RedFlag's red-flag scoring, not a validated clinical test. Live mode
needs a secure context (HTTPS or localhost) for browser camera access.
"""
from __future__ import annotations

import queue
import tempfile
import time
from pathlib import Path

import streamlit as st
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

from motor_cv import _ensure_model, extract_hand_sample, load_hand_landmarks, new_landmarker, tap_rhythm

st.set_page_config(page_title="CV motor test", page_icon="🎥")
st.title("Finger-tap CV test (exploratory)")
st.caption(
    "Stretch goal, not part of ALS RedFlag's scoring. Rapid thumb-to-index tapping; "
    "MediaPipe tracks the hand and we look at tap-to-tap jitter, micro-hesitations, and "
    "whether rhythm slows over the trial. Not a validated clinical test."
)


def render_result(result: dict) -> None:
    if not result["intervals_ms"]:
        st.warning(result["interpretation"])
        return
    st.line_chart(result["intervals_ms"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Jitter (CV)", result["jitter_cv"])
    col2.metric("Micro-hesitations", result["hesitation_count"])
    col3.metric("Fatigue slope", f"{result['slope_ms_per_tap']} ms/tap")
    st.write(result["interpretation"])


mode = st.radio("Capture method", ["Upload a clip", "Live camera"], horizontal=True)

if mode == "Upload a clip":
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
        render_result(tap_rhythm(samples))

else:
    st.caption(
        "Needs camera permission and a secure context (HTTPS or localhost) — browsers "
        "block camera access on plain HTTP for non-localhost URLs."
    )
    try:
        _ensure_model()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    class HandTapProcessor(VideoProcessorBase):
        def __init__(self) -> None:
            import mediapipe as mp

            self.landmarker = new_landmarker(mp.tasks.vision.RunningMode.VIDEO)
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
            sample = extract_hand_sample(result, timestamp_ms / 1000)
            if sample:
                self.samples.put(sample)
            return frame

    ctx = webrtc_streamer(
        key="cv-motor-test",
        video_processor_factory=HandTapProcessor,
        media_stream_constraints={"video": True, "audio": False},
    )

    st.caption("Tap for ~15-30s, then click Stop above, then Analyze below.")
    if ctx.video_processor and st.button("Analyze recording"):
        samples = []
        while True:
            try:
                samples.append(ctx.video_processor.samples.get_nowait())
            except queue.Empty:
                break
        render_result(tap_rhythm(samples))
