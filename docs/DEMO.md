# Demo script

Target length: **3 minutes** at the judging table (Sun 1:30–3:00 PM, MCCD 7110/7120). Judges come to us; expect them to ask "how do you know it works?" and "how is this different from ReferALS?".

## URLs

| | URL |
|---|---|
| Live | <prod URL> |
| Backup (local) | `streamlit run app.py` → http://localhost:8501 |
| Backup (no network, no key) | `python timeline.py data/alex --offline --diagnosis=2026-07-14` |
| Devpost | https://biohacksmcmaster.devpost.com |

## Script

| Step | Action | Expected result |
|---|---|---|
| 0 | Opening line: "Alex waited 25 months. Four clinicians each saw part of the pattern." | Problem slide on screen |
| 1 | Open the app, select patient **Alex Chen** (notes in `data/alex/`) | Six notes listed in date order, Oct 2024 → Jun 2026 |
| 2 | Step through the timeline note by note | Each note shows the findings it added (e.g. wasting, twitching, brisk reflexes) with the quoted sentence from the note |
| 3 | Stop at the first **HIGH** risk note | Banner: first flagged date, and "<N> months before diagnosis". N must come from `evaluate.py`, not from memory |
| 4 | Open the reasons panel for that note | Points breakdown, Gold Coast status, and advice: urgent neurology referral, request EMG, consider serum NfL |
| 5 | Load the carpal-tunnel mimic note | Risk **LOW**: numbness/tingling and positive Phalen's point away from ALS |
| 6 | Close: limits and next step | n=1 fictional case; invented test notes; next: retrospective validation on real referral letters |

## Seeded data and reset

- Patient notes: `data/alex/*.txt` (typed from the case file), `data/sample/*.txt` (invented patient for tests).
- Gemini results are cached in `.cache/extract/`. To force a fresh run: `rm -rf .cache/extract`.
- Before judging: run the demo once with the key set so every note is cached; then the demo works even if the network or quota fails.
- Reset UI state: restart Streamlit (`Ctrl+C`, then `streamlit run app.py`).
