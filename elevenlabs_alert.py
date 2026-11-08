"""Spoken urgent-referral alert ("the call that never came") - plays when the
timeline reaches its first HIGH-risk note. Not part of ALS RedFlag's clinical
scoring; the spoken text only repeats numbers app.py already computed and
verified via evaluate.py, nothing new is claimed out loud.

    from elevenlabs_alert import generate_alert
    audio_bytes = generate_alert(date="2026-02-10", months=5.1)  # None if no API key
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CACHE_DIR = Path(__file__).parent / ".cache" / "elevenlabs"
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MODEL_ID = "eleven_multilingual_v2"


def _api_key() -> str | None:
    return os.getenv("ELEVENLABS_API_KEY")


def _alert_text(date: str, months: float | None) -> str:
    months_clause = f" That is {months} months before the eventual diagnosis." if months is not None else ""
    return (
        "Urgent neurology referral advised. "
        f"Pattern consistent with Gold Coast criteria, first flagged {date}.{months_clause}"
    )


def generate_alert(date: str, months: float | None) -> bytes | None:
    """Returns mp3 bytes, or None if ELEVENLABS_API_KEY is unset (caller falls back
    to silence - same posture as extract.py's offline mode when GEMINI_API_KEY is unset)."""
    api_key = _api_key()
    if not api_key:
        return None

    text = _alert_text(date, months)
    cache_key = hashlib.sha256(text.encode()).hexdigest()[:16]
    cache_path = CACHE_DIR / f"{cache_key}.mp3"
    if cache_path.exists():
        return cache_path.read_bytes()

    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        output_format="mp3_44100_128",
    )
    audio_bytes = b"".join(audio)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(audio_bytes)
    return audio_bytes


def demo() -> None:
    assert "urgent" in _alert_text("2026-02-10", 5.1).lower()
    assert "That is 5.1 months" in _alert_text("2026-02-10", 5.1)
    assert "before the eventual diagnosis" not in _alert_text("2026-02-10", None)

    if not _api_key():
        assert generate_alert("2026-02-10", 5.1) is None

    print("elevenlabs_alert.py: all checks passed")


if __name__ == "__main__":
    demo()
