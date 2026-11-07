# Plan: `evaluate.py` (TASKS.md row 6)

## Task
Print Alex's timeline number (first HIGH date, months before diagnosis) and score every
mimic note in `data/mimics/`, confirming each stays LOW. Demo steps 3, 5. Numbers here are
the only ones allowed in README/UI/Devpost (CLAUDE.md rule).

## Design (reuses existing interfaces only, no shared-file edits)
- `evaluate.py` at repo root, calls `run_timeline`/`first_flag` (timeline.py) and
  `extract_findings`/`score` (extract.py/score.py) exactly as `docs/interfaces.md` defines them.
- Alex: `run_timeline("data/alex", offline=...)`, print first-HIGH date + months before a
  diagnosis date (default `2026-07-14`, from the diagnosis letter, PDF p.13; overridable with
  `--diagnosis=YYYY-MM-DD`).
- Mimics: scores every `.txt` in `data/mimics/` individually (one note = one presentation,
  not a timeline). If the directory doesn't exist yet (TASKS row 8, Linh, still TODO), prints
  that plainly instead of fabricating a result — does not create mimic content itself.
- Exit code: 0 normally, 1 if any mimic scores above LOW (so CI/the loop's judge can catch it
  once mimics exist).
- No new test file: CLAUDE.md says no new test suites; the script's own exit code is the check.

## Open decisions (deciding now, won't re-ask mid-loop)
1. **Default extractor = auto-detect, same as `timeline.py` (`offline=None`): Gemini if
   `GEMINI_API_KEY` is set, keyword fallback otherwise.** Bruce asked for highest accuracy —
   the keyword fallback is known to miss findings (handoff notes: misses "no improvement",
   "within normal limits", "foot catching"), so Gemini is the more accurate path when a key is
   available, and this repo's `.env` has one. Output always prints which mode actually ran, so
   a number is never silently mislabeled. `--offline` forces the deterministic keyword path —
   used by the acceptance check's task-specific command so judge PASS/FAIL doesn't depend on
   whether a given machine happens to have a key.
2. **Mimics absent today is not a failure.** `data/mimics/` doesn't exist; row 8 is still TODO.
   `evaluate.py` reports "none yet" rather than blocking or inventing notes.
3. **Diagnosis date hardcoded default `2026-07-14`.** Matches the diagnosis letter and the
   CLAUDE.md decisions log.

## Acceptance check
- `python -m pytest -q` → 0 exit, 6 passed (unchanged).
- `ruff check --select E9,F .` → clean (unchanged).
- `python evaluate.py --offline` → exit 0, prints (deterministic, the judge's grading command):
  - `First HIGH risk: 2026-02-10 (2026-02-10_physio.txt), 5.1 months before diagnosis (2026-07-14)`
  - `Mimic cases ... none in data/mimics/ yet (TASKS.md row 8)`
- `python evaluate.py` (no flags, real Gemini key) → exit 0:
  - `First HIGH risk: 2024-12-09 (2024-12-09_surgery.txt), 19.1 months before diagnosis (2026-07-14)`
  - This matches commit `9f5714c`'s own number, reproduced independently on **our** verified
    `data/alex/` set (not the teammate's) — a real cross-check, not an artifact of their files.
- Stored baseline for the judge to diff against: the offline 5.1-month number. A changed
  offline number is a FAIL to report, not a baseline to overwrite. The Gemini number is
  informational (network/key dependent) but is now corroborated, so it is safe to use in
  README/Devpost once `claim-check` runs — not done by this task.

## Branch note
`feat/evaluate` branches from `origin/main` (which already has Mia's real
Gold Coast/ReferALS `rules.json` + `score.py`, commit `9f5714c`), not from `feat/app`. A
teammate's commit `1fbb64c` added a second, differently-named `data/alex/` set (pp.7-12,
not verified against the PDF) that would have duplicated same-date notes with ours if both
landed in `data/alex/`. Removed their set from this branch only (main is untouched; that
conflict is main's to resolve via PR review) and kept our word-for-word-verified 6 files.
