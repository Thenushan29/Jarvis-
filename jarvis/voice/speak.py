"""Text-to-speech via Edge TTS — bilingual with Iron Man Jarvis preset support.

Thread-safe: a single lock serializes all speak() calls so a reminder firing
in the scheduler thread can't interrupt a reply in the main thread.
"""
import asyncio
import os
import tempfile
import threading
from pathlib import Path

import edge_tts
import pygame

from ..config import TTS_VOICE_TAMIL, TTS_VOICE_ENGLISH
from .presets import ENGLISH_PRESETS, TAMIL_PRESETS, find_preset

_mixer_state: dict = {"inited": False, "ok": False, "error": None}
_speak_lock = threading.Lock()


def _ensure_mixer() -> bool:
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
              "Pick a default audio output in Windows Sound settings.")
        return False


def _preset_for(lang: str) -> dict:
    """Look up the preset by language from settings (with sensible defaults)."""
    is_tamil = (lang or "").lower().startswith("ta")
    presets = TAMIL_PRESETS if is_tamil else ENGLISH_PRESETS
    stored = TTS_VOICE_TAMIL if is_tamil else TTS_VOICE_ENGLISH
    # `stored` can be a preset id (like "jarvis") OR a raw Edge voice (like "en-GB-ThomasNeural").
    # Env overrides (rate/pitch) are also respected.
    preset = dict(find_preset(presets, stored))
    rate_override = os.getenv("TTS_RATE_EN" if not is_tamil else "TTS_RATE_TA", "").strip()
    pitch_override = os.getenv("TTS_PITCH_EN" if not is_tamil else "TTS_PITCH_TA", "").strip()
    if rate_override:
        preset["rate"] = rate_override
    if pitch_override:
        preset["pitch"] = pitch_override
    return preset


async def _synthesize(text: str, voice: str, rate: str, pitch: str, out_path: Path) -> None:
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await comm.save(str(out_path))


def speak(text: str, lang: str = "en") -> None:
    """Speak text aloud in the matching language preset. Blocks until done. Thread-safe."""
    text = (text or "").strip()
    if not text:
        return

    preset = _preset_for(lang)
    with _speak_lock:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = Path(f.name)
        try:
            try:
                asyncio.run(_synthesize(text, preset["voice"], preset["rate"], preset["pitch"], path))
            except Exception as e:
                print(f"[speak] TTS synth failed: {e}")
                return
            if not _ensure_mixer():
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


def preview_voice(preset: dict, sample_text: str = "") -> str | None:
    """Synthesize a short sample with the given preset; return the temp .mp3 path.

    The settings dialog calls this to let the user hear a voice before saving.
    """
    text = sample_text or (
        "Good evening. I am Jarvis, your personal assistant. Standing by."
    )
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        path = Path(f.name)
    try:
        asyncio.run(_synthesize(text, preset["voice"], preset["rate"], preset["pitch"], path))
    except Exception as e:
        print(f"[preview] synth failed: {e}")
        return None
    return str(path)


def play_audio_file(path: str) -> None:
    """Play a file path. Blocks until done. Used by the voice preview button."""
    if not path:
        return
    with _speak_lock:
        if not _ensure_mixer():
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(80)
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"[play_audio_file] {e}")
