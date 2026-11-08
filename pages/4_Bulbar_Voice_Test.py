"""Bulbar/voice test: guided live camera + mic.

Exploratory stretch goal (context/Biohack- LBMP.md, Part 2 §2), not part of
ALS RedFlag's red-flag scoring, not a validated clinical test. Needs a secure
context (HTTPS or localhost) for browser camera/mic access. Captures video +
audio from one WebRTC stream (no ffmpeg demuxing needed).
"""
from __future__ import annotations

import threading
import time
from collections import deque

import av
import librosa
import numpy as np
import streamlit as st
from streamlit_webrtc import AudioProcessorBase, VideoProcessorBase, webrtc_streamer

from motor_face_audio import (
    FORMANT_FLAG_CV,
    JITTER_FLAG_PCT,
    LEFT_LIP_CORNER,
    RIGHT_LIP_CORNER,
    _ensure_model,
    extract_lip_sample,
    lip_velocity,
    new_face_landmarker,
    voice_jitter_and_formants,
    voice_tier_b,
)

TEST_SECONDS = 8
ONSET_SKIP_S = 1.0  # pitch is unstable for the first moment of any vowel, and people react late
ANALYSIS_SR = 16000  # ~10x faster than 48 kHz for pyin/LPC, and removes a 48 kHz pitch artifact
BUFFER_S = 60  # processors keep only the last minute, so an idle open tab can't grow memory
VOICE_RMS = 0.01  # ponytail: hand-picked "someone is talking" level; tune if mics differ a lot
YELLOW = (0, 255, 255)  # BGR

st.set_page_config(page_title="Bulbar/voice test", page_icon="🗣️")
st.title("Bulbar & voice test (exploratory)")
st.caption(
    "Stretch goal, not part of ALS RedFlag's scoring. Measures how steady the voice "
    "stays while holding one note, and tracks the lip corners. Not a validated clinical test."
)

with st.container(border=True):
    st.markdown(
        f"""**How it works** (about {TEST_SECONDS + 2} seconds)
1. Allow **camera and microphone** when the browser asks.
2. Face the camera until you see **Face found**.
3. Click **Start test**, then say **"aaah"** at a comfortable pitch and hold it until the bar fills.
4. The result appears on its own."""
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
        self.last_face_at = 0.0
        self.lock = threading.Lock()
        self.samples: deque = deque(maxlen=30 * BUFFER_S)

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
        now = time.time()
        sample = extract_lip_sample(result, now)  # wall-clock, so it lines up with the audio
        if sample:
            self.last_face_at = now
            with self.lock:
                self.samples.append(sample)
            h, w = img.shape[:2]
            face = result.face_landmarks[0]
            for idx in (LEFT_LIP_CORNER, RIGHT_LIP_CORNER):
                cv2.circle(img, (int(face[idx].x * w), int(face[idx].y * h)), 8, YELLOW, 2)
        else:
            cv2.putText(img, "Look at the camera", (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, YELLOW, 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")


class VoiceProcessor(AudioProcessorBase):
    def __init__(self) -> None:
        self.sample_rate = 48000
        self.lock = threading.Lock()
        self.chunks: deque = deque(maxlen=50 * BUFFER_S)  # WebRTC sends ~50 frames/s

    def recv(self, frame):
        raw = frame.to_ndarray()
        scale = np.iinfo(raw.dtype).max if np.issubdtype(raw.dtype, np.integer) else 1.0
        # Browser audio arrives packed, shape (1, samples * channels) with L/R interleaved,
        # so averaging over axis 0 would read stereo as double-length mono at half the pitch.
        if frame.format.is_planar:
            mono = raw.mean(axis=0)
        else:
            mono = raw.reshape(-1, len(frame.layout.channels)).mean(axis=1)
        with self.lock:
            self.sample_rate = frame.sample_rate
            self.chunks.append((time.time(), (mono / scale).astype(np.float32)))
        return frame

    def clip(self, start: float, end: float) -> np.ndarray:
        with self.lock:
            parts = [c for t, c in self.chunks if start <= t <= end]
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def level(self) -> float:
        y = self.clip(time.time() - 0.5, time.time())
        return float(np.sqrt(np.mean(y**2))) if len(y) else 0.0


def analyze(video: LipProcessor, audio: VoiceProcessor, start: float) -> dict:
    start, end = start + ONSET_SKIP_S, start + TEST_SECONDS
    with video.lock:
        lips = [s for s in video.samples if start <= s[0] <= end]
    y = audio.clip(start, end)
    voice = tier_b = None
    if len(y):
        y = librosa.resample(y, orig_sr=audio.sample_rate, target_sr=ANALYSIS_SR)
        voice = voice_jitter_and_formants(y, ANALYSIS_SR)
        tier_b = voice_tier_b(y, ANALYSIS_SR)
    return {"voice": voice, "lips": lip_velocity(lips), "lip_frames": len(lips), "tier_b": tier_b}


STATUS = {
    "ok": ":green[:material/check_circle:] **Steady**",
    "flag": ":orange[:material/flag:] **Flagged**",
    "na": ":gray[:material/remove_circle:] **Not measured**",
}


def render_result(r: dict) -> None:
    voice = r["voice"]
    if not voice or voice["jitter_pct"] is None:
        st.warning(
            'We could not hear a steady "aaah". Move closer to the microphone, then retake.',
            title="Not enough voice captured",
            icon=":material/mic_off:",
        )
        return

    jitter, formant = voice["jitter_pct"], voice["formant_stability_cv"]
    pitch_status = "flag" if jitter > JITTER_FLAG_PCT else "ok"
    formant_status = "na" if formant is None else ("flag" if formant > FORMANT_FLAG_CV else "ok")
    flagged = [
        name for name, s in (("pitch steadiness", pitch_status), ("voice resonance", formant_status)) if s == "flag"
    ]

    if flagged:
        st.warning(
            f"Flagged: {' and '.join(flagged)}. A cold, tiredness or a noisy room can do this too. "
            "If it shows up again on a retake, it is worth mentioning to a doctor.",
            title="Some voice changes worth a clinician's look",
            icon=":material/report:",
        )
    else:
        st.success(
            "Pitch and resonance held steady through the note.",
            title="No voice warning signs in this recording",
            icon=":material/check_circle:",
        )

    with st.container(border=True):
        st.markdown(
            f"{STATUS[pitch_status]} · Pitch steadiness — your pitch moved {jitter}% from moment "
            f"to moment (flagged above {JITTER_FLAG_PCT}%)."
        )
        formant_text = (
            "not enough clear voice to measure."
            if formant is None
            else f"the vowel's sound shape varied by {formant:.0%} (flagged above {FORMANT_FLAG_CV:.0%})."
        )
        st.markdown(f"{STATUS[formant_status]} · Voice resonance — {formant_text}")
        lips_ok = r["lips"]["mean_velocity"] is not None
        st.markdown(
            f"{STATUS['ok' if lips_ok else 'na']} · Face tracking — lip corners followed in "
            f"{r['lip_frames']} frames (shown for transparency, not scored)."
        )

    st.caption(
        ":material/info: Screening aid for research, not a diagnosis. It cannot tell whether "
        "someone has ALS — only a neurologist can, with a full examination."
    )

    with st.expander("Technical details"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Pitch jitter", f"{jitter}%", help="Mean frame-to-frame change in pitch (librosa pyin).")
        col2.metric("F0 SD (Hz)", voice["f0_sd"], help="Pitch standard deviation; the strongest single feature in VOC-ALS.")
        col3.metric("Formant CV", formant if formant is not None else "—", help="Frame-to-frame variability of F1/F2 (LPC).")
        lips = r["lips"]
        col1, col2 = st.columns(2)
        col1.metric("Mean lip velocity", lips["mean_velocity"] if lips_ok else "—")
        col2.metric("Lip velocity CV", lips["velocity_cv"] if lips_ok else "—")
        st.caption("Lip movement is not used in the summary: it has not been calibrated for a held vowel.")
        tier_b = r["tier_b"]
        if tier_b:
            st.metric("Research voice model score (0-1)", tier_b["risk_probability"])
            st.caption(f"{tier_b['source']}. {tier_b['caveat']}")
        else:
            st.caption("Research voice model unavailable for this clip; heuristics only.")


ss = st.session_state
ss.setdefault("bulbar_want_playing", True)
ss.setdefault("bulbar_test_start", None)
ss.setdefault("bulbar_result", None)

ctx = webrtc_streamer(
    key="bulbar-voice-test",
    video_processor_factory=LipProcessor,
    audio_processor_factory=VoiceProcessor,
    media_stream_constraints={
        "video": {"width": {"ideal": 1280}, "height": {"ideal": 720}},
        "audio": True,
    },
    # Auto-starts on page load and hides streamlit-webrtc's Start/Select-device buttons.
    desired_playing_state=ss.bulbar_want_playing,
    sendback_audio=False,  # otherwise the mic plays back through the speakers and echoes
)


@st.fragment(run_every="0.3s")
def live_panel() -> None:
    video, audio = ctx.video_processor, ctx.audio_processor
    if not (ctx.state.playing and video and audio):
        if ss.bulbar_result is None:
            st.caption("Waiting for camera and microphone access…")
        return

    now, start = time.time(), ss.bulbar_test_start
    hearing = audio.level() >= VOICE_RMS
    with st.container(horizontal=True):
        if now - video.last_face_at < 1.0:
            st.badge("Face found", icon=":material/face:", color="green")
        else:
            st.badge("Face not found — look at the camera", icon=":material/visibility_off:", color="orange")
        if hearing:
            st.badge("Hearing you", icon=":material/mic:", color="green")
        elif start is not None:
            st.badge("Louder, please", icon=":material/volume_up:", color="orange")
        else:
            st.badge("Microphone on", icon=":material/mic:", color="gray")

    if start is None:
        return
    elapsed = now - start
    if elapsed >= TEST_SECONDS:
        with st.spinner("Analyzing…"):
            ss.bulbar_result = analyze(video, audio, start)
        ss.bulbar_want_playing = False  # recording done: release camera and mic
        st.rerun(scope="app")
    st.progress(elapsed / TEST_SECONDS, text=f'Keep saying "aaah"… {TEST_SECONDS - elapsed:.0f}s left')


def _start_test() -> None:
    ss.bulbar_test_start = time.time()


def _reset() -> None:
    ss.bulbar_result = None
    ss.bulbar_test_start = None
    ss.bulbar_want_playing = True


live_panel()

if ss.bulbar_result is not None:
    render_result(ss.bulbar_result)
if ss.bulbar_test_start is None:
    st.button(
        "Start test",
        type="primary",
        icon=":material/play_arrow:",
        disabled=not ctx.state.playing,
        on_click=_start_test,
    )
else:
    st.button("Retake test", icon=":material/replay:", on_click=_reset)
