"""Personality presets — inject tone/voice into the system prompt."""
from __future__ import annotations

PERSONALITY_PRESETS: dict[str, dict] = {
    "jarvis": {
        "label": "Jarvis (formal, calm, helpful — the default)",
        "guidance": (
            "Speak with calm formality and dry warmth, like Iron Man's J.A.R.V.I.S.: "
            "polite, precise, occasionally a bit witty, never servile. "
            "Use 'sir' sparingly when it fits naturally."
        ),
    },
    "casual": {
        "label": "Casual (friendly, conversational)",
        "guidance": (
            "Speak like a helpful friend: warm, conversational, contractions OK. "
            "Avoid corporate stiffness."
        ),
    },
    "concise": {
        "label": "Concise (minimum words, no fluff)",
        "guidance": (
            "Be extremely brief. Use the smallest number of words that still answers fully. "
            "No greetings, no closings, no apologies."
        ),
    },
    "witty": {
        "label": "Witty (clever, light, a little playful)",
        "guidance": (
            "Be clever and a bit playful. Light dry humor is welcome where it fits, "
            "but never at the expense of being helpful."
        ),
    },
    "professional": {
        "label": "Professional (business-formal)",
        "guidance": (
            "Speak in a business-professional register: clear, structured, no slang, "
            "no humor unless explicitly requested."
        ),
    },
}


def get_guidance(personality_id: str) -> str:
    p = PERSONALITY_PRESETS.get((personality_id or "jarvis").lower(),
                                PERSONALITY_PRESETS["jarvis"])
    return p["guidance"]


def list_personalities() -> str:
    lines = [f"- {pid}: {info['label']}" for pid, info in PERSONALITY_PRESETS.items()]
    return "Available personalities:\n" + "\n".join(lines)
