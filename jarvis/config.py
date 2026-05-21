"""Central config — loads .env and exposes settings."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Silence noisy HuggingFace warnings about anonymous downloads. Set BEFORE importing
# anything that pulls from HF Hub (faster-whisper does this lazily).
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


# ===== LLM provider config =====
# Pick one: groq | openai | anthropic | gemini | openrouter | ollama | together | openai_compat
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()

# Optional: a fallback LLM used automatically when the primary rate-limits / errors.
# Must be the SAME API family as the primary (e.g. primary=groq, fallback=gemini —
# both OpenAI-compatible). Great free pairing: Groq + Gemini.
LLM_FALLBACK_PROVIDER = os.getenv("LLM_FALLBACK_PROVIDER", "").strip().lower()
LLM_FALLBACK_API_KEY = os.getenv("LLM_FALLBACK_API_KEY", "").strip()
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "").strip()

# Optional: vision provider can differ from text provider.
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "").strip().lower()
VISION_API_KEY = os.getenv("VISION_API_KEY", "").strip()
VISION_MODEL = os.getenv("VISION_MODEL", "").strip()
VISION_BASE_URL = os.getenv("VISION_BASE_URL", "").strip()


# ===== Backwards-compat: old GROQ_API_KEY / GROQ_MODEL etc still accepted =====
if not LLM_PROVIDER and (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_MODEL")):
    LLM_PROVIDER = "groq"
    LLM_API_KEY = LLM_API_KEY or os.getenv("GROQ_API_KEY", "").strip()
    LLM_MODEL = LLM_MODEL or os.getenv("GROQ_MODEL", "").strip()
    VISION_MODEL = VISION_MODEL or os.getenv("GROQ_VISION_MODEL", "").strip()

# Final default — Groq with their free key if user just dropped one in.
if not LLM_PROVIDER:
    LLM_PROVIDER = "groq"


# ===== Voice / wake config =====
TTS_VOICE_TAMIL = os.getenv("TTS_VOICE_TAMIL", "ta-IN-ValluvarNeural").strip()
TTS_VOICE_ENGLISH = os.getenv("TTS_VOICE_ENGLISH", "en-US-GuyNeural").strip()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny").strip()
MAX_LISTEN_SECONDS = int(os.getenv("MAX_LISTEN_SECONDS", "15"))

# Home Assistant (smart home) — optional
HA_URL = os.getenv("HA_URL", "").strip()
HA_TOKEN = os.getenv("HA_TOKEN", "").strip()

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
REMINDERS_FILE = DATA_DIR / "reminders.json"
MEMORY_FILE = DATA_DIR / "memory.json"
CONVERSATION_LOG = DATA_DIR / "conversation.log"
FOLLOWUP_SECONDS = int(os.getenv("FOLLOWUP_SECONDS", "8"))


def assert_keys():
    missing = []
    if not LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if missing:
        raise RuntimeError(
            "Missing required keys in .env: " + ", ".join(missing)
            + "\nCopy .env.example to .env and fill them in. See README.md."
        )
