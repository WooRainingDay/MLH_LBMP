---
name: demo-check
description: Report-only check that the demo path works end to end before a merge or before judging. Runs build, lint, typecheck and the demo script, then reports PASS/FAIL per demo step. Use when the user asks for a demo check, pre-merge check, or "is the demo working".
---

# Demo check (report only)

**Do not change any code or files in this skill.** Only run commands and report.

1. Read `CLAUDE.md` → "Stack and commands". Run each of build, lint, typecheck and test that is defined (skip ones marked n/a). Record the exit code and the first relevant error lines.
2. If `e2e/demo.spec.*` exists, run it (`npx playwright test e2e/demo.spec.* --trace off`).
3. Read `docs/DEMO.md` and walk through **every step**. Run the action where it can be run from the terminal (CLI command, script, HTTP request, or a Playwright/browser check of the page). If a step can only be done by a person, mark it MANUAL and say what to check.
4. Output one table:

   | Step | Expected | Actual | PASS/FAIL |
   |---|---|---|---|

5. For every FAIL, give the likely cause as `file:line` and one sentence on why. If you are not sure, say so instead of guessing.
6. End with a one-line verdict: **DEMO READY** or **NOT READY (n failing steps)**.
