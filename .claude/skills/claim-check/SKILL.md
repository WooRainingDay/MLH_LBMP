---
name: claim-check
description: Verify every claim the team will show judges (README, Devpost, slides, UI text, pitch script) with two independent reviewers before it ships. Use before publishing the README or Devpost, before making slides, or whenever a number, clinical statement or comparison is added to user-facing text.
---

# Claim check

Judges at BioHacks include clinicians. One wrong number or overclaim costs more than a missing feature. Adapted from ECC `santa-method` (MIT): two reviewers, same rubric, no shared context, both must pass.

## 1. Extract the claims

From the target text, list every claim as a row: the exact sentence, its type (number / clinical fact / comparison / capability / limitation) and the **source** it relies on. Valid sources only:

- a command in this repo plus its output (e.g. `python evaluate.py`), pasted verbatim;
- a page of the BioHacks case file (Alex's notes, pp. 7-15; rubric p. 20);
- a published source with a PMID or DOI that you actually opened.

A claim with no valid source is a FAIL. Do not invent a source.

## 2. Two independent reviewers

Spawn two subagents in parallel with the prompt below, the same rubric and the same inputs (target text + claim table + source outputs). Neither sees the other's review. Each returns JSON: `{"verdict": "PASS|FAIL", "checks": [{"criterion", "result", "detail"}], "critical_issues": [], "suggestions": []}`.

Prompt opening: "You are an independent reviewer. You have not seen any other review. Your job is to find problems, not to approve."

## 3. Rubric (objective pass/fail only)

| Criterion | Pass condition |
|---|---|
| Numbers reproduce | Every number matches a pasted command output or a cited case-file page exactly. In particular, no "19 months" unless `evaluate.py` printed it. |
| No diagnosis claim | The tool "flags for urgent neurology referral" or "supports a referral decision". It never "detects", "diagnoses" or "predicts" ALS. |
| Limits stated | n=1 fictional case; test notes invented by the team; offline vs Gemini results distinguished; no validation on real patients. |
| No unmeasured accuracy | No sensitivity, specificity, accuracy or AUC unless measured on a stated dataset. |
| Comparisons are fair | Claims about ReferALS or current practice match what that tool or the case file actually says. |
| Clinical facts correct | Gold Coast criteria, UMN/LMN signs, NfL figures and timelines match the case file or a cited source. |
| Privacy framed right | Says the data is fictional. If real-world use is mentioned, notes that PHI handling and Health Canada clearance would be needed. |

## 4. Verdict and fixes

- Both PASS: ship.
- Otherwise merge both reviewers' critical issues, fix **only** those, and re-run with **fresh** reviewers. Max 3 rounds, then stop and show the user the remaining issues.
- If only one reviewer flags an issue, treat it as real.

Output: the final claim table (claim | source | PASS/FAIL) plus the corrected text.
