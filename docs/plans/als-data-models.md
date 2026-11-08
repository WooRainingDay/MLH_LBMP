# Plan: Ground the Part 2 biomarkers in real ALS data

Replace the hand-picked `ponytail:` thresholds in `motor_cv.py` and
`motor_face_audio.py` with models and cutoffs learned and validated on public
ALS datasets, and show judges where every number comes from.

**This does not make the app diagnose ALS.** Output stays a decision-support
signal, labelled with how much evidence backs it (see "Confidence tiers").

## Goal

Strengthens `docs/DEMO.md` step 6 and answers the judge question "how do you
know it works?" with numbers from a command, not from memory:
*each Part 2 reading shows a calibrated score plus the dataset, n, and
cross-validated AUC it came from.*

## Data sources

Access details below came from a web search on 2026-11-08. Confirm each one
before planning work around it.

| Dataset | What it gives us | Used for | Access |
|---|---|---|---|
| **VOC-ALS** (Synapse, Sci Data 2024) | 1,224 recordings: sustained vowels /a e i o u/ + /pa ta ka/; 102 ALS + 51 matched controls; ALSFRS-R speech score, dysarthria severity | Voice model: train + cross-validate | Free Synapse account + terms. **User action** |
| **TORGO** | Dysarthric speech from ALS and cerebral palsy speakers + controls | Voice: external test set only (different etiology mix and mic) | Public download (confirm licence) |
| **Toronto NeuroFace** | 261 facial videos, 11 ALS / 14 stroke / 11 controls, 68 manually labelled landmarks, clinical scores; tasks incl. pa-ta-ka, lip spread | Lip-velocity cutoffs (descriptive only, n too small to train) | Data request (confirm process) |
| **Answer ALS** | >1,000 ALS patients; smartphone speech + finger tracing for ~80 | Finger-motor reference values; extra ALS speech | Portal registration + data use terms (confirm) |
| **Gait in Neurodegenerative Disease** (PhysioNet) | Stride-interval series: 13 ALS, 15 PD, 20 HD, 16 controls | Validates the rhythm-variability *method* (jitter, slope) on real ALS motor data, though not on fingers | Open download |
| **DNE-113** | Smartphone videos of finger tapping etc., 113 participants, mixed neuro conditions | Finger-tap CV pipeline check (pose → tap timing) | Unknown: confirm the data is released |
| Gold Coast real-world study (PMC11592046) + Gold Coast criteria paper | Criteria text, real-world sens/spec | RAG source for the advice/explanation text | Open access |

Not usable (checked): ALS Focus, DREAM/PRO-ACT progression data, bigP3BCI,
EEGET-ALS, Seattle profile. They hold survey, progression, EEG or interview
data, with no voice, face or motion signal to train on. EHR studies (AUC
≈0.95) use private data. Cite them in the pitch only.

## Confidence tiers (shown in the UI)

| Tier | Signal | Evidence |
|---|---|---|
| A | Clinical notes → Gold Coast / ReferALS rules (`rules.json`) | Published clinical criteria. Unchanged |
| B | Voice model | Trained and cross-validated on VOC-ALS (n=153), external check on TORGO |
| C | Lip velocity, finger tap | Cutoffs from small datasets (NeuroFace n=22, Answer ALS, Gait). Descriptive only |

The tiers are never merged into a single "AI confidence %".

## Files to touch

Prefer new files. **Shared files** (owner OK needed, per `CLAUDE.md`) are marked ⚠.

| File | New/Edit | Purpose |
|---|---|---|
| `research/fetch_data.py` | New | Download each dataset into `data/external/<name>/` (VOC-ALS via `synapseclient` + `SYNAPSE_AUTH_TOKEN`). Idempotent, prints file counts |
| `research/voice_features.py` | New | One feature row per recording: F0 mean/SD (the best single ALS feature in the VOC-ALS paper), jitter, shimmer, HNR, F1–F3 mean/SD, MFCC stats |
| `research/train_voice.py` | New | Baseline: logistic regression + random forest on the features. **Subject-level** stratified k-fold. Prints AUC, sensitivity, specificity with 95% CI. Saves `models/voice_baseline.joblib` |
| `research/train_voice_ssl.py` | New | wav2vec2 / HuBERT embeddings (frozen first, then fine-tune the top layers) + classifier, same CV protocol, compared against the baseline |
| `research/calibrate_face.py`, `research/calibrate_motor.py` | New | Run the existing `lip_velocity` / `tap_rhythm` logic on NeuroFace, Answer ALS and Gait data. Print per-group distributions and the cutoffs chosen |
| `research/report.py` | New | One command that prints every number the README, Devpost or UI shows (like `evaluate.py`) |
| `motor_face_audio.py` | Edit | Add `f0_sd` to the voice output. Load the trained voice model if present and fall back to the current heuristic if not |
| `motor_cv.py` | Edit | Replace the `ponytail:` cutoffs with values from `calibrate_motor.py`, citing the source in a comment |
| `pages/3_*`, `pages/4_*` | Edit | Show the calibrated score, tier label and provenance line ("VOC-ALS n=153, CV AUC X ± Y") |
| `.gitignore` | Edit | `data/external/`, `models/*.pt` (licensed data and large weights are never committed) |
| ⚠ `requirements.txt` | Edit | `scikit-learn`, `joblib`, `synapseclient`, `praat-parselmouth` (standard jitter/shimmer/HNR). Optional group: `torch`, `transformers` for the SSL step |
| ⚠ `.env.example` | Edit | `SYNAPSE_AUTH_TOKEN=` |
| `docs/DEMO.md`, `docs/TASKS.md`, `README.md` | Edit | New numbers, only after **claim-check** |

## Steps

Each step is one commit on `feat/data-models`.

0. **Data access (user).** Create the Synapse account, accept the VOC-ALS
   terms and put the token in `.env`. Request NeuroFace and Answer ALS access.
   Steps 1–3 need only VOC-ALS, so they can start before the rest arrives.
1. **Fetch + features.** `fetch_data.py` (VOC-ALS, TORGO, Gait first) and
   `voice_features.py`. Add `f0_sd` to `motor_face_audio.py`.
2. **Voice baseline.** `train_voice.py`. Check: does F0 SD alone reproduce the
   paper's finding? This guards against bugs in our own pipeline.
3. **Voice external check.** DONE - `research/score_torgo.py`. TORGO (8092
   recordings, 8 dysarthric + 7 control speakers, all 4 archives): AUC 0.544,
   down from VOC-ALS's CV AUC 0.64. A large drop, confirming real domain shift
   (different mic, mixed ALS/CP etiology). Stated in the UI's Tier B caveat
   and `docs/DEMO.md`, not hidden.
4. **Voice SSL.** Skipped for this hackathon: the baseline's TORGO AUC (0.544)
   is near chance, so there is no credible "beats TORGO" bar for an SSL model
   to clear yet, and torch/transformers are heavy for the remaining time
   budget. Revisit once more labelled data (TORGO per-speaker etiology,
   Answer ALS) narrows what "better" would mean.
5. **Face + motor calibration.** `calibrate_face.py` (NeuroFace) and
   `calibrate_motor.py` (Gait now, Answer ALS / DNE-113 when access arrives).
   Replace the `ponytail:` cutoffs.
6. **UI integration.** Tier labels and provenance lines on pages 3–4. Load the
   model at startup and fall back cleanly if it is missing, so the demo never
   depends on the training data being present.
7. **Optional RAG for advice text.** Retrieve Gold Coast criteria passages and
   quote them in the reasons panel. Scoring stays in `rules.json` and does not
   change. Do this step only if time remains.
8. **Report + claim-check.** `report.py`, then the **claim-check** skill on
   every number before it reaches the README, Devpost or slides.

## Method rules (non-negotiable)

- **Split by subject, never by recording.** VOC-ALS has 8 recordings per
  person. A recording-level split leaks the speaker into the test set and
  inflates accuracy. The likely cause of the 98–99% figures seen in some
  papers.
- Report class balance (102 vs 51), use stratified folds and report
  sensitivity and specificity, not only accuracy.
- Choose cutoffs inside the training folds and never tune on the test fold.
  Fix the random seeds.
- Domain shift: VOC-ALS was recorded on a smartphone app, our app uses a
  browser mic. Resample to one rate and note the gap in the UI.
- Small n means wide confidence intervals. Report the CI, not just the point
  estimate.

## Acceptance check

- `python research/fetch_data.py --check` → prints the expected file counts per dataset.
- `python research/train_voice.py` → subject-level CV AUC with a 95% CI. F0 SD alone has AUC clearly above 0.5.
- `python research/report.py` → every number shown in the UI and README, reproducible.
- `python -m pytest -q` passes and `ruff check --select E9,F .` is clean.
- With `data/external/` and `models/` deleted, pages 3–4 still load and fall back to the heuristic.
- The claim-check skill passes on the README and Devpost text.

## Out of scope

- Fine-tuning Gemini: no labelled clinical-note corpus exists. We have 9 fictional notes.
- RAG for the risk score itself: it makes scoring less deterministic and less reproducible.
- Merging the tiers into one score, or calling any output a "diagnosis".
- Committing or redistributing dataset files or derived weights before the licence allows it.
- New data collection from people: needs ethics approval, outside this project.

## Risks

- **Data access lead time** (Synapse, NeuroFace and Answer ALS approvals) is
  the critical path, not code.
- **Licences:** confirm that trained weights may ship in a public repo or demo.
  If they may not, keep them local and show only the metrics.
- `torch`/`transformers` are heavy for the Vultr box (8 GB RAM). Run the SSL
  model locally or precompute, and serve the baseline model on Vultr.
- PR #12 (live camera) is still open. Merge it first so this branch starts from current `main`.
