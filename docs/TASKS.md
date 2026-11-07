# Tasks

Statuses: **TODO** · **DOING** · **REVIEW** · **MERGED** · **CUT**

Rule: every task names the `docs/DEMO.md` step it serves. No demo step → it goes to the bottom or gets CUT.

| # | Task | Owner | Branch | Status | Demo step | Notes |
|---|---|---|---|---|---|---|
| 1 | Deploy hello-world to prod URL | Bruce (lead) | `feat/deploy` | TODO | all | **Due within the first 3h.** Streamlit Community Cloud or Vultr; put the URL in `docs/DEMO.md` |
| 2 | Core pipeline: extract / score / timeline | Peter | `main` | MERGED | 2, 3 | Commits d871883..dfe201b |
| 3 | Type Alex's notes into `data/alex/` (6 notes, case file pp. 7–9) | Linh | `feat/alex-notes` | TODO | 1 | Name files `YYYY-MM-DD_source.txt` |
| 4 | Replace placeholder weights with Gold Coast + ReferALS rules | Mia | `feat/rules` | TODO | 3 | Do not tune weights on Alex alone (n=1) |
| 5 | Streamlit UI (`app.py`) | Bruce | `feat/app` | TODO | 1–5 | Uses `run_timeline`, `first_flag`, `score` per `docs/interfaces.md` |
| 6 | `evaluate.py`: Alex timeline + mimic cases, print numbers | Bruce | `feat/evaluate` | TODO | 3, 5 | Numbers go in README and pitch |
| 7 | Fix README "December 2024 / 19 months" claim | Peter | `fix/readme-numbers` | TODO | 3 | Offline run says 2026-02-10 (5.1 months). Re-measure with Gemini |
| 8 | Mimic notes (carpal tunnel, radiculopathy, neuropathy) that must score low | Linh | `feat/mimics` | TODO | 5 | |
| 9 | Devpost write-up + 60 s pitch + slides | <owner> | n/a | TODO | all | Due Sun 11:30 AM |
| 10 | Claude Code kit (hooks, skills, docs, worktree script) | Bruce | `claude/epic-wright-7qyy63` | DOING | n/a | Built and tested; commit bb444c3 is local only. Push blocked (403: Claude GitHub App not installed on WooRainingDay). See `.claude/sessions/2026-11-07-2105-claude-epic-wright-7qyy63.md` |
| 11 | <task> | <owner> | <branch> | TODO | <step> | |
