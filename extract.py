"""Turn one clinical note into a findings dict (see schema.py).

    from extract import extract_findings
    f = extract_findings(note_text)                # Gemini if GEMINI_API_KEY is set, else keywords
    f = extract_findings(note_text, offline=True)  # keywords only, no API call

Gemini results are cached in .cache/ by note text + model, so re-running the
timeline or the evaluation does not spend quota twice.

CLI:  python extract.py data/alex/2024-10-14_gp.txt [--offline]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from schema import FLAGS, Findings

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# gemini-3.5-flash: ~2 s per note. gemini-3.8-flash gave the same findings but took ~3 min per note.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
THINKING = os.getenv("GEMINI_THINKING", "low")  # "" to use the model default
MIN_SECONDS_BETWEEN_CALLS = float(os.getenv("GEMINI_MIN_INTERVAL", "7"))  # free tier
CACHE_DIR = Path(__file__).parent / ".cache" / "extract"
_last_call = 0.0
_gemini_down = False   # set after a failed call; the rest of the run uses keywords
last_extractor = None  # "gemini" or "keywords": what produced the most recent findings


class QuotaExhausted(RuntimeError):
    pass


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def has_gemini() -> bool:
    return _api_key() is not None


PROMPT = """You are helping a family doctor spot early ALS (amyotrophic lateral sclerosis).
Read the clinical note below and fill in the findings.

Rules:
- true = the note says it is present. false = the note says it was checked and is absent
  (e.g. "sensation intact" -> sensory_symptoms false; "no pain" -> painless true).
  null = the note does not say. Never guess; use only what is written.
- weakness_regions: each place with muscle weakness, short and with side if given,
  e.g. "right hand", "left foot", "speech". Empty list if none.
- date: date of the note as YYYY-MM-DD if stated, else null.
- source: who wrote it, e.g. "GP referral", "physiotherapy", "nerve conduction study".
- evidence: for every finding that is true or false, one short exact quote (under 25 words).

Findings:
{flags}

Clinical note:
\"\"\"
{note}
\"\"\"
"""


def _prompt(note: str) -> str:
    return PROMPT.format(flags="\n".join(f"- {k}: {v}" for k, v in FLAGS.items()), note=note.strip())


def _cache_path(note: str) -> Path:
    h = hashlib.sha256(f"{MODEL}\n{_prompt(note)}".encode()).hexdigest()[:24]
    return CACHE_DIR / f"{h}.json"


def extract_gemini(note: str, retries: int = 4) -> dict:
    global _last_call
    cache = _cache_path(note)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_api_key())
    config = types.GenerateContentConfig(
        response_mime_type="application/json", response_schema=Findings, temperature=0,
        thinking_config=types.ThinkingConfig(thinking_level=THINKING) if THINKING else None)
    delay = 10.0
    for attempt in range(retries + 1):
        wait = MIN_SECONDS_BETWEEN_CALLS - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            _last_call = time.time()
            resp = client.models.generate_content(model=MODEL, contents=_prompt(note), config=config)
            parsed = resp.parsed if isinstance(resp.parsed, Findings) else Findings.model_validate_json(resp.text)
            break
        except Exception as e:  # rate limit / server hiccup -> back off and retry
            msg = str(e)
            if "PerDay" in msg or "per day" in msg:   # daily quota gone: retrying for hours won't help
                raise QuotaExhausted(msg[:300]) from e
            transient = any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE", "deadline"))
            if attempt == retries or not transient:
                raise
            print(f"[extract] Gemini error ({msg[:80]}), retrying in {delay:.0f}s", file=sys.stderr)
            time.sleep(delay)
            delay *= 2

    out = parsed.model_dump()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Offline keyword extractor: rough, but needs no API key. For UI work, tests,
# and as a fallback when the Gemini quota runs out.
# ---------------------------------------------------------------------------

_KEYWORDS: dict[str, list[str]] = {
    "sensory_symptoms": [r"numb", r"tingl", r"pins and needles", r"paraesthes|paresthes",
                         r"(reduced|decreased|diminished|loss of) sensation", r"sensory (loss|symptoms|change)"],
    "wasting": [r"wast(ing|ed)", r"atroph", r"flatter|flattening", r"thin(ning)? (of )?(the )?(muscle|hand|calf|calves|thenar)"],
    "fasciculations": [r"fascicul", r"twitch"],
    "cramps": [r"cramp"],
    "brisk_reflexes": [r"brisk", r"hyperreflex", r"(increased|exaggerated|hyperactive) reflex", r"clonus", r"spastic"],
    "upgoing_plantar_or_hoffmann": [r"hoffmann", r"babinski", r"(up-?going|extensor) plantar"],
    "failed_local_treatment": [r"no (improvement|benefit|change) (after|following|with|from|since)",
                               r"did(n't| not) (help|improve)", r"despite (the )?(surgery|release|physio|treatment|injection|splint)",
                               r"not improved", r"(has not|hasn't) improved", r"failed to (help|improve)"],
    "weight_loss": [r"weight loss", r"lost \d+ ?(kg|lb|pounds)"],
    "speech_or_swallow_change": [r"slurr", r"dysarthri", r"dysphagi", r"(difficulty|trouble) swallowing",
                                 r"chok(e|ing)", r"tongue (wasting|fascicul|atroph)", r"nasal speech"],
    "breathing_change": [r"short(ness)? of breath", r"dyspn", r"orthopn", r"\bfvc\b", r"breathless"],
}
_SENSORY_NORMAL = [r"sensation (is |was )?(intact|normal|preserved)", r"(normal|intact) sensation",
                   r"sensory (exam(ination)? )?(is |was )?normal"]
_NCS_SENSORY_NORMAL = [r"sensory (nerve )?conduction(s| studies)? (is |are |were )?normal", r"normal sensory (nerve )?(conduction|responses|studies)",
                       r"sensory (responses|potentials|amplitudes) (are |were )?normal",
                       # "median sensory and motor latencies within normal limits", "Sensory studies, median, sural: all normal"
                       r"sensory[^.;]{0,30}(latenc|conduction|amplitude|stud|respons|potential|snap)[^.;]{0,40}(within normal limits|normal)"]
_NCS_SENSORY_ABNORMAL = [r"sensory (nerve )?conduction(s| studies)? (is |are |were )?(abnormal|reduced|slowed|prolonged)",
                         r"sensory[^.;]{0,30}(latenc|conduction|amplitude|respons|potential|snap)[^.;]{0,30}(prolonged|slowed|delayed|reduced|absent|abnormal)",
                         r"(slowing|delay) (across|at) the (carpal tunnel|wrist|elbow)"]
_WEAK = re.compile(r"weak|\bdropp(ing|ed|s)\b|tires? (quickly|easily)|difficulty (gripping|buttoning|doing up|opening)|"
                   r"trouble (gripping|doing up)|grip|foot drop|tripping|catch(es|ing) on|dragg(ing|s)|slurr|"
                   r"[0-4]/5|[0-4] out of 5")
# Treatment aimed at a local cause (wrist, neck, nerve), and a later "it didn't help"
_LOCAL_TREATMENT = re.compile(r"surgery|release|decompression|splint|injection|physio|brace|orthotic", re.I)
_NO_BETTER = [r"no (improvement|benefit|better)", r"not (any )?better", r"(hand|arm|leg|foot|grip|weakness) is (now )?(weaker|worse)",
              r"if anything[^.;]{0,30}(weaker|worse)"]
_PLACE = re.compile(r"\b(?:(left|right)\s+)?(hand|thumb|fingers?|wrist|forearm|arm|shoulder|grip|foot|ankle|leg|thigh|hip|"
                    r"knee|calf|toes?|speech|tongue|swallow\w*|neck)\b")
_NEGATION = re.compile(r"\b(no|not|denies|denied|without|absent|negative for|nil|never|free of)\b[^.;]{0,40}$")
_SENTENCE = re.compile(r"[^.;\n]+[.;\n]?")


def _match(patterns: list[str], sentences: list[str]) -> tuple[bool | None, str]:
    """True if a sentence mentions it, False if only negated mentions, None if never."""
    result, quote = None, ""
    for sent in sentences:
        low = sent.lower()
        for pat in patterns:
            m = re.search(pat, low)
            if not m:
                continue
            negated = bool(_NEGATION.search(low[: m.start()]))
            if not negated:
                return True, sent.strip()[:200]
            if result is None:
                result, quote = False, sent.strip()[:200]
    return result, quote


def _canonical_place(side: str | None, part: str) -> str:
    part = part.lower()
    if part in ("thumb", "finger", "fingers", "wrist", "grip"):
        part = "hand"
    if part in ("toe", "toes", "ankle"):
        part = "foot"
    if part.startswith("swallow") or part == "tongue":
        part = "speech"
    return f"{side} {part}" if side and part not in ("speech", "neck") else part


def extract_offline(note: str) -> dict:
    sentences = [s for s in _SENTENCE.findall(note) if s.strip()]
    f = Findings().model_dump()
    evidence = []

    for field, patterns in _KEYWORDS.items():
        val, quote = _match(patterns, sentences)
        f[field] = val
        if quote:
            evidence.append({"field": field, "quote": quote})

    # Sensation documented as normal -> no sensory symptoms
    normal, q = _match(_SENSORY_NORMAL, sentences)
    if normal and f["sensory_symptoms"] is not True:
        f["sensory_symptoms"] = False
        evidence.append({"field": "sensory_symptoms", "quote": q})

    ok, q1 = _match(_NCS_SENSORY_NORMAL, sentences)
    bad, q2 = _match(_NCS_SENSORY_ABNORMAL, sentences)
    if bad:
        f["normal_sensory_nerve_tests"] = False
        evidence.append({"field": "normal_sensory_nerve_tests", "quote": q2})
    elif ok:
        f["normal_sensory_nerve_tests"] = True
        evidence.append({"field": "normal_sensory_nerve_tests", "quote": q1})

    # "Surgery 20 January 2025 ... He reports no improvement": the two halves are in different sentences
    if f["failed_local_treatment"] is not True and _LOCAL_TREATMENT.search(note):
        worse, q = _match(_NO_BETTER, sentences)
        if worse:
            f["failed_local_treatment"] = True
            evidence.append({"field": "failed_local_treatment", "quote": q})

    # Weakness regions: places named in sentences that describe weakness
    regions: list[str] = []
    for sent in sentences:
        low = sent.lower()
        if _WEAK.search(low) and not _NEGATION.search(low[: _WEAK.search(low).start()]):
            for side, part in _PLACE.findall(low):
                place = _canonical_place(side or None, part)
                if place not in regions:
                    regions.append(place)
    f["weakness_regions"] = regions

    # Painless: weakness + "no pain" / "painless"; pain-dominant -> false
    pain_neg, q = _match([r"\bpain"], sentences)
    if regions:
        if re.search(r"painless", note, re.I) or pain_neg is False:
            f["painless"] = True
            evidence.append({"field": "painless", "quote": q or "painless"})
        elif re.search(r"(severe|significant|constant) pain|painful", note, re.I):
            f["painless"] = False

    m = re.search(r"\b(20\d\d)-(\d\d)-(\d\d)\b", note)
    f["date"] = m.group(0) if m else None
    first_line = note.strip().splitlines()[0] if note.strip() else ""
    f["source"] = re.split(r"[,.:]", first_line)[0].strip()[:60] or None
    f["evidence"] = evidence
    return f


def extract_findings(note_text: str, offline: bool | None = None) -> dict:
    """Main entry point. offline=None: use Gemini if a key is set, else keywords.

    With offline=None a Gemini failure (quota gone, network down) falls back to keywords
    instead of crashing the app; a warning goes to stderr and last_extractor says which ran.
    offline=False forces Gemini and raises on failure.
    """
    global _gemini_down, last_extractor
    auto = offline is None
    if auto:
        offline = not has_gemini() or (_gemini_down and not _cache_path(note_text).exists())
    if offline:
        last_extractor = "keywords"
        return extract_offline(note_text)
    try:
        out = extract_gemini(note_text)
    except Exception as e:
        if not auto:
            raise
        if not _gemini_down:
            print(f"[extract] Gemini unavailable, using keyword fallback for the rest of this run: {str(e)[:150]}",
                  file=sys.stderr)
        _gemini_down = True
        last_extractor = "keywords"
        return extract_offline(note_text)
    last_extractor = "gemini"
    return out


SAMPLE_NOTE = """Referral, 14 October 2024. Mountain Brow Family Health Team.
Re: Right hand weakness and deteriorating handwriting, four months.
Thank you for seeing Alex, a 45-year-old right-handed teacher who is otherwise well. Since June he has
noticed that his handwriting fades across the page and that his right thumb and index finger tire quickly
when writing on a whiteboard. He has started dropping his whiteboard marker and his coffee cup. No pain.
No numbness or tingling. He reports some cramping in the right forearm at night.
On examination the right thenar eminence looks a little flatter than the left. Grip is slightly weaker on the
right. Phalen's test was equivocal. Sensation to light touch was normal in all fingers. I suspect a carpal
tunnel syndrome or a median neuropathy at the wrist."""


if __name__ == "__main__":
    # python extract.py               -> runs on the built-in sample note
    # python extract.py NOTE.txt      -> runs on a note file
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    text = Path(args[0]).read_text(encoding="utf-8") if args else SAMPLE_NOTE
    print(json.dumps(extract_findings(text, offline=True if "--offline" in sys.argv else None), indent=2))
