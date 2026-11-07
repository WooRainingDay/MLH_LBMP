---
name: handoff
description: Write a session handoff note before clearing context, so the next session can continue without re-discovering anything. Use when the user says handoff, wrap up, save progress, or before /clear.
---

# Handoff

1. Get the timestamp and branch: `date +%Y-%m-%d-%H%M` and `git branch --show-current` (replace `/` in the branch name with `-`).
2. Write `.claude/sessions/<YYYY-MM-DD-HHMM>-<branch>.md` with exactly these sections:

   ```markdown
   # Handoff: <branch>, <date time>

   ## Goal
   What this session was trying to achieve, and the demo step it serves.

   ## Done (with evidence)
   - Item: evidence (command + result, commit hash, screenshot path)

   ## Tried and failed
   - Approach: what happened (error message, symptom). Why it failed if known.

   ## Not tried yet / next steps
   1. Ordered, concrete next actions.

   ## Gotchas
   - Anything surprising: env quirks, flaky commands, files that must not be touched.

   ## Files touched
   - path: one-line summary of the change
   ```

   Only list evidence you actually saw this session. Do not invent results.
3. Update this branch's row in `docs/TASKS.md` (status and notes).
4. Show the handoff file to the user.
5. Tell them: run `/clear`, then start the next session with:
   `Read .claude/sessions/<file>.md and continue from next steps`
