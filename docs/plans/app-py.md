# Plan: `app.py` (TASKS.md row 5)

## Task
Streamlit UI covering `docs/DEMO.md` steps 1-6: pick a patient, step through their notes in
date order with quoted evidence, see the first HIGH-risk flag with months-before-diagnosis,
see the reasons/advice panel, load a mimic note and see it score LOW.

## Design (reuses existing interfaces only, no shared-file edits)
- Single-file `app.py` at repo root. Calls `run_timeline`/`first_flag` (timeline.py),
  `months_between` (timeline.py). No new dependency — `streamlit` is already in requirements.txt.
- **Sidebar:** patient/dataset picker = every subdirectory of `data/` (dynamic glob, not
  hardcoded — so `data/mimics/` just appears once someone adds it); offline/Gemini toggle;
  diagnosis-date input (default `2026-07-14`, same default as `evaluate.py`).
- **Main area:** one expandable block per note, oldest first — date, source, risk badge
  (low/medium/high color), points, and the quoted evidence for findings newly added at that
  step (from `step["findings"]["evidence"]`, filtered to that step's `new_findings`).
- **First-HIGH banner:** once `first_flag()` finds a step, a highlighted banner above the
  timeline: flagged date + months before the diagnosis-date input (`months_between`), plus
  that step's reasons list, Gold Coast flag, and advice text (all already in the step dict —
  no recomputation).
- **No mimic hardcoding:** demo step 5 ("load the carpal-tunnel mimic note") is just picking
  a different sidebar entry once `data/mimics/` exists; app.py doesn't special-case it.
- Caching: `st.cache_data` on the `run_timeline` call keyed by (dir, offline, mtime of the
  dir) so switching the diagnosis-date input doesn't re-run extraction (Gemini calls cost
  quota/time) — the existing `.cache/extract/` already caches per-note Gemini results, this
  is an additional UI-level cache to avoid rebuilding the whole timeline on every rerun.

## Open decisions (deciding now)
1. **Default dataset = `data/alex`**, default mode = offline (matches `evaluate.py`'s
   reasoning: same UI behavior for anyone without a key; a sidebar toggle switches to Gemini).
2. **No file upload / paste-a-note box** — docs/PRD.md lists that under "Nice to have," not
   "Must have." Skipping it; the picker only sees existing `data/*/` folders. Add later if
   there's time.
3. **No persistence/session state beyond Streamlit's own rerun model** — nothing to save
   across sessions for a 3-minute judging demo.

## Acceptance check
- `python -m pytest -q` → 6 passed (unchanged).
- `ruff check --select E9,F .` → clean (unchanged).
- `streamlit run app.py --server.headless true &` then curl the health endpoint within 20s
  → process starts without a traceback, health check answers.
- Manual: load `data/alex` offline, confirm 6 notes render, first-HIGH banner shows
  2026-02-10 / 5.1 months (matches `evaluate.py --offline`'s number exactly).
