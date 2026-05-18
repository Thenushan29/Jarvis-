"""Text-to-speech via Edge TTS (free Microsoft neural voices). Bilingual Tamil/English.

Thread-safe: a single lock serializes all speak() calls so a reminder firing
in the scheduler thread can't interrupt a reply in the main thread.
"""
import asyncio
import tempfile
import threading
from pathlib import Path

import edge_tts
import pygame

from ..config import TTS_VOICE_TAMIL, TTS_VOICE_ENGLISH

_mixer_state: dict = {"inited": False, "ok": False, "error": None}
_speak_lock = threading.Lock()


def _ensure_mixer() -> bool:
    """Init pygame mixer once. Returns True on success."""
    if _mixer_state["inited"]:
        return _mixer_state["ok"]
    _mixer_state["inited"] = True
    try:
        pygame.mixer.init()
        _mixer_state["ok"] = True
        return True
    except Exception as e:
        _mixer_state["error"] = str(e)
        _mixer_state["ok"] = False
        print(f"[speak] WARNING: pygame.mixer.init failed: {e}. "
              "Make sure a default audio output device is selected in Windows Sound settings.")
        return False


def _voice_for(lang: str) -> str:
    # 'ta' = Tamil. Anything else falls back to English.
    return TTS_VOICE_TAMIL if (lang or "").lower().startswith("ta") else TTS_VOICE_ENGLISH


async def _synthesize(text: str, voice: str, out_path: Path) -> None:
    comm = edge_tts.Communicate(text, voice)
    await comm.save(str(out_path))


def speak(text: str, lang: str = "en") -> None:
    """Speak text aloud in the matching language voice. Blocks until done. Thread-safe."""
    text = (text or "").strip()
    if not text:
        return

    voice = _voice_for(lang)
    # Serialize concurrent speak() calls (main thread + reminder thread).
    with _speak_lock:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = Path(f.name)
        try:
            try:
                asyncio.run(_synthesize(text, voice, path))
            except Exception as e:
                print(f"[speak] TTS synth failed: {e}")
                return
            if not _ensure_mixer():
                # Mixer unavailable — just print the text so the user still sees it.
                print(f"[speak:text-only] {text}")
                return
            try:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(80)
                pygame.mixer.music.unload()
            except Exception as e:
                print(f"[speak] playback failed: {e}")
        finally:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
