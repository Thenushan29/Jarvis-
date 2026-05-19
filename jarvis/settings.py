"""Settings store — JSON file in user's AppData. Persists user choices from the GUI.

Falls back to .env / defaults when settings.json is absent. Once a user changes
something via the GUI, it's written here and takes precedence.
"""
from __future__ import annotations
import json
import os
import threading
from pathlib import Path
from typing import Any


def _settings_dir() -> Path:
    """%APPDATA%\\Jarvis on Windows, ~/.config/jarvis elsewhere."""
    appdata = os.getenv("APPDATA")
    if appdata:
        d = Path(appdata) / "Jarvis"
    else:
        d = Path.home() / ".config" / "jarvis"
    d.mkdir(parents=True, exist_ok=True)
    return d


SETTINGS_FILE = _settings_dir() / "settings.json"

_lock = threading.Lock()
_cache: dict | None = None

# Keys we manage (so we don't blow away unknown user-added keys).
SCHEMA: dict[str, Any] = {
    "llm_provider": "groq",
    "llm_api_key": "",
    "llm_model": "",
    "llm_base_url": "",
    "vision_provider": "",
    "vision_api_key": "",
    "vision_model": "",
    "vision_base_url": "",
    "tts_voice_tamil": "tamil_male",
    "tts_voice_english": "jarvis",      # Iron Man Jarvis preset by default
    "whisper_model": "tiny",
    "max_listen_seconds": 15,
    "followup_seconds": 8,
    "auto_start_on_boot": False,
    "default_mode": "wake",     # wake | voice | text
}


def _load_disk() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load() -> dict:
    """Load settings into the cache. Returns the full merged dict."""
    global _cache
    with _lock:
        if _cache is None:
            disk = _load_disk()
            merged = dict(SCHEMA)
            merged.update({k: v for k, v in disk.items() if k in SCHEMA})
            _cache = merged
        return dict(_cache)


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def save(updates: dict) -> None:
    """Update one or more settings and persist to disk."""
    global _cache
    with _lock:
        current = _load_disk()
        for k, v in updates.items():
            if k in SCHEMA:
                current[k] = v
        SETTINGS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
        _cache = None  # force reload next get()


def settings_path() -> Path:
    return SETTINGS_FILE


# ===== Provider helpers =====

PROVIDER_INFO = [
    {"id": "groq",         "label": "Groq (free, fast)",            "key_url": "https://console.groq.com/keys",                 "key_prefix": "gsk_"},
    {"id": "openai",       "label": "OpenAI (GPT-4o etc.)",         "key_url": "https://platform.openai.com/api-keys",          "key_prefix": "sk-"},
    {"id": "anthropic",    "label": "Anthropic Claude",             "key_url": "https://console.anthropic.com/",                "key_prefix": "sk-ant-"},
    {"id": "gemini",       "label": "Google Gemini (free tier)",    "key_url": "https://aistudio.google.com/app/apikey",        "key_prefix": "AIza"},
    {"id": "openrouter",   "label": "OpenRouter (many models)",     "key_url": "https://openrouter.ai/keys",                    "key_prefix": "sk-or-"},
    {"id": "ollama",       "label": "Ollama (local, no internet)",  "key_url": "https://ollama.com/download",                   "key_prefix": ""},
    {"id": "together",     "label": "Together AI",                  "key_url": "https://api.together.xyz/settings/api-keys",    "key_prefix": ""},
    {"id": "openai_compat","label": "Custom OpenAI-compatible",     "key_url": "",                                              "key_prefix": ""},
]


def apply_to_environ() -> None:
    """Copy settings into os.environ so the existing config.py picks them up.

    Called early in app startup BEFORE jarvis.config is imported.
    """
    s = load()
    mapping = {
        "LLM_PROVIDER":    s.get("llm_provider", ""),
        "LLM_API_KEY":     s.get("llm_api_key", ""),
        "LLM_MODEL":       s.get("llm_model", ""),
        "LLM_BASE_URL":    s.get("llm_base_url", ""),
        "VISION_PROVIDER": s.get("vision_provider", ""),
        "VISION_API_KEY":  s.get("vision_api_key", ""),
        "VISION_MODEL":    s.get("vision_model", ""),
        "VISION_BASE_URL": s.get("vision_base_url", ""),
        "TTS_VOICE_TAMIL": s.get("tts_voice_tamil", ""),
        "TTS_VOICE_ENGLISH": s.get("tts_voice_english", ""),
        "WHISPER_MODEL":   s.get("whisper_model", ""),
        "MAX_LISTEN_SECONDS": str(s.get("max_listen_seconds", 15)),
        "FOLLOWUP_SECONDS":   str(s.get("followup_seconds", 8)),
    }
    for k, v in mapping.items():
        if v:
            os.environ[k] = str(v)
