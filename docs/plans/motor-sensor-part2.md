# Plan: Part 2 — Software Motion & Sensor Tracking (Digital Biomarkers)

Source spec: `context/Biohack- LBMP.md`, "Part 2" (verbatim, via research subagent):
> Use computer vision (OpenCV/MediaPipe pose tracking) ... to record rapid finger tapping
> ... measure frequency jitter, micro-hesitations, and rhythm degradation over a 30-second
> trial. Combine facial keypoint tracking (lip corner velocity during speech) with audio
> analysis of sustained vowels (pitch perturbation and formant stability using librosa).

This plan builds that **exactly as specified** — real CV hand/face landmark tracking and
real librosa pitch/formant analysis, not the simplified button-tap stand-in already on this
branch. `motor_test.py` / `pages/2_Motor_Test.py` stay untouched as a live-demo fallback.

## Goal

Serves a **new** `docs/DEMO.md` step (no existing step covers this — per `docs/TASKS.md`'s
own rule, a demo step must exist for a task to be plan-eligible, so this plan adds one):
insert a new step 6 ("digital-biomarker stretch demo") between the current step 5 (mimic
note) and step 6 ("close"), which becomes step 7. One sentence: *show a finger-tap clip and
a sustained-vowel clip each producing an exploratory motor/bulbar biomarker reading,
explicitly separate from ALS RedFlag's clinical score.*

## Files to touch

All NEW files except two doc edits (neither is on `CLAUDE.md`'s shared-file list):

| File | New/Edit | Purpose |
|---|---|---|
| `motor_cv.py` | New | Hand-landmark tap-interval extraction: jitter, micro-hesitations, rhythm-degradation slope |
| `motor_face_audio.py` | New | Face-landmark lip-corner velocity + librosa F0 jitter + librosa.lpc formant stability |
| `pages/3_CV_Motor_Test.py` | New | Streamlit page: upload a finger-tap video → `motor_cv` → chart |
| `pages/4_Bulbar_Voice_Test.py` | New | Streamlit page: upload a speech video + a vowel audio clip → `motor_face_audio` → chart |
| `data/motor_samples/` | New | One sample finger-tap video, one sample vowel audio clip, so the demo and the acceptance check don't depend on live capture |
| `docs/DEMO.md` | Edit | Insert new step 6, renumber old step 6→7; note model auto-download + sample clips |
| `docs/TASKS.md` | Edit | Fill template row #11 with this task (owner Bruce, branch `feat/motor-test`, demo step 6); flag row #5 as stale (`app.py` is already built, not TODO) |
| `.gitignore` | Edit | Ignore the downloaded `.task` model-bundle cache dir (binary, re-downloadable) |

No new line in `requirements.txt` — `opencv-python`, `mediapipe`, `librosa` are already
there; `numpy`/`scipy` arrive transitively (scipy via librosa, used for `scipy.signal.find_peaks`
peak detection — reuse, not a new dependency). No `rules.json`/`score.py` edit — that's Mia's
file; motor-test output stays a separate, clearly-labeled "exploratory" reading, never folded
into the clinical risk score.

## Steps

1. **`motor_cv.py`** — pure function `tap_rhythm(landmark_samples: list[tuple[float, float, float]]) -> dict`
   taking `(thumb_tip_x, index_tip_x, timestamp_s)`-style samples, finds thumb-index distance
   peaks (`scipy.signal.find_peaks`), returns inter-tap intervals + jitter (coefficient of
   variation) + rhythm-degradation slope (same least-squares approach as `motor_test.py`) +
   micro-hesitation count (intervals >1.5× the trial median). Plus a `load_hand_landmarks(video_path)`
   wrapper around MediaPipe `HandLandmarker` (VIDEO running mode, per the official Python Tasks
   API) that downloads the official `hand_landmarker.task` model bundle to a local cache on
   first use (exact download URL confirmed from MediaPipe's official docs page at
   implementation time — not guessed). Self-check (`demo()`/`__main__`) runs `tap_rhythm` on a
   synthetic thumb-index signal, no camera needed. **Commit:** `feat: add motor_cv tap-rhythm extraction`.
2. **`pages/3_CV_Motor_Test.py`** — upload a video, decode frames with OpenCV, run
   `load_hand_landmarks` + `tap_rhythm`, show the interval chart + jitter/hesitation/slope
   readout, same disclaimer caption style as `pages/2_Motor_Test.py`. **Commit:**
   `feat: add CV finger-tap motor-test page`.
3. **`motor_face_audio.py`** — `lip_velocity(landmark_samples)` (pure function, face-mesh
   lip-corner landmarks 61/291, frame-to-frame displacement / dt) + `voice_jitter_and_formants(y, sr)`
   (librosa `pyin` → F0 track → mean relative frame-to-frame F0 change as jitter;
   librosa `lpc` on short frames → formant frequencies via polynomial roots → std as
   formant-stability score) + a `load_face_landmarks(video_path)` wrapper (MediaPipe
   `FaceLandmarker`, VIDEO mode, same download-cache pattern as step 1). Self-check with
   synthetic landmark + synthetic sine-wave audio, no mic/camera needed. **Commit:**
   `feat: add bulbar lip-velocity and voice jitter/formant analysis`.
4. **`pages/4_Bulbar_Voice_Test.py`** — two uploaders (video for lip tracking, audio for
   voice — kept separate to avoid adding an ffmpeg/moviepy dependency for audio-from-video
   demuxing), wires to `motor_face_audio`, shows both readouts. **Commit:**
   `feat: add bulbar/voice motor-test page`.
5. **Docs + sample data** — record/add the two sample clips to `data/motor_samples/`, insert
   the new `docs/DEMO.md` step, fill `docs/TASKS.md` row #11, flag row #5, add the
   `.gitignore` line. **Commit:** `docs: add motor-test demo step and sample clips`.

## Acceptance check

- `python motor_cv.py` → prints "all checks passed" (synthetic signal, no camera).
- `python motor_face_audio.py` → prints "all checks passed" (synthetic signal, no mic).
- `ruff check --select E9,F .` → clean.
- `python -m pytest -q` → still 6 passed, unchanged.
- Manual: `streamlit run app.py` → open "CV Motor Test" → upload `data/motor_samples/finger_tap.mp4`
  → chart + jitter/slope readout renders within ~10s, no traceback. Open "Bulbar Voice Test" →
  upload `data/motor_samples/vowel.wav` (+ optional video) → F0-jitter and formant-stability
  readouts render.
- Model bundles download once to a local cache on first run and are reused (no re-download)
  on a second run — confirmed by a log line or cache file check.

## Out of scope

- Spiral-drawing alternative task (brainstorm's alt to finger-tapping — same signal class, not building both).
- Live webcam/mic streaming inside Streamlit — upload-then-analyze only (last session's decision; avoids `streamlit-webrtc` fragility in a judging room).
- Folding motor/bulbar output into `rules.json`/`score.py`'s clinical score — stays separate and labeled "exploratory," per Mia's ownership of `rules.json`.
- Audio-from-video demuxing via ffmpeg — two separate uploads instead.
- Phone gyroscope input — no browser/Streamlit API for it; camera CV covers the same signal.
- Deleting the existing simple tap-timing page — kept as a live-demo fallback.

## Risk flagged for the approval gate

Model-bundle downloads (hand + face `.task` files, few-MB each) need network on first run;
CV/audio inference is slower than the existing pure-Python page. Given the Sun 11:30 AM
deadline, recommend testing steps 1–2 (hand) end-to-end before starting step 3 (face+audio) —
if time runs out after step 2, steps 1–2 alone already give a real CV demo, and the DEMO.md/TASKS.md
edits in step 5 can scope down to match whatever's actually done.
