# Tasks

Statuses: **TODO** · **DOING** · **REVIEW** · **MERGED** · **CUT**

Rule: every task names the `docs/DEMO.md` step it serves. No demo step → it goes to the bottom or gets CUT.

| # | Task | Owner | Branch | Status | Demo step | Notes |
|---|---|---|---|---|---|---|
| 1 | Deploy hello-world to prod URL | Bruce (lead) | `feat/deploy` | TODO | all | **Due within the first 3h.** Streamlit Community Cloud or Vultr; put the URL in `docs/DEMO.md` |
| 2 | Core pipeline: extract / score / timeline | Peter | `main` | MERGED | 2, 3 | Commits d871883..dfe201b |
| 3 | Type Alex's notes into `data/alex/` (6 notes, case file pp. 7–9) | Bruce | `feat/alex-notes` | REVIEW | 1 | 6 notes typed; Claude verifies them against case file pp. 7-9 |
| 4 | Replace placeholder weights with Gold Coast + ReferALS rules | Mia | `feat/rules` | TODO | 3 | Do not tune weights on Alex alone (n=1) |
| 5 | Streamlit UI (`app.py`) | Bruce | `feat/app` | MERGED | 1–5 | Uses `run_timeline`, `first_flag`, `score` per `docs/interfaces.md`. Status was stale TODO; already merged via PR #7 |
| 6 | `evaluate.py`: Alex timeline + mimic cases, print numbers | Bruce | `feat/evaluate` | TODO | 3, 5 | Numbers go in README and pitch |
| 7 | Fix README "December 2024 / 19 months" claim | Peter | `fix/readme-numbers` | TODO | 3 | Offline run says 2026-02-10 (5.1 months). Re-measure with Gemini |
| 8 | Mimic notes (carpal tunnel, radiculopathy, neuropathy) that must score low | Linh | `feat/mimics` | TODO | 5 | |
| 9 | Devpost write-up + 60 s pitch + slides | <owner> | n/a | TODO | all | Due Sun 11:30 AM |
| 10 | Claude Code kit (hooks, skills, docs, worktree script) | Bruce | `claude/epic-wright-7qyy63` | DOING | n/a | Built and tested; commit bb444c3 is local only. Push blocked (403: Claude GitHub App not installed on WooRainingDay). See `.claude/sessions/2026-11-07-2105-claude-epic-wright-7qyy63.md` |
| 11 | Part 2 digital biomarkers: CV finger-tap + bulbar/voice motor test | Bruce | `feat/motor-test` | REVIEW | 6 | `motor_cv.py`, `motor_face_audio.py`, pages 3-4; real MediaPipe + librosa, exploratory, not folded into `rules.json`. Needs real sample clips in `data/motor_samples/` before judging |
| 12 | Voice baseline model on VOC-ALS (`research/train_voice.py`), subject-level CV | Bruce | `feat/data-models` | REVIEW | 6 | Plan: `docs/plans/als-data-models.md` Steps 1-2. F0 SD alone AUC 0.629 (CI 0.594-0.664). merge-reviewer verdict: MERGE |
