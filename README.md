# ALS RedFlag

Alex Chen waited just over two years for an ALS diagnosis. A hand surgeon operated for carpal tunnel syndrome in January 2025; three months later he reported no improvement. A physiotherapist and his GP both later suspected a neurological cause; his GP sent an urgent referral to neurology, but it still took five more months to reach a diagnosis.

ALS RedFlag reads referral letters, consult notes and physio summaries. It pulls out the key findings with Gemini (or an offline keyword fallback when there is no API key) and checks them against the ALS red-flag pattern: painless weakness, muscle wasting, twitching, brisk reflexes, normal sensation, spread to another limb, and no response to treatment. When the pattern appears, it recommends an urgent neurology referral and explains why.

Run on Alex's own notes in order: the offline keyword extractor first flags him HIGH risk on **2026-02-10, 5.1 months before his diagnosis**; with Gemini's fuller extraction, the first HIGH flag moves earlier, to **2024-12-09, 19.1 months before diagnosis**. Both numbers are reproducible — `python evaluate.py --offline` and `python evaluate.py` (with a Gemini API key in `.env`) respectively.

**This tool supports clinical decisions. It does not diagnose.** Alex Chen is a fictional case written for BioHacks 2026; every note in `data/` is team-authored test data, not drawn from a real patient or EHR. This is a single case (n=1) — the tool has not been validated against a real patient population.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env
# then paste your Gemini API key into .env

python timeline.py data/sample --offline --diagnosis=2025-03-18   # no key needed
python timeline.py data/alex --diagnosis=2026-07-14               # uses Gemini if a key is set
python evaluate.py --offline                                      # Alex + mimic numbers, deterministic
python score.py data/sample/2024-12-03_gp.txt                     # score one note
python -m pytest -q
```

| File | What it does |
| --- | --- |
| `schema.py` | The findings format: each red flag is true / false / null, plus weakness regions and evidence quotes |
| `extract.py` | `extract_findings()`: Gemini turns a note into findings (structured output, cached in `.cache/`); keyword fallback when there is no key |
| `score.py` | `combine()` merges a patient's notes; `score()` applies `rules.json` and the Gold Coast pattern |
| `rules.json` | Weights, thresholds and recommendation wording, editable without code |
| `timeline.py` | Runs a patient's notes in date order and reports the first date flagged |
| `evaluate.py` | Prints the Alex timeline number and mimic-case scores — the only numbers allowed in judge-facing material |

Interfaces for the app are in [docs/interfaces.md](docs/interfaces.md).

## Team
BioHacks 2026, McMaster University, Detection and Diagnostics track.
