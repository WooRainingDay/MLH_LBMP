---
name: feature
description: Phased workflow for building one hackathon feature end to end (research, plan, implement, review, verify). Use when the user asks to build, add or implement a feature, screen, endpoint or integration.
---

# Feature workflow

Work through the phases in order. Do not skip phase 2's approval stop.

## 1. Research

- Launch an **Explore** subagent. Give it the PURPOSE (what the feature is for and which demo step it serves), not only file names.
- At most **3 follow-up rounds** with it. If it still has not found what you need, say what is missing and move on.
- For any third-party API or library, fetch **current docs** before planning: context7 (`resolve-library-id` then `query-docs`), or the vendor's `/llms.txt`. Do not write API code from memory.

## 2. Plan, then STOP

Write `docs/plans/<feature>.md` with:

- **Goal**: one sentence, tied to a numbered step in `docs/DEMO.md`. If it serves no demo step, ask whether it belongs in this hackathon.
- **Files to touch**: prefer NEW files over editing shared ones. Mark any file from the "Shared files" list in `CLAUDE.md`.
- **Steps**: ordered, each small enough for one commit.
- **Acceptance check**: the exact command or click path that proves it works.
- **Out of scope**: what you will not do.

Show the plan and **stop. Wait for the user to approve** before writing code.

## 3. Implement

- Work on a feature branch (`feat/<name>`); never commit to `main`. Use `scripts/new-worktree.sh <name>` if another session is working in the main checkout.
- Small conventional commits (`feat:`, `fix:`, `chore:`, `docs:`).
- No new dependencies without asking. Keep each file under ~300 lines.
- New env vars go in `.env.example`, never hardcoded.

## 4. Review

Run the **merge-reviewer** subagent on `git diff main...HEAD`. Fix every FIX FIRST / BLOCK issue before moving on.

## 5. Verify

- Prove it works with evidence: command output, test result, or a screenshot. "Should work" is not evidence.
- If the **same approach fails twice**, stop and report what you tried and what you saw. Do not try it a third time.
- Update this branch's row in `docs/TASKS.md` (status, notes).
