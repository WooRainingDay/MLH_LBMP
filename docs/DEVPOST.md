**DRAFT — not yet claim-checked. Do not submit to Devpost until the claim-check skill has reviewed this file.**

# ALS RedFlag

BioHacks 2026 (McMaster, 7–8 Nov 2026) — Detection and Diagnostics track.

## The problem

Alex Chen is a 47-year-old high-school biology teacher in Hamilton. His handwriting started fading on the whiteboard in June 2024. Over the next two years his case passed through a family doctor (14 Oct 2024, referred for suspected carpal tunnel), a hand surgeon (consult 9 Dec 2024, surgery 20 Jan 2025, no improvement, forearm "rippling" noted 21 Apr 2025), eighteen sessions of physiotherapy for a worsening foot drop (12 Aug 2025 – 5 Feb 2026, discharge summary flags brisk reflexes and recommends neurology), and back to his family doctor, who sent an urgent neurology referral on 16 Feb 2026. Neurology confirmed ALS, limb onset with early bulbar and respiratory involvement, on 14 July 2026 — about 25 months after his first symptom. (Source: `context/BioHacks-2026-Hacker-Package.pdf`, pp. 7–13; summarised in `docs/PRD.md`.) Each clinician saw part of the pattern — wasting, fasciculations, brisk reflexes, failed local treatment — but no one synthesized it across the full record until February 2026, when the physiotherapist and GP both independently suspected a neurological cause and the GP sent an urgent referral; diagnosis still took five more months after that. Earlier referral means earlier multidisciplinary care, medication, and trial eligibility.

## The solution

ALS RedFlag reads a patient's clinical notes in date order — GP referrals, surgical consults, physiotherapy discharge summaries — and extracts ALS red-flag findings (painless weakness, wasting, fasciculations, brisk reflexes, bulbar or respiratory change, failed local treatment, and more) with the exact quoted sentence as evidence. It scores the accumulated findings against a rule set built from the Gold Coast criteria and ALS Canada's ReferALS red flags (`rules.json`), and reports the first date in the record where the pattern crosses the threshold for an urgent neurology referral. It supports a referral decision. It does not diagnose ALS, and the UI, this write-up and the pitch are worded that way throughout.

## The numbers

Both numbers below are from Alex's six typed notes in `data/alex/` (venv activated, run from the repo root). They are **not interchangeable** — the offline extractor is a deterministic keyword matcher used for grading and demos without a key; the Gemini run uses structured LLM extraction and is the number we believe is closer to what a clinician reading the notes would catch.

**Offline (keyword fallback, deterministic):**

```
$ python evaluate.py --offline
Mode: offline keyword extractor

Alex Chen timeline:
  First HIGH risk: 2026-02-10 (2026-02-10_physio.txt), 5.1 months before diagnosis (2026-07-14)

Mimic cases (must all score low):
  [ok] 2026-01-12_hand_clinic.txt: low
  [ok] 2026-02-03_spine_clinic.txt: low
  [ok] 2026-03-20_neuro_clinic.txt: low
```

**Gemini (structured extraction, `gemini-3.5-flash`):**

```
$ python evaluate.py
Mode: Gemini if GEMINI_API_KEY is set, else offline

Alex Chen timeline:
  First HIGH risk: 2024-12-09 (2024-12-09_surgery.txt), 19.1 months before diagnosis (2026-07-14)

Mimic cases (must all score low):
  [ok] 2026-01-12_hand_clinic.txt: low
  [ok] 2026-02-03_spine_clinic.txt: low
  [ok] 2026-03-20_neuro_clinic.txt: low
```

The offline extractor only catches the pattern at the 10 Feb 2026 physiotherapy discharge summary (explicit wasting + brisk reflexes language). Gemini's extraction catches it earlier, at the 9 Dec 2024 hand-surgery **initial consultation** — not because treatment had already failed (surgery was only scheduled for 20 Jan 2025 as of this note, so "failed local treatment" can't be true yet), but because the rule set's "doesn't fit" logic fires: visible thenar wasting plus normal nerve-conduction studies and no sensory symptoms means carpal tunnel syndrome itself cannot explain the weakness. Verified directly against the scorer's output for that note (`python3 -c "from timeline import run_timeline; steps=run_timeline('data/alex', offline=False); [print(s['reasons']) for s in steps if s['date']=='2024-12-09']"`), which prints `+3 Doesn't fit: weakness and wasting with normal sensory nerve tests, so carpal tunnel or a pinched nerve does not explain it` plus painless weakness, wasting, normal sensory nerves, no numbness/tingling and cramps — 11 points, HIGH. All three mimic (non-ALS) test notes — carpal tunnel, cervical radiculopathy, peripheral neuropathy — score "low" in both modes, shown above.

## Rubric fit

| Criterion (pts) | How we hit it |
|---|---|
| Clinical grounding (20) | Every rule in `rules.json` cites the Gold Coast criteria (Shefner et al. 2020) or ALS Canada's ReferALS tool; every finding for Alex traces to a quoted sentence from his actual case notes, pp. 7–13 |
| Diagnostic value (30) | Clear, narrow claim: flags the pattern for urgent neurology referral, not a diagnosis. The comparison that matters is against what actually happened in the case, not against our own offline number: Alex's GP sent an urgent referral ~20 months after his first symptom (16 Feb 2026, case file pp. 7–8), and our offline extractor lands close to that same point (5.1 months before diagnosis). Gemini's extraction flags the pattern ~14 months earlier than that real referral, at the first surgical consult (9 Dec 2024) — that gap against the real timeline, not the offline-vs-Gemini gap, is the genuine advantage this tool offers |
| Evidence and testing (20) | Reproducible: `python evaluate.py [--offline]` on real repo data, offline and Gemini numbers shown separately, limits stated below; 3 mimic cases (carpal tunnel, cervical radiculopathy, peripheral neuropathy) all score low in both modes |
| Feasibility (15) | Reads notes a GP already has; no new hardware, lab work, or EHR integration; runs offline with no API key; cost is one Gemini call per note, rate-limited for the free tier (`GEMINI_MIN_INTERVAL`); framed throughout as decision support, not a regulated diagnostic device |
| Communication (15) | 60-second pitch below; demo (`docs/DEMO.md`) runs fully offline as a backup; every number here traces to a command, not memory |

## Limits

- **n = 1.** Alex Chen is a fictional case written for this hackathon (`context/BioHacks-2026-Hacker-Package.pdf`). No real patient has been run through this tool.
- Alex's six notes (`data/alex/`) and the three mimic/non-ALS test notes (`data/mimics/`) are all typed by the team, not drawn from real patients.
- No sensitivity, specificity, accuracy, or AUC numbers exist for this tool on any dataset. The two numbers above are a single-case timeline, not a performance metric.
- Offline and Gemini give different answers (5.1 vs. 19.1 months before diagnosis) because they use different extraction methods; neither should be quoted without saying which one it is.
- This tool has not been validated against real referral letters or a real clinician's chart review, and is not a diagnostic or regulated medical device. It is a decision-support prototype.
- Real-world or real-patient use would require PHI-compliant data handling and likely Health Canada clearance as a medical device; this prototype has neither and was never run on real patient data.

## 60-second pitch script

> Alex Chen is a 47-year-old teacher. His handwriting started fading in June 2024. Over two years his hand surgeon raised a neurological opinion, his physiotherapist said it wasn't an ankle problem, and his GP sent an urgent neurology referral by February 2026 — twenty months after that first symptom. Diagnosis took five more months.
>
> ALS RedFlag reads a patient's notes in date order, pulls out red-flag findings — wasting, fasciculations, brisk reflexes, failed treatment — with the quoted sentence as evidence, and scores them against the Gold Coast criteria. It doesn't diagnose; it flags an urgent neurology referral, now.
>
> On Alex's notes, Gemini flags that pattern at his first surgical consult, December 2024 — fourteen months before the real referral went out. Our offline extractor catches it later, close to where the real referral landed.
>
> One fictional case. But the failure is real: clinicians raised concern more than once before anyone acted. ALS RedFlag surfaces it the first time it appears.

(161 words — timed at conversational pace for ~60 seconds.)
