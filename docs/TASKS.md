# Tasks

Statuses: **TODO** · **DOING** · **REVIEW** · **MERGED** · **CUT**

Rule: every task names the `docs/DEMO.md` step it serves. No demo step → it goes to the bottom or gets CUT.

| # | Task | Owner | Branch | Status | Demo step | Notes |
|---|---|---|---|---|---|---|
| 1 | Deploy hello-world to prod URL | Bruce (lead) | `feat/deploy` | TODO | all | **Due within the first 3h.** Streamlit Community Cloud or Vultr; put the URL in `docs/DEMO.md` |
| 2 | Core pipeline: extract / score / timeline | Peter | `main` | MERGED | 2, 3 | Commits d871883..dfe201b |
| 3 | Type Alex's notes into `data/alex/` (6 notes, case file pp. 7–9) | Bruce | `feat/alex-notes` | REVIEW | 1 | 6 notes typed; Claude verifies them against case file pp. 7-9 |
| 4 | Replace placeholder weights with Gold Coast + ReferALS rules | Mia | `feat/rules` | MERGED | 3 | Gold Coast + ReferALS/RACE rules in `rules.json` (commit 9f5714c). Do not tune weights on Alex alone (n=1) |
| 5 | Streamlit UI (`app.py`) | Bruce | `feat/app` | MERGED | 1–5 | Uses `run_timeline`, `first_flag`, `score` per `docs/interfaces.md`. Status was stale TODO; already merged via PR #7 |
| 6 | `evaluate.py`: Alex timeline + mimic cases, print numbers | Bruce | `feat/evaluate` | MERGED | 3, 5 | Numbers go in README and pitch |
| 7 | Fix README "December 2024 / 19 months" claim | Peter | `fix/readme-numbers` | REVIEW | 3 | Offline fallback fixed; offline and Gemini both give 2024-12-09, 19.1 months (`evaluate.py`). Branch `fix/offline-fallback` |
| 8 | Mimic notes (carpal tunnel, radiculopathy, neuropathy) that must score low | Linh | `feat/mimics` | MERGED | 5 | 3 notes in `data/mimics/`, all LOW. Linh's ~30 test cases still needed |
| 9 | Devpost write-up + 60 s pitch + slides | <owner> | n/a | TODO | all | Due Sun 11:30 AM |
| 10 | Claude Code kit (hooks, skills, docs, worktree script) | Bruce | `claude/epic-wright-7qyy63` | DOING | n/a | Built and tested; commit bb444c3 is local only. Push blocked (403: Claude GitHub App not installed on WooRainingDay). See `.claude/sessions/2026-11-07-2105-claude-epic-wright-7qyy63.md` |
| 11 | Part 2 digital biomarkers: CV finger-tap + bulbar/voice motor test | Bruce | `feat/motor-test` | REVIEW | 6 | `motor_cv.py`, `motor_face_audio.py`, pages 3-4; real MediaPipe + librosa, exploratory, not folded into `rules.json`. Needs real sample clips in `data/motor_samples/` before judging |
| 12 | Data-model grounding: VOC-ALS voice baseline + TORGO external check + gait method validation | Bruce | `feat/data-models` | REVIEW | 6 | Plan: `docs/plans/als-data-models.md` Steps 1-3, 5 (partial), 6 (voice), 8 (partial). VOC-ALS CV AUC 0.64 (95% CI 0.57-0.71); TORGO external AUC 0.544 (domain shift, disclosed honestly). NeuroFace/Answer ALS finger-tap calibration still pending data access. merge-reviewer: MERGE (3 rounds total) |
