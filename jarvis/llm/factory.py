"""Factory: read config and produce the right LLM + vision client."""
from __future__ import annotations

from ..config import (
    LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL,
    VISION_PROVIDER, VISION_API_KEY, VISION_MODEL, VISION_BASE_URL,
)
from .base import LLMClient


# === Sensible defaults per provider so user can supply just the key =============
PROVIDER_DEFAULTS: dict[str, dict] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "vision_model": "meta-llama/llama-4-scout-17b-16e-instruct",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "vision_model": "gpt-4o",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4",
        "vision_model": "anthropic/claude-sonnet-4",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash",
        "vision_model": "gemini-2.5-flash",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.3",
        "vision_model": "llava",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "vision_model": "meta-llama/Llama-Vision-Free",
    },
    "anthropic": {
        "base_url": None,
        "model": "claude-sonnet-4-6",
        "vision_model": "claude-sonnet-4-6",
    },
    "openai_compat": {
        # Generic — user must provide both base_url and model.
        "base_url": None,
        "model": None,
        "vision_model": None,
    },
}


def _resolve(provider: str, key_kind: str, override: str) -> str:
    """Return override if non-empty, else the default for this provider, else ''."""
    if override:
        return override
    return PROVIDER_DEFAULTS.get(provider, {}).get(key_kind, "") or ""


def make_llm_client() -> LLMClient:
    """Build the configured LLM client for the brain."""
    provider = (LLM_PROVIDER or "groq").lower()
    base_url = _resolve(provider, "base_url", LLM_BASE_URL)
    model = _resolve(provider, "model", LLM_MODEL)

    if not LLM_API_KEY:
        raise RuntimeError(
            f"LLM_API_KEY is empty. Set it in .env (provider={provider})."
        )
    if not model:
        raise RuntimeError(
            f"LLM_MODEL is empty and provider '{provider}' has no default. Set LLM_MODEL in .env."
        )

    if provider == "anthropic":
        from .anthropic_provider import AnthropicClient
        return AnthropicClient(api_key=LLM_API_KEY, model=model)

    # Everything else uses the OpenAI-compatible client.
    from .openai_compat import OpenAICompatClient
    return OpenAICompatClient(api_key=LLM_API_KEY, model=model, base_url=base_url or None)


def make_vision_client():
    """Build a vision-capable client. Defaults to the same provider/key as the brain."""
    provider = (VISION_PROVIDER or LLM_PROVIDER or "groq").lower()
    api_key = VISION_API_KEY or LLM_API_KEY
    model = _resolve(provider, "vision_model", VISION_MODEL)
    base_url = _resolve(provider, "base_url", VISION_BASE_URL)

    if not api_key:
        raise RuntimeError("No API key set for vision (LLM_API_KEY or VISION_API_KEY).")
    if not model:
        raise RuntimeError(f"No vision model for provider '{provider}'. Set VISION_MODEL.")

    if provider == "anthropic":
        from .anthropic_provider import AnthropicClient
        return ("anthropic", AnthropicClient(api_key=api_key, model=model))

    from .openai_compat import OpenAICompatClient
    return ("openai_compat", OpenAICompatClient(api_key=api_key, model=model, base_url=base_url or None))
