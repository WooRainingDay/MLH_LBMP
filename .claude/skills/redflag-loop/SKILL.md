---
name: redflag-loop
description: Build-and-review loop for ALS RedFlag tasks. Use when the user says "loop", "keep going", "work through TASKS.md", or asks Claude to implement a task and keep fixing and reviewing it until it passes. Runs plan, build and an independent judge against a fixed, machine-checkable acceptance check, with a 3-round retry cap and two human gates.
---

# RedFlag loop

A loop is only safe when a machine can decide "done" and the agent cannot game that decision. Adapted from ECC `loop-design-check` and `santa-method` (MIT).

## 0. Gate before starting (ask everything now, not mid-loop)

1. Pick the task: one row in `docs/TASKS.md` (status TODO), or the one the user names.
2. Write its **acceptance check**: one or more commands that print a clear PASS/FAIL. If the task cannot have one (pitch wording, design taste, clinical judgment), **do not loop**: do it once and hand it to the user.
3. List every open question for the user now. The loop will not stop to ask later; anything unclear is left for the user, not guessed.
4. Show the task, acceptance check and plan (`docs/plans/<task>.md`). **Wait for approval (Gate 1).**

## Acceptance check (default judge for this repo)

All must pass. The judge runs these itself; it never trusts the builder's report.

- `python -m pytest -q` exits 0.
- `ruff check --select E9,F .` exits 0.
- If `evaluate.py` exists: `python evaluate.py` exits 0 and its numbers match the stored baseline (Alex's first HIGH date; every mimic note LOW). If a number changes, that is a FAIL to report, not a baseline to overwrite.
- If the task touches `app.py`: the app starts headless (`streamlit run app.py --server.headless true`) and the health URL answers within 20 s (check the current Streamlit docs for the health path).
- Plus the task-specific check written at Gate 1.

## Boundaries (the loop must NOT)

- Delete, skip or weaken a test or an assertion. Changing what "correct" means is the user's call.
- Tune `rules.json` weights or the Gemini prompt to make Alex flag earlier. Alex is n=1 and the only real case; tuning on him inflates the result.
- Edit shared files (`schema.py`, `extract.py`, `score.py`, `timeline.py`, `rules.json`, `docs/interfaces.md`) without asking.
- Overwrite the evaluation baseline, add dependencies, read or edit `.env`, push to `main`, or force push.
- Put a number in README, UI, Devpost or slides that `evaluate.py` did not print.

## The loop

1. **Build**: implement the smallest slice that can pass. Commit on the feature branch.
2. **Judge** (independent): spawn a fresh `merge-reviewer` subagent on `git diff main...HEAD`. It also runs the acceptance commands itself. Builder and judge are never the same context.
3. **FAIL**: pass the exact failing output back. Fix **only** what was flagged; no refactors. Re-judge with a **fresh** subagent (no memory of the last round).
4. **Retry cap**: 3 rounds. If the same approach fails twice, stop early. Then stop and report: what was tried, the exact failure, and options. Do not try a 4th time.
5. **PASS**: set the task row in `docs/TASKS.md` to REVIEW and show the diff summary plus acceptance output. **The user flips it to MERGED (Gate 2).** The loop never merges.
6. Continue to the next task only if the user asked to work through a list. After each task, if context is getting long, run the `handoff` skill.

## Report format

```
TASK: <row #, name>          ROUND: <n>/3
ACCEPTANCE:
  pytest        PASS/FAIL  (<n> passed)
  ruff E9,F     PASS/FAIL
  evaluate.py   PASS/FAIL  (Alex first HIGH: <date>, <months> before dx; mimics LOW: <k>/<n>)
  app health    PASS/FAIL/N.A.
  task check    PASS/FAIL  (<command>)
JUDGE VERDICT: MERGE | FIX FIRST | BLOCK
NEXT: <what happens now, or what the user must decide>
```
