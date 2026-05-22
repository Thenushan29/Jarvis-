"""Jarvis entry point with three modes.

Usage:
    python run.py            # default: wake-word mode ("Hey Jarvis")
    python run.py text       # text mode — type commands, no mic needed (BEST FOR TESTING)
    python run.py voice      # press-ENTER-to-talk mode (good for testing mic + STT)
    python run.py wake       # explicit wake-word mode

Pipeline (voice/wake modes):
    activate -> record until silence -> Whisper STT -> Groq brain (with tools) -> Edge TTS
"""
from __future__ import annotations
import sys
import time
import traceback

import numpy as np
import sounddevice as sd

from jarvis.config import assert_keys, FOLLOWUP_SECONDS
from jarvis.voice.listen import (
    listen, record_until_silence, transcribe, SAMPLE_RATE, calibrate_silence,
)
from jarvis.voice.speak import speak
from jarvis.brain import Brain
from jarvis.tools.reminders import ReminderScheduler
from jarvis.conversation_log import log as conv_log


FOLLOWUP_VOICE_RMS = 0.025


def on_reminder_fire(reminder: dict) -> None:
    text = reminder["text"]
    lang = reminder.get("lang", "en")
    prefix = "நினைவூட்டல்: " if lang.startswith("ta") else "Reminder: "
    print(f"\n[REMINDER] {text}")
    conv_log("reminder", text, lang)
    try:
        speak(prefix + text, lang)
    except Exception as e:
        print(f"[reminder] speak failed: {e}")


def _wait_for_voice(seconds: float) -> bool:
    detected = {"v": False}
    deadline = time.time() + seconds

    def cb(indata, frames, time_info, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        if rms > FOLLOWUP_VOICE_RMS:
            detected["v"] = True

    try:
        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, callback=cb, dtype="float32"):
            while time.time() < deadline and not detected["v"]:
                sd.sleep(80)
    except Exception as e:
        print(f"[followup] voice-detect error: {e}")
        return False
    return detected["v"]


def _process_user_turn(brain: Brain, text: str, lang: str, speak_reply: bool = True) -> None:
    print(f"[heard:{lang}] {text}")
    conv_log("user", text, lang)
    try:
        reply = brain.think(text, lang=lang)
    except Exception as e:
        traceback.print_exc()
        reply = f"Sorry, something broke: {e}"
    print(f"[reply:{lang}] {reply}")
    conv_log("jarvis", reply, lang)
    if speak_reply:
        speak(reply, lang)


# ===== MODE: TEXT (no mic, type commands) =====

def run_text_mode(brain: Brain, speak_replies: bool) -> int:
    print("\n=== TEXT MODE ===")
    print("Type a command and press ENTER. Replies print in console" +
          (" and are spoken aloud." if speak_replies else "."))
    print("Type 'quit' or Ctrl+C to exit.\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit] bye.")
            return 0
        if not text:
            continue
        if text.lower() in {"quit", "exit", "bye"}:
            return 0
        # Naive language detection — has Tamil unicode = Tamil.
        lang = "ta" if any("஀" <= c <= "௿" for c in text) else "en"
        _process_user_turn(brain, text, lang, speak_reply=speak_replies)


# ===== MODE: VOICE (press ENTER to talk, no wake word) =====

def run_voice_mode(brain: Brain) -> int:
    print("\n=== VOICE MODE (press ENTER to talk) ===")
    calibrate_silence()
    speak("Voice mode. Press enter and then talk.", "en")
    while True:
        try:
            input("\n[Press ENTER to start listening, Ctrl+C to quit] ")
        except (EOFError, KeyboardInterrupt):
            print("\n[exit] bye.")
            return 0
        print("Listening... speak now.")
        try:
            import winsound; winsound.Beep(900, 120)
        except Exception:
            pass
        audio = record_until_silence()
        text, lang = transcribe(audio)
        if not text.strip():
            print("(nothing heard)")
            speak("I didn't catch that.", "en")
            continue
        _process_user_turn(brain, text, lang)


# ===== MODE: WAKE (wake-word + voice) =====

def run_wake_mode(brain: Brain) -> int:
    from jarvis.voice.wake import WakeWordListener
    print("\n=== WAKE MODE ===")
    try:
        wake = WakeWordListener()
    except Exception as e:
        print(f"[wake] Failed to start wake-word listener: {e}")
        print("Tip: try 'python run.py voice' (press-ENTER mode) to test the rest of the pipeline.")
        return 1

    calibrate_silence()
    speak("Good day, sir. Jarvis online and at your service.", "en")

    try:
        while True:
            print("\n[idle] waiting for 'Hey Jarvis'...")
            wake.wait_for_wake()
            print("[wake] detected. Listening...")
            try:
                import winsound; winsound.Beep(900, 120)
            except Exception:
                pass

            text, lang = listen()
            if not text:
                speak("I didn't catch that.", "en")
                continue
            from jarvis.conversation import is_exit_phrase, farewell
            if is_exit_phrase(text):
                speak(farewell(lang), lang); continue
            _process_user_turn(brain, text, lang)

            # Natural conversation: keep talking until the user says they're done
            # (or two silences in a row). No need to repeat "Hey Jarvis".
            misses = 0
            while True:
                print(f"[conversation] listening...")
                if not _wait_for_voice(FOLLOWUP_SECONDS):
                    misses += 1
                    if misses >= 2:
                        print("[conversation] ending — back to wake word.")
                        break
                    continue
                misses = 0
                audio = record_until_silence()
                text, lang = transcribe(audio)
                if not text.strip():
                    continue
                if is_exit_phrase(text):
                    speak(farewell(lang), lang)
                    break
                _process_user_turn(brain, text, lang)
    finally:
        try:
            wake.close()
        except Exception:
            pass
    return 0


# ===== MAIN =====

def main() -> int:
    try:
        assert_keys()
    except RuntimeError as e:
        print(str(e))
        return 1

    mode = (sys.argv[1].lower() if len(sys.argv) > 1 else "wake").strip()
    no_speak = "--no-speak" in sys.argv
    if mode not in {"text", "voice", "wake", "telegram"}:
        print(f"Unknown mode '{mode}'. Use: text | voice | wake | telegram")
        return 1

    if mode == "telegram":
        from jarvis.telegram_bridge import run_bridge
        return run_bridge()

    print("=" * 60)
    print(f" JARVIS — bilingual voice assistant  (mode: {mode})")
    print(" Ctrl+C to quit.")
    print("=" * 60)

    brain = Brain()
    scheduler = ReminderScheduler(on_fire=on_reminder_fire)
    scheduler.start()

    try:
        if mode == "text":
            return run_text_mode(brain, speak_replies=not no_speak)
        if mode == "voice":
            return run_voice_mode(brain)
        return run_wake_mode(brain)
    except KeyboardInterrupt:
        print("\n[exit] shutting down.")
        return 0
    finally:
        scheduler.stop()


if __name__ == "__main__":
    sys.exit(main())
