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

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Groq brain model. Default is the smartest free-tier model.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
# Vision model — must be a multimodal Groq model.
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct").strip()
TTS_VOICE_TAMIL = os.getenv("TTS_VOICE_TAMIL", "ta-IN-ValluvarNeural").strip()
TTS_VOICE_ENGLISH = os.getenv("TTS_VOICE_ENGLISH", "en-US-GuyNeural").strip()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small").strip()
MAX_LISTEN_SECONDS = int(os.getenv("MAX_LISTEN_SECONDS", "15"))

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
REMINDERS_FILE = DATA_DIR / "reminders.json"
MEMORY_FILE = DATA_DIR / "memory.json"
CONVERSATION_LOG = DATA_DIR / "conversation.log"
FOLLOWUP_SECONDS = int(os.getenv("FOLLOWUP_SECONDS", "8"))


def assert_keys():
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if missing:
        raise RuntimeError(
            "Missing required keys in .env: " + ", ".join(missing)
            + "\nCopy .env.example to .env and fill them in. See README.md."
        )
