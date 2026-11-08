# Plan: "The Call That Never Came" - ElevenLabs audio alert

A spoken urgent-referral alert that plays the moment the timeline reaches the
first HIGH-risk note. Not a gimmick bolt-on: it literalizes the demo's own
opening line ("Alex waited 25 months. Four clinicians each saw part of the
pattern.") - the app now does, out loud, the thing that should have happened
back then.

## Why this and not other ElevenLabs ideas

Considered and rejected:

- **Synthetic "before/after ALS voice" demo** - would require simulating a
  patient's voice changing over time with no real longitudinal recording to
  back it. Dramatization, not evidence; certain to fail claim-check.
- **Conversational voice Q&A over the notes** - large scope, hallucination
  risk for a clinical tool, not enough hours left before judging.
- **Narrate every finding as the timeline is stepped through** - more API
  calls and UI complexity for marginal benefit over the existing text.

The single-alert version is small, ties directly to the pitch's emotional
core, and is the cheapest version that is still genuinely different from a
colored banner.

## API (researched via context7, ElevenLabs Python SDK, 2026-11-07)

```python
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key=api_key)
audio = client.text_to_speech.convert(
    text=alert_text,
    voice_id="JBFqnCBsd6RMkjVDRZzb",  # a calm, clear default voice; swap if needed
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)
audio_bytes = b"".join(audio)  # convert() returns an iterable of chunks
```

`st.audio(audio_bytes, format="audio/mp3", autoplay=True)` plays it without a
user click - Streamlit >=1.40 (already in requirements.txt) supports
`autoplay`.

## Text template (no LLM, no invented content)

Built entirely from numbers `evaluate.py`/`app.py` already computed and
verified - nothing new to claim-check beyond "does this sentence match the
variables":

```python
ALERT_TEMPLATE = (
    "Urgent neurology referral advised. "
    "Pattern consistent with Gold Coast criteria, first flagged {date}."
    "{months_clause}"
)
# months_clause = f" That is {months} months before the eventual diagnosis." if months is not None else ""
```

Matches the exact `flag["date"]` / `months` values already shown in the
`st.error` banner at `app.py:49-52` - the voice says only what the screen
already says, just out loud.

## Files to touch

| File | Change |
|---|---|
| `app.py` ⚠ (Bruce owns it - this plan is that sign-off) | After the existing `st.error(...)` block (line ~49-53): build `ALERT_TEMPLATE` from `flag["date"]`/`months` (already in scope), call a new `elevenlabs_alert.generate_alert(date, months)`, play via `st.audio(..., autoplay=True)` if it returns bytes, skip silently if it returns `None` |
| `elevenlabs_alert.py` (new) | `generate_alert(date: str, months: float \| None) -> bytes \| None`. Returns `None` if `ELEVENLABS_API_KEY` is unset (no crash, same fallback pattern as `extract.py`'s Gemini key check). Caches by `(date, months)` to `.cache/elevenlabs/<hash>.mp3` so repeated demo runs/reruns don't spend API quota |
| `requirements.txt` ⚠ | Add `elevenlabs` (official SDK) |
| `.env.example` ⚠ | Add `ELEVENLABS_API_KEY=` |
| `docs/DEMO.md` | Step 3 (first HIGH flag) gets a line: audio plays automatically; note it needs a network + API key, falls back silently to the existing silent banner if missing |

## Steps

1. `elevenlabs_alert.py`: `generate_alert()` + on-disk cache + graceful
   no-key fallback. Self-check: no key set -> returns `None`, no network
   call attempted (assert via monkeypatching `os.environ` in the demo()
   block, no real API call in the self-check - keeps it runnable without a
   key/quota).
2. Wire into `app.py` right after the existing HIGH-risk banner.
3. Update `docs/DEMO.md` step 3.
4. Run with a real key once to confirm the audio actually plays and the
   cache file lands in `.cache/elevenlabs/`; re-run to confirm the cache hit
   (no second API call - check via a request counter or network log).
5. **claim-check** the exact spoken sentence (same rigor as the Tier B voice
   score) before it's used in front of judges - it's a new judge-facing
   claim surface even though it's built from already-verified numbers.

## Fallback / risk

- No key -> `generate_alert()` returns `None` -> `app.py` shows exactly what
  it shows today, no audio, no error. The feature can be demoed without it
  working, same posture as the Gemini offline mode.
- Free-tier ElevenLabs quota is limited by characters/month - caching by
  `(date, months)` means the demo can be rehearsed repeatedly without
  burning it, since Alex's numbers don't change between reruns.
- Browser autoplay-with-sound can be blocked by the browser until a user
  interacts with the page first; on Vultr's live URL, judges will have
  already clicked around the app before reaching this note, so this is a
  minor risk, not a blocker - confirm in a real browser before judging.

## Out of scope (this plan)

- Voice for mimic notes or any other page.
- Any text not already shown on screen elsewhere in the app.
