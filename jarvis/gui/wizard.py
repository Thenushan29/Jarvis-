"""First-run wizard — opens the Settings dialog if no provider key is set."""
from __future__ import annotations
from PySide6.QtWidgets import QMessageBox

from ..settings import load as load_settings
from .settings_dialog import SettingsDialog


def needs_first_run() -> bool:
    s = load_settings()
    # If no api key is set in settings and the legacy env-loaded config also has nothing,
    # we trigger the wizard. Otherwise skip.
    if s.get("llm_api_key"):
        return False
    # Fall back to env (config.py reads .env on import).
    from .. import config
    return not bool(config.LLM_API_KEY)


def run_first_run_wizard(parent=None) -> bool:
    """Returns True if user finished setup (saved settings), False if cancelled."""
    msg = QMessageBox(parent)
    msg.setWindowTitle("Welcome to Jarvis")
    msg.setText("Welcome! Jarvis needs an LLM API key to think.\n\n"
                "Pick a provider on the next screen and paste your key. "
                "Most providers (Groq, Gemini) have a free tier — no credit card needed.")
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    if msg.exec() != QMessageBox.Ok:
        return False
    dlg = SettingsDialog(parent)
    return bool(dlg.exec())
