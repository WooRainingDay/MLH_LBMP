"""CV finger-tap motor test: live camera only.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §1), not part of
ALS RedFlag's red-flag scoring, not a validated clinical test. Needs a secure
context (HTTPS or localhost) for browser camera access.
"""
from __future__ import annotations

import io
import math
import struct
import threading
import time
import wave

import av
import streamlit as st
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

from motor_cv import (
    INDEX_TIP,
    THUMB_TIP,
    _ensure_model,
    detect_taps,
    extract_hand_sample,
    new_landmarker,
    tap_rhythm,
)

YELLOW = (0, 255, 255)  # BGR

st.set_page_config(page_title="CV motor test", page_icon="🎥")


@st.cache_data
def _beep_bytes(variant: int = 0) -> bytes:
    """A short synthetic beep (stdlib only, no TTS/network) to confirm a tap was caught.

    `variant` nudges the pitch by a few Hz so repeated calls produce distinct bytes —
    st.audio has no `key` param, and Streamlit dedupes identical-content elements.
    """
    freq, duration_s, sample_rate, volume = 880 + (variant % 7), 0.12, 22050, 0.4
    n = int(sample_rate * duration_s)
    frames = bytearray()
    for i in range(n):
        envelope = 1.0 - (i / n)  # fade out so it doesn't click
        sample = volume * envelope * math.sin(2 * math.pi * freq * i / sample_rate)
        frames += struct.pack("<h", int(sample * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    return buf.getvalue()
st.title("Finger-tap CV test (exploratory)")
st.caption(
    "Stretch goal, not part of ALS RedFlag's scoring. Rapid thumb-to-index tapping; "
    "MediaPipe tracks the hand and we look at tap-to-tap jitter, micro-hesitations, and "
    "whether rhythm slows over the trial. Not a validated clinical test."
)


def _draw_hand_overlay(img, result) -> None:
    """Yellow box around the hand plus the thumb and index tips, drawn on the live frame,
    so the person can see what MediaPipe is tracking before they start tapping."""
    import cv2

    h, w = img.shape[:2]
    if not result.hand_landmarks:
        cv2.putText(img, "Show one hand to the camera", (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, YELLOW, 2)
        return
    pts = [(int(p.x * w), int(p.y * h)) for p in result.hand_landmarks[0]]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    left, top = min(xs) - 20, min(ys) - 20
    cv2.rectangle(img, (left, top), (max(xs) + 20, max(ys) + 20), YELLOW, 2)
    cv2.putText(img, "Hand", (left, top - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, YELLOW, 2)
    thumb, index = pts[THUMB_TIP], pts[INDEX_TIP]
    cv2.line(img, thumb, index, YELLOW, 2)
    for (x, y), label in ((thumb, "Thumb"), (index, "Index")):
        cv2.rectangle(img, (x - 14, y - 14), (x + 14, y + 14), YELLOW, 2)
        cv2.putText(img, label, (x + 18, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, YELLOW, 2)


def render_result(result: dict) -> None:
    if not result["intervals_ms"]:
        st.warning(result["interpretation"])
        return

    n_taps = len(result["intervals_ms"]) + 1
    duration_s = sum(result["intervals_ms"]) / 1000
    # Same flags _score() uses for its technical interpretation string — restated in
    # plain language here so a non-technical reader (or a judge) gets the headline
    # without needing to know what "jitter (CV)" means.
    notes = []
    if result["jitter_cv"] > 0.3:
        notes.append("the spacing between taps varied a lot")
    if result["hesitation_count"] > 0:
        plural = "s" if result["hesitation_count"] > 1 else ""
        notes.append(f"{result['hesitation_count']} tap{plural} had a noticeable pause beforehand")
    if result["slope_ms_per_tap"] > 15:
        notes.append("tapping got slower as the trial went on")

    summary = f"{n_taps} taps over {duration_s:.0f}s."
    if notes:
        st.info(f"**Some irregularity in the tapping rhythm.** {summary} " + "; ".join(notes).capitalize() + ".", icon=":material/info:")
    else:
        st.success(f"**Steady tapping rhythm.** {summary} Evenly spaced, no pauses, no slowdown.", icon=":material/check_circle:")

    st.caption("Each point is the time gap between two taps — a flat line means a steady rhythm; spikes mean the gap varied.")
    st.line_chart(result["intervals_ms"])

    with st.expander("Technical details"):
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Jitter (CV)",
            result["jitter_cv"],
            help="How irregular the gap between taps is. Lower = steadier rhythm; higher = the timing wobbles more.",
        )
        col2.metric(
            "Micro-hesitations",
            result["hesitation_count"],
            help="Taps where the pause beforehand was over 1.5x the usual gap — a brief stall mid-tapping.",
        )
        col3.metric(
            "Fatigue slope",
            f"{result['slope_ms_per_tap']} ms/tap",
            help="Whether taps got slower over the trial. Positive = slowing down (possible fatigue); near-zero or negative = steady or speeding up.",
        )


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
        self.lock = threading.Lock()
        self.samples: list = []

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
            with self.lock:
                self.samples.append(sample)
        _draw_hand_overlay(img, result)
        return av.VideoFrame.from_ndarray(img, format="bgr24")


# Auto-request the camera as soon as the page loads, instead of making the person click
# Start. desired_playing_state hides streamlit-webrtc's own Start/Stop/Select-device
# buttons and makes playing state Python-controlled, so we provide our own Stop/Start
# toggle below.
if "cv_motor_want_playing" not in st.session_state:
    st.session_state.cv_motor_want_playing = True

ctx = webrtc_streamer(
    key="cv-motor-test",
    video_processor_factory=HandTapProcessor,
    # Plain {"video": True} lets the browser pick its own default, which on some
    # cameras crops in tight. Ask for a standard 720p frame instead.
    media_stream_constraints={
        "video": {"width": {"ideal": 1280}, "height": {"ideal": 720}},
        "audio": False,
    },
    desired_playing_state=st.session_state.cv_motor_want_playing,
)

if st.session_state.cv_motor_want_playing:
    if st.button("Stop", icon=":material/stop:"):
        st.session_state.cv_motor_want_playing = False
        st.rerun()
elif st.button("Start again", icon=":material/videocam:"):
    st.session_state.cv_motor_want_playing = True
    st.session_state.cv_motor_last_n_taps = 0
    st.rerun()

st.caption("The camera starts automatically — allow access when your browser asks. Wait ~1s for it to settle, tap for ~15-30s, click Stop, then Analyze.")
# The first ~1s after the camera opens is skipped: MediaPipe's landmark lock-on is
# unstable right as a hand enters frame, which was registering as spurious early taps.
WARMUP_S = 1.0
if "cv_motor_last_n_taps" not in st.session_state:
    st.session_state.cv_motor_last_n_taps = 0


@st.fragment(run_every="0.3s")
def live_tap_feedback():
    # streamlit-webrtc tears its worker down on Stop, so ctx.video_processor goes
    # back to None right after — stash the last live instance for Analyze below.
    if ctx.state.playing and ctx.video_processor:
        st.session_state["cv_motor_processor"] = ctx.video_processor
        with ctx.video_processor.lock:
            samples_so_far = [s for s in ctx.video_processor.samples if s[1] >= WARMUP_S]
        n_taps = len(detect_taps(samples_so_far))
    else:
        n_taps = st.session_state.cv_motor_last_n_taps
    st.metric("Taps detected so far", n_taps)
    if n_taps > st.session_state.cv_motor_last_n_taps:
        # ponytail: beeps once per ~0.3s tick, not per tap instant — two taps inside
        # the same tick share one beep. Tighten run_every if that reads as laggy.
        st.audio(_beep_bytes(n_taps), format="audio/wav", autoplay=True)
        st.session_state.cv_motor_last_n_taps = n_taps


live_tap_feedback()

processor = st.session_state.get("cv_motor_processor")
if processor and st.button("Analyze recording"):
    with processor.lock:
        samples = [s for s in processor.samples if s[1] >= WARMUP_S]
    render_result(tap_rhythm(samples))
