"""Settings dialog — pick provider, paste API key, pick a voice, preview it, save."""
from __future__ import annotations
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QHBoxLayout, QDialogButtonBox, QMessageBox,
    QGroupBox, QTabWidget, QWidget,
)

from ..settings import load as load_settings, save as save_settings, PROVIDER_INFO
from ..voice.presets import ENGLISH_PRESETS, TAMIL_PRESETS, find_preset


class _TestWorker(QThread):
    finished_with = Signal(bool, str)

    def __init__(self, provider: str, api_key: str, model: str, base_url: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def run(self):
        from ..llm.test_provider import test_provider
        ok, msg = test_provider(self.provider, self.api_key, self.model, self.base_url)
        self.finished_with.emit(ok, msg)


class _PreviewWorker(QThread):
    finished_with = Signal(str)   # path to mp3, or "" on failure

    def __init__(self, preset: dict):
        super().__init__()
        self.preset = preset

    def run(self):
        from ..voice.speak import preview_voice
        path = preview_voice(self.preset)
        self.finished_with.emit(path or "")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis — Settings")
        self.setMinimumWidth(620)
        self.setMinimumHeight(520)
        self._test_thread: _TestWorker | None = None
        self._preview_thread: _PreviewWorker | None = None

        s = load_settings()
        outer = QVBoxLayout(self)

        title = QLabel("⚙️  Jarvis Settings")
        f = QFont(); f.setPointSize(14); f.setBold(True); title.setFont(f)
        outer.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_brain_tab(s), "🧠  Brain")
        tabs.addTab(self._build_voice_tab(s), "🔊  Voice")
        tabs.addTab(self._build_advanced_tab(s), "⚙️  Advanced")
        outer.addWidget(tabs, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        outer.addWidget(btns)

        self._on_provider_changed()  # fill key hint

    # ===== BRAIN TAB =====
    def _build_brain_tab(self, s: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        intro = QLabel(
            "Pick an LLM provider and paste your API key. "
            "Most providers (Groq, Gemini) have a <b>free tier</b> — no credit card needed."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()

        self.provider_combo = QComboBox()
        for info in PROVIDER_INFO:
            self.provider_combo.addItem(info["label"], userData=info["id"])
        for idx in range(self.provider_combo.count()):
            if self.provider_combo.itemData(idx) == s.get("llm_provider"):
                self.provider_combo.setCurrentIndex(idx); break
        form.addRow("Provider:", self.provider_combo)

        self.key_edit = QLineEdit(s.get("llm_api_key", ""))
        self.key_edit.setEchoMode(QLineEdit.Password)
        form.addRow("API key:", self.key_edit)

        self.key_link = QLabel()
        self.key_link.setOpenExternalLinks(True)
        self.key_link.setTextFormat(Qt.RichText)
        form.addRow("", self.key_link)

        self.model_edit = QLineEdit(s.get("llm_model", ""))
        self.model_edit.setPlaceholderText("(leave blank to use provider default)")
        form.addRow("Model:", self.model_edit)

        self.url_edit = QLineEdit(s.get("llm_base_url", ""))
        self.url_edit.setPlaceholderText("(leave blank for provider default)")
        form.addRow("Base URL:", self.url_edit)

        layout.addLayout(form)

        # Test row
        test_row = QHBoxLayout()
        self.test_btn = QPushButton("🧪  Test connection")
        self.test_status = QLabel("")
        self.test_status.setWordWrap(True)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_status, 1)
        layout.addLayout(test_row)

        layout.addStretch(1)

        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.test_btn.clicked.connect(self._on_test)

        return page

    # ===== VOICE TAB =====
    def _build_voice_tab(self, s: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        intro = QLabel(
            "Pick how Jarvis sounds. The default is a deep British voice — "
            "similar to Marvel's <b>J.A.R.V.I.S.</b>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # English voice
        en_group = QGroupBox("English voice")
        en_layout = QVBoxLayout(en_group)

        en_row = QHBoxLayout()
        self.en_voice_combo = QComboBox()
        for p in ENGLISH_PRESETS:
            self.en_voice_combo.addItem(p["label"], userData=p["id"])
        cur_en = find_preset(ENGLISH_PRESETS, s.get("tts_voice_english", "jarvis"))
        for i in range(self.en_voice_combo.count()):
            if self.en_voice_combo.itemData(i) == cur_en["id"]:
                self.en_voice_combo.setCurrentIndex(i); break
        self.en_preview_btn = QPushButton("▶  Preview")
        en_row.addWidget(self.en_voice_combo, 1)
        en_row.addWidget(self.en_preview_btn)
        en_layout.addLayout(en_row)

        self.en_description = QLabel(cur_en.get("description", ""))
        self.en_description.setWordWrap(True)
        self.en_description.setStyleSheet("color: #666; font-style: italic;")
        en_layout.addWidget(self.en_description)
        layout.addWidget(en_group)

        # Tamil voice
        ta_group = QGroupBox("Tamil voice")
        ta_layout = QVBoxLayout(ta_group)

        ta_row = QHBoxLayout()
        self.ta_voice_combo = QComboBox()
        for p in TAMIL_PRESETS:
            self.ta_voice_combo.addItem(p["label"], userData=p["id"])
        cur_ta = find_preset(TAMIL_PRESETS, s.get("tts_voice_tamil", "tamil_male"))
        for i in range(self.ta_voice_combo.count()):
            if self.ta_voice_combo.itemData(i) == cur_ta["id"]:
                self.ta_voice_combo.setCurrentIndex(i); break
        self.ta_preview_btn = QPushButton("▶  Preview")
        ta_row.addWidget(self.ta_voice_combo, 1)
        ta_row.addWidget(self.ta_preview_btn)
        ta_layout.addLayout(ta_row)

        self.ta_description = QLabel(cur_ta.get("description", ""))
        self.ta_description.setWordWrap(True)
        self.ta_description.setStyleSheet("color: #666; font-style: italic;")
        ta_layout.addWidget(self.ta_description)
        layout.addWidget(ta_group)

        layout.addStretch(1)

        self.en_voice_combo.currentIndexChanged.connect(
            lambda: self._update_voice_desc(self.en_voice_combo, ENGLISH_PRESETS, self.en_description)
        )
        self.ta_voice_combo.currentIndexChanged.connect(
            lambda: self._update_voice_desc(self.ta_voice_combo, TAMIL_PRESETS, self.ta_description)
        )
        self.en_preview_btn.clicked.connect(lambda: self._preview(self.en_voice_combo, ENGLISH_PRESETS))
        self.ta_preview_btn.clicked.connect(lambda: self._preview(self.ta_voice_combo, TAMIL_PRESETS))

        return page

    # ===== ADVANCED TAB =====
    def _build_advanced_tab(self, s: dict) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.whisper_combo = QComboBox()
        for w in ("tiny", "base", "small", "medium", "large-v3"):
            self.whisper_combo.addItem(w)
        cur = s.get("whisper_model", "tiny")
        if cur in {self.whisper_combo.itemText(i) for i in range(self.whisper_combo.count())}:
            self.whisper_combo.setCurrentText(cur)
        form.addRow("Speech recognition (Whisper):", self.whisper_combo)

        self.followup_edit = QLineEdit(str(s.get("followup_seconds", 8)))
        form.addRow("Follow-up seconds:", self.followup_edit)

        self.max_listen_edit = QLineEdit(str(s.get("max_listen_seconds", 15)))
        form.addRow("Max listen seconds:", self.max_listen_edit)

        layout.addLayout(form)

        hint = QLabel(
            "<small><b>Whisper</b>: 'tiny' = fast (~0.3s), less accurate. 'small' = balanced. "
            "'large-v3' = best (esp. Tamil) but ~3 GB and slower.<br>"
            "<b>Follow-up seconds</b>: after a reply, Jarvis listens this many seconds for a "
            "continuation without needing the wake word again.</small>"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    # ===== Helpers =====
    def _update_voice_desc(self, combo: QComboBox, presets: list[dict], label: QLabel):
        chosen_id = combo.currentData()
        for p in presets:
            if p["id"] == chosen_id:
                label.setText(p.get("description", ""))
                return

    def _preview(self, combo: QComboBox, presets: list[dict]):
        if self._preview_thread and self._preview_thread.isRunning():
            return
        chosen_id = combo.currentData()
        preset = next((p for p in presets if p["id"] == chosen_id), presets[0])
        combo.parent().setCursor(Qt.WaitCursor)
        self._preview_thread = _PreviewWorker(preset)
        self._preview_thread.finished_with.connect(self._on_preview_done)
        self._preview_thread.start()

    def _on_preview_done(self, path: str):
        self.setCursor(Qt.ArrowCursor)
        if not path:
            QMessageBox.warning(self, "Preview failed",
                                "Could not generate the voice sample (network or audio issue).")
            return
        from ..voice.speak import play_audio_file
        # Play in another thread so UI doesn't freeze.
        import threading
        threading.Thread(target=play_audio_file, args=(path,), daemon=True).start()

    def _current_provider_info(self) -> dict:
        pid = self.provider_combo.currentData()
        for info in PROVIDER_INFO:
            if info["id"] == pid:
                return info
        return {}

    def _on_provider_changed(self):
        info = self._current_provider_info()
        url = info.get("key_url", "")
        if url:
            self.key_link.setText(f'<a href="{url}">📋  Click here to get your API key</a>')
        else:
            self.key_link.setText("")
        prefix = info.get("key_prefix", "")
        if prefix:
            self.key_edit.setPlaceholderText(f"Paste your API key here (starts with {prefix})")
        else:
            self.key_edit.setPlaceholderText("Paste your API key here")

    def _on_test(self):
        if self._test_thread and self._test_thread.isRunning():
            return
        info = self._current_provider_info()
        self.test_status.setText("⏳  Testing...")
        self.test_status.setStyleSheet("color: #666;")
        self.test_btn.setEnabled(False)
        self._test_thread = _TestWorker(
            provider=info["id"],
            api_key=self.key_edit.text().strip(),
            model=self.model_edit.text().strip(),
            base_url=self.url_edit.text().strip(),
        )
        self._test_thread.finished_with.connect(self._on_test_done)
        self._test_thread.start()

    def _on_test_done(self, ok: bool, msg: str):
        self.test_btn.setEnabled(True)
        if ok:
            self.test_status.setText(f"✅  {msg}")
            self.test_status.setStyleSheet("color: #2a8a2a;")
        else:
            self.test_status.setText(f"❌  {msg}")
            self.test_status.setStyleSheet("color: #b22222;")

    def _safe_int(self, text: str, default: int) -> int:
        try:
            return int(text)
        except ValueError:
            return default

    def _on_save(self):
        info = self._current_provider_info()
        save_settings({
            "llm_provider": info["id"],
            "llm_api_key": self.key_edit.text().strip(),
            "llm_model": self.model_edit.text().strip(),
            "llm_base_url": self.url_edit.text().strip(),
            "tts_voice_english": self.en_voice_combo.currentData(),
            "tts_voice_tamil": self.ta_voice_combo.currentData(),
            "whisper_model": self.whisper_combo.currentText(),
            "followup_seconds": self._safe_int(self.followup_edit.text(), 8),
            "max_listen_seconds": self._safe_int(self.max_listen_edit.text(), 15),
        })
        QMessageBox.information(
            self, "Saved",
            "Settings saved.\n\nIf Jarvis is currently running, click <b>Stop</b> then <b>Start</b> "
            "to apply the new voice + model."
        )
        self.accept()
