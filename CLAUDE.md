# CLAUDE.md

BioHacks 2026 (McMaster, 7–8 Nov 2026), **Detection and Diagnostics** track. Devpost due **Sun 11:30 AM**; expo judging Sun 1:30–3:00 PM. Patient case: Alex Chen (see `docs/PRD.md`).

## What we're building

**ALS RedFlag**: reads a patient's clinical notes (GP referrals, consults, physio summaries) in date order, extracts ALS red-flag findings with Gemini, scores them against rules and the Gold Coast pattern, and shows the first date an urgent neurology referral was warranted, with quoted evidence. It supports clinical decisions; it does not diagnose.

Demo path: `docs/DEMO.md`. Every feature must serve a step there.

> Open decision (see Decisions log): the team brainstorm also proposed a home motion/voice app plus a biofluid test strip. Not built. Do not start it without the lead's go-ahead.

## Stack and commands

Python 3.11+, Gemini via `google-genai`, pydantic, Streamlit UI, pytest.

| Task | Command |
|---|---|
| Setup | `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env` |
| Dev (UI) | `streamlit run app.py` <!-- app.py not written yet --> |
| Dev (CLI, no key) | `python timeline.py data/sample --offline --diagnosis=2025-03-18` |
| Build | n/a |
| Lint | `ruff check .` |
| Typecheck | n/a |
| Test | `python -m pytest -q` |

Env vars: see `.env.example` (`GEMINI_API_KEY`, optional `GEMINI_MODEL`, `GEMINI_MIN_INTERVAL`).

## Team and ownership

| Person | Role | Owns |
|---|---|---|
| Bruce | Lead | `main` (merges), `app.py`, `evaluate.py` |
| Peter | Pipeline | `extract.py`, `score.py`, `timeline.py`, `schema.py` |
| Mia | Clinical rules | `rules.json` (Gold Coast + ReferALS) |
| Linh | Test cases | `data/` test notes, evaluation cases |
| <name> | <role> | <files> |

Ownership above is inferred from `docs/interfaces.md` and `rules.json`; the lead should confirm it.

## Shared files

Edit only with the owner's OK, and say so in the PR:

- `schema.py`: findings schema used by every module
- `score.py` (`combine`, `score` signatures) and `timeline.py` (`run_timeline`, `first_flag`)
- `rules.json`
- `docs/interfaces.md`
- `requirements.txt`, `.env.example`
- `CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/*`

## Rules

- Hackathon code: **demo path first**. No new test suites or coverage targets (keep the existing tests passing).
- Files under ~300 lines. Prefer a new file over growing a shared one.
- No new dependencies without asking the lead.
- No hardcoded secrets. Every new env var goes in `.env.example`.
- No `console.log` in JS/TS; no stray debug `print()` in app code (CLI `__main__` blocks are fine).
- No new `.md` files outside `docs/` and `.claude/` (README.md and CLAUDE.md excepted).
- Use CLIs for services (`gh`, `vercel`, `supabase`) rather than clicking through dashboards.
- Check current docs (context7 or `/llms.txt`) before writing third-party API code. The Gemini SDK changes often.
- Clinical claims in UI, README or pitch must be traceable to the case file or a cited source. Any number shown to judges must be reproducible with a command.

## Workflow

1. Build features with the **feature** skill (research → plan in `docs/plans/` → approval → implement → review → verify).
2. Before merging into `main`: run the **merge-reviewer** subagent and the **demo-check** skill.
3. Before `/clear` or ending a session: run the **handoff** skill.
4. Parallel work: `scripts/new-worktree.sh <name>` gives each person or session its own checkout and branch.
5. Track work in `docs/TASKS.md`.
6. To work through tasks with self-review, use the **redflag-loop** skill (machine-checkable acceptance, independent judge, max 3 rounds, user approves plan and merge). Never loop on a task without an acceptance command.
7. Before anything reaches judges (README, Devpost, slides, UI text): run the **claim-check** skill.
8. Optional ECC skills (MIT, `.claude/skills/`): `loop-design-check` (design or review a loop), `santa-method` (dual independent review), `parallel-execution-optimizer` (split work into lanes), `scientific-db-pubmed-database` (citations), `ui-demo` (backup demo video; Streamlit runs on port 8501, not 3000), `frontend-slides` (pitch slides).

## Context files (local, not in git)

`context/` holds the BioHacks case PDF (Alex's notes pp. 7-15, rubric p. 20), the original brainstorm `Biohack- LBMP.md` (strip + home app, both dropped) and session handoffs. Read them when you need case facts; never commit them.

## Decisions log

| Date | Decision | Why / notes |
|---|---|---|
| 2026-11-07 | Track 1: Detection and Diagnostics | Locked on team form |
| 2026-11-07 | Build ALS RedFlag (notes → findings → rules → timeline) on `main` | Targets Alex's real failure: clinicians each saw part of the pattern |
| 2026-11-07 | Default model `gemini-3.5-flash`, low thinking | ~2 s per note vs ~3 min on 3.8-flash, same findings (per commit dfe201b) |
| 2026-11-07 | README "flagged December 2024, ~19 months" claim is **not verified** | Offline run on Alex's notes: first HIGH 2026-02-10 (5.1 months before diagnosis). Perfect extraction would give 2025-04-21 (~15 months). Re-measure with Gemini before using any number |
| <date> | Open: keep RedFlag only, or add the brainstorm's motion/voice test? | <decision> |
