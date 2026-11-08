# Plan: Live camera/mic mode for the Part 2 motor-test pages

Adds real-time webcam/mic capture to `pages/3_CV_Motor_Test.py` and
`pages/4_Bulbar_Voice_Test.py`, alongside (not replacing) the existing
upload-a-clip flow from `docs/plans/motor-sensor-part2.md`. Upload stays as
the demo-reliability fallback if live capture has issues at judging time.

## Goal

Enhances `docs/DEMO.md` step 6 (the digital-biomarker stretch demo): judges
can run the finger-tap and voice test live in the browser, no pre-recording
needed, while the already-tested upload path remains available if WebRTC has
trouble on the judging-room network.

## Feasibility check (done)

`streamlit-webrtc` resolves cleanly and installs with prebuilt wheels here
(macOS arm64, no native build needed): `aiortc`, `av`, `streamlit-webrtc`
installed, imports verified. PyAV/aiortc publish manylinux wheels, so the
Vultr box (Ubuntu) should install the same way — **to confirm on that box
before judging**, not guessed.

## Files to touch

| File | Change |
|---|---|
| `requirements.txt` | Add `streamlit-webrtc` (new dependency — flagging per "no new deps without asking the lead"; this plan *is* that ask) |
| `motor_cv.py` | Add `extract_hand_sample(result, timestamp_s)` — pulls the existing thumb/index-tip logic out of `load_hand_landmarks`'s frame loop into a reusable function, so the new live callback and the existing file-loop share identical extraction logic (no duplicated landmark-indexing code) |
| `motor_face_audio.py` | Same refactor: `extract_lip_sample(result, timestamp_s)`, reused by both the file loop and the new live callback |
| `pages/3_CV_Motor_Test.py` | Add a mode choice ("Upload a clip" / "Live camera"). Live mode: `streamlit_webrtc.webrtc_streamer` with a `VideoProcessorBase` that runs HandLandmarker per frame and appends to a thread-safe buffer (`queue.Queue`, since the WebRTC callback runs on its own thread, not Streamlit's script thread); a "Stop & analyze" button reads the buffer and calls the *same* `tap_rhythm()` used by the upload path |
| `pages/4_Bulbar_Voice_Test.py` | Same pattern for lip tracking (video) and for audio — buffer raw PCM frames from the WebRTC audio track, pass the real sample rate straight into `voice_jitter_and_formants(y, sr)` (no resampling needed, `sr` is already a parameter) |

No changes to `motor_cv.py`/`motor_face_audio.py`'s public scoring functions
(`tap_rhythm`, `lip_velocity`, `voice_jitter_and_formants`) — both capture
modes feed the same analysis code, so nothing scored differently between
upload and live.

## Steps

1. `extract_hand_sample` / `extract_lip_sample` refactor in both modules — pure
   function extraction, re-run existing self-checks to confirm no behavior
   change. **Commit:** `refactor: extract per-frame sample logic for reuse by live capture`.
2. `requirements.txt` + live mode on `pages/3_CV_Motor_Test.py` (hand only
   first — simpler, one media stream, proves the WebRTC pattern works before
   doing the two-stream bulbar page). **Commit:** `feat: add live camera mode to CV motor test`.
3. Live mode on `pages/4_Bulbar_Voice_Test.py` (video + audio tracks).
   **Commit:** `feat: add live camera/mic mode to bulbar voice test`.
4. Manual test in a real browser (localhost first, then the Vultr deploy —
   WebRTC needs a STUN server for NAT traversal off localhost; `streamlit-webrtc`
   defaults to Google's public STUN, should work from a judging-room network
   to a Vultr public IP, but **this is the one thing that can't be fully
   verified until tested on real devices on real WiFi** — confirm before
   relying on it for judging).

## Acceptance check

- `python motor_cv.py` / `python motor_face_audio.py` self-checks still pass
  after the refactor (same output as before).
- `ruff check --select E9,F .` clean.
- Manual: open CV Motor Test live mode in a real browser, see the webcam
  feed, tap fingers for ~15s, hit "Stop & analyze", see a real (non-empty)
  jitter/slope readout. Same for Bulbar Voice Test with a real face + voice.
- Upload mode on both pages still works unchanged (regression check).

## Out of scope / risk

- **Time cost**: this is real new surface area (WebRTC threading, a second
  capture mode on two pages) on top of an already-shipped, tested feature,
  with the Devpost deadline tomorrow 11:30 AM. If step 2 (hand, live) eats
  more time than expected, stop there — upload-only stays fully demo-ready
  regardless, nothing here is a regression risk to what's already merged.
- Mobile browser camera permissions / HTTPS requirement: WebRTC camera
  access generally requires a secure context. The Vultr demo is plain HTTP
  (`http://108.61.193.162:8501`) — **most browsers block camera access on
  plain HTTP for non-localhost origins.** This needs checking before relying
  on live camera for judging; if it's blocked, the fix is HTTPS (e.g. a free
  Caddy/certbot reverse proxy) or keep live mode as a "works on localhost
  for the team, upload for judges" split. Flagging this now since it could
  make live-camera unusable on the deployed URL regardless of code quality.
