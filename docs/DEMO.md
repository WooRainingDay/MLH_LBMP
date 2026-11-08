# Demo script

Target length: **3 minutes** at the judging table (Sun 1:30–3:00 PM, MCCD 7110/7120). Judges come to us; expect them to ask "how do you know it works?" and "how is this different from ReferALS?".

## URLs

| | URL |
|---|---|
| Live | http://108.61.193.162:8501 |
| Backup (local) | `streamlit run app.py` → http://localhost:8501 |
| Backup (no network, no key) | `python timeline.py data/alex --offline --diagnosis=2026-07-14` |
| Devpost | https://biohacksmcmaster.devpost.com |

## Script

| Step | Action | Expected result |
|---|---|---|
| 0 | Opening line: "Alex waited 25 months. Four clinicians each saw part of the pattern." | Problem slide on screen |
| 1 | Open the app, select patient **Alex Chen** (notes in `data/alex/`) | Six notes listed in date order, Oct 2024 → Jun 2026 |
| 2 | Step through the timeline note by note | Each note shows the findings it added (e.g. wasting, twitching, brisk reflexes) with the quoted sentence from the note |
| 3 | Stop at the first **HIGH** risk note | Banner: first flagged date, and "<N> months before diagnosis". N must come from `evaluate.py`, not from memory. If `ELEVENLABS_API_KEY` is set, a spoken alert plays automatically - same numbers as the banner, read aloud ("the call that never came"); with no key, this is silent and nothing else changes |
| 4 | Open the reasons panel for that note | Points breakdown, Gold Coast status, and advice: urgent neurology referral, request EMG, consider serum NfL |
| 5 | Load the carpal-tunnel mimic note | Risk **LOW**: numbness/tingling and positive Phalen's point away from ALS |
| 6 | Optional stretch: open **CV Motor Test**, camera starts automatically — allow access, wait ~1s, tap thumb-to-index in front of the camera, watch the live tap counter and the yellow hand-tracking overlay, click Stop, then Analyze; open **Bulbar Voice Test** the same way (camera + mic) | MediaPipe hand/face tracking + librosa pitch/formant readouts render live, explicitly labeled exploratory and separate from ALS RedFlag's clinical score, with a plain-language summary before the technical numbers. Bulbar Voice Test also shows a **Tier B** score from a model trained and cross-validated on the public VOC-ALS dataset (n=153 subjects, 1224 recordings, subject-level CV AUC 0.64 [95% CI 0.57-0.71], sens 0.90, spec 0.19 - `python research/report.py` reproduces every number), with full source, the specificity/CI caveat, AND a domain-shift note citing the actual measured drop (TORGO external check: AUC fell to 0.54, near chance) cited on screen - answers "how do you know it works?" **and** "does it generalize?" honestly, including the honest negative |
| 7 | Close: limits and next step | n=1 fictional case; invented test notes; next: retrospective validation on real referral letters, and a findings report patients/clinicians could save to their phone (would need PHI/Health Canada clearance - not built) |

## Seeded data and reset

- Patient notes: `data/alex/*.txt` (typed from the case file), `data/sample/*.txt` (invented patient for tests).
- Step 6 (motor/bulbar stretch): **live camera + mic only** (upload was removed). Test it
  once on the demo machine beforehand — good lighting, hand/face fully in frame — since
  there's no pre-recorded fallback clip. The first run of each page downloads a MediaPipe
  model bundle (needs network once); after that it's cached in `.cache/models/`.
- Tier B voice score needs `models/voice_baseline.joblib` (gitignored, not on a fresh clone/Vultr). Run `python research/fetch_data.py` then `python research/voice_features.py` then `python research/train_voice.py` once on whichever machine demos - otherwise the page silently falls back to the Tier C heuristic.
- Gemini results are cached in `.cache/extract/`. To force a fresh run: `rm -rf .cache/extract`.
- Before judging: run the demo once with the key set so every note is cached; then the demo works even if the network or quota fails.
- Reset UI state: restart Streamlit (`Ctrl+C`, then `streamlit run app.py`).
