"""Settings dialog — pick provider, paste API key, test it, save."""
from __future__ import annotations
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QHBoxLayout, QDialogButtonBox, QMessageBox,
)

from ..settings import load as load_settings, save as save_settings, PROVIDER_INFO


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


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis — Settings")
        self.setMinimumWidth(540)
        self._test_thread: _TestWorker | None = None

        s = load_settings()
        layout = QVBoxLayout(self)

        # Heading
        h = QLabel("<b>LLM provider</b><br><small>Pick a provider and paste your API key. "
                   "Click <i>Test</i> to verify before saving.</small>")
        h.setWordWrap(True)
        layout.addWidget(h)

        form = QFormLayout()

        # Provider dropdown
        self.provider_combo = QComboBox()
        for info in PROVIDER_INFO:
            self.provider_combo.addItem(info["label"], userData=info["id"])
        for idx in range(self.provider_combo.count()):
            if self.provider_combo.itemData(idx) == s.get("llm_provider"):
                self.provider_combo.setCurrentIndex(idx)
                break
        form.addRow("Provider:", self.provider_combo)

        # API key
        self.key_edit = QLineEdit(s.get("llm_api_key", ""))
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Paste your API key here")
        form.addRow("API key:", self.key_edit)

        self.key_link = QLabel()
        self.key_link.setOpenExternalLinks(True)
        self.key_link.setTextFormat(Qt.RichText)
        form.addRow("", self.key_link)

        # Model
        self.model_edit = QLineEdit(s.get("llm_model", ""))
        self.model_edit.setPlaceholderText("(leave blank to use provider default)")
        form.addRow("Model:", self.model_edit)

        # Base URL
        self.url_edit = QLineEdit(s.get("llm_base_url", ""))
        self.url_edit.setPlaceholderText("(leave blank for provider default)")
        form.addRow("Base URL:", self.url_edit)

        layout.addLayout(form)

        # Voices
        voice_h = QLabel("<b>Voices</b>")
        layout.addWidget(voice_h)
        vform = QFormLayout()
        self.en_voice = QLineEdit(s.get("tts_voice_english", ""))
        self.ta_voice = QLineEdit(s.get("tts_voice_tamil", ""))
        vform.addRow("English voice:", self.en_voice)
        vform.addRow("Tamil voice:", self.ta_voice)
        layout.addLayout(vform)

        # Whisper model
        wform = QFormLayout()
        self.whisper_combo = QComboBox()
        for w in ("tiny", "base", "small", "medium", "large-v3"):
            self.whisper_combo.addItem(w)
        cur = s.get("whisper_model", "tiny")
        if cur in {self.whisper_combo.itemText(i) for i in range(self.whisper_combo.count())}:
            self.whisper_combo.setCurrentText(cur)
        wform.addRow("Whisper STT model:", self.whisper_combo)
        layout.addLayout(wform)

        # Test row
        test_row = QHBoxLayout()
        self.test_btn = QPushButton("Test connection")
        self.test_status = QLabel("")
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_status, 1)
        layout.addLayout(test_row)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(btns)

        # Wire up
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.test_btn.clicked.connect(self._on_test)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)

        self._on_provider_changed()  # initialize hint text

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
            self.key_link.setText(f'<a href="{url}">Get an API key here</a>')
        else:
            self.key_link.setText("")
        prefix = info.get("key_prefix", "")
        if prefix:
            self.key_edit.setPlaceholderText(f"Paste your API key here (typically starts with {prefix})")
        else:
            self.key_edit.setPlaceholderText("Paste your API key here")

    def _on_test(self):
        info = self._current_provider_info()
        if self._test_thread and self._test_thread.isRunning():
            return
        self.test_status.setText("Testing...")
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
            self.test_status.setText(f"✓ {msg}")
            self.test_status.setStyleSheet("color: #2a8a2a;")
        else:
            self.test_status.setText(f"✗ {msg}")
            self.test_status.setStyleSheet("color: #b22222;")

    def _on_save(self):
        info = self._current_provider_info()
        save_settings({
            "llm_provider": info["id"],
            "llm_api_key": self.key_edit.text().strip(),
            "llm_model": self.model_edit.text().strip(),
            "llm_base_url": self.url_edit.text().strip(),
            "tts_voice_english": self.en_voice.text().strip(),
            "tts_voice_tamil": self.ta_voice.text().strip(),
            "whisper_model": self.whisper_combo.currentText(),
        })
        QMessageBox.information(self, "Saved", "Settings saved. Restart Jarvis for changes to take effect.")
        self.accept()
