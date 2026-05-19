"""Main Jarvis window — status display, controls, recent conversation log."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QStatusBar,
)
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from .worker import JarvisWorker
from .settings_dialog import SettingsDialog
from ..settings import load as load_settings, save as save_settings


STATUS_COLOR = {
    "idle":      "#888",
    "starting":  "#cc9933",
    "listening": "#3366cc",
    "thinking":  "#9933cc",
    "speaking":  "#33aa66",
    "error":     "#cc3333",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jarvis")
        self.resize(640, 520)

        s = load_settings()
        self.worker = JarvisWorker(self)
        self.worker.status_changed.connect(self._on_status)
        self.worker.message_logged.connect(self._on_log)
        self.worker.error.connect(self._on_error)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Status row
        status_row = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #888; font-size: 22px;")
        self.status_text = QLabel("Idle")
        f = QFont(); f.setBold(True); f.setPointSize(11)
        self.status_text.setFont(f)
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_text, 1)

        # Mode picker + start/stop
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Wake word (Hey Jarvis)", "wake")
        self.mode_combo.addItem("Voice (manual trigger)", "voice")
        cur_mode = s.get("default_mode", "wake")
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == cur_mode:
                self.mode_combo.setCurrentIndex(i); break
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.settings_btn = QPushButton("Settings...")

        status_row.addWidget(self.mode_combo)
        status_row.addWidget(self.start_btn)
        status_row.addWidget(self.stop_btn)
        status_row.addWidget(self.settings_btn)
        layout.addLayout(status_row)

        # Conversation log
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.log_view, 1)

        # Talk-now button (only relevant in voice mode)
        self.talk_btn = QPushButton("🎤  Talk now")
        self.talk_btn.setEnabled(False)
        self.talk_btn.setMinimumHeight(40)
        layout.addWidget(self.talk_btn)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"Provider: {s.get('llm_provider','?')}  |  Model: {s.get('llm_model') or '(default)'}")

        # Wire
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)
        self.settings_btn.clicked.connect(self._open_settings)
        self.talk_btn.clicked.connect(lambda: self.worker.request_voice_turn())

    # --- actions ---
    def _start(self):
        mode = self.mode_combo.currentData()
        save_settings({"default_mode": mode})
        self.worker.start(mode)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.mode_combo.setEnabled(False)
        self.talk_btn.setEnabled(mode == "voice")
        self._append("system", f"Starting in {mode} mode...")

    def _stop(self):
        self.worker.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.mode_combo.setEnabled(True)
        self.talk_btn.setEnabled(False)
        self._append("system", "Stop requested. (May need to close window to fully exit wake mode.)")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            s = load_settings()
            self.statusBar().showMessage(
                f"Provider: {s.get('llm_provider','?')}  |  Model: {s.get('llm_model') or '(default)'}"
            )

    # --- signals from worker ---
    def _on_status(self, s: str):
        self.status_text.setText(s.capitalize())
        color = STATUS_COLOR.get(s, "#888")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 22px;")

    def _on_log(self, role: str, text: str):
        self._append(role, text)

    def _on_error(self, msg: str):
        self._append("error", msg)
        self._on_status("error")

    # --- helpers ---
    def _append(self, role: str, text: str):
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        prefix_colors = {
            "you": "#3366cc",
            "jarvis": "#2a8a2a",
            "reminder": "#cc9933",
            "system": "#888",
            "error": "#cc3333",
        }
        fmt.setForeground(QColor(prefix_colors.get(role, "#222")))
        fmt.setFontWeight(QFont.Bold)
        cursor.insertText(f"{role}: ", fmt)
        fmt2 = QTextCharFormat()
        fmt2.setForeground(QColor("#222"))
        cursor.insertText(text + "\n", fmt2)
        self.log_view.setTextCursor(cursor)
        self.log_view.ensureCursorVisible()

    # --- close behavior ---
    def closeEvent(self, event):
        # Hide to tray instead of quitting if tray icon is visible
        if hasattr(self, "_hide_on_close") and self._hide_on_close:
            event.ignore()
            self.hide()
        else:
            self.worker.stop()
            super().closeEvent(event)
