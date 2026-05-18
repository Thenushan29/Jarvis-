# Jarvis — Bilingual Voice Assistant (Tamil + English)

A personal AI voice agent for Windows. Wake word, speech-to-text, Groq brain
with tool calling, text-to-speech. Speaks Tamil and English (auto-detected per turn).

---

## 🚀 Quick start (after cloning)

### 1. Clone & enter the folder

```powershell
git clone https://github.com/Thenushan29/Jarvis-.git
cd Jarvis-
```

### 2. Requirements

- **Windows 10/11**
- **Python 3.11 or 3.12** recommended (3.13 works but some wheels are still rolling out)
- **Google Chrome** (only if you want WhatsApp Web features)
- A working **microphone** and **speakers/headphones**
- Internet (for first-run model downloads + Groq API)

### 3. Get a free Groq API key (no credit card)

1. Go to https://console.groq.com/keys
2. Sign up (Google login works)
3. Click **Create API Key** → copy it (starts with `gsk_...`)

> Wake word ("Hey Jarvis") uses **openWakeWord** which is fully local — no second account needed.

### 4. Install Python packages

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run this once:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 5. Configure `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace `your_groq_api_key_here` with your actual key. Save, close.

### 6. Run him

You have **three modes** — start with `text` to confirm everything works:

```powershell
python run.py text   # type commands, no mic needed (best first test)
python run.py voice  # press ENTER, then speak
python run.py wake   # always-on "Hey Jarvis" wake word
```

In text mode, type:
```
What time is it?
Open YouTube
Remember my favorite food is dosa
quit
```

If those work, you're set. Try `voice` mode next, then `wake`.

---

## 🧠 What Jarvis can do

### Voice & system
- **Wake on "Hey Jarvis"** — fully local, ~30 MB model cached
- **Open apps & websites** — Chrome, YouTube, WhatsApp, VS Code, Spotify, anything
- **PC control** — volume, mute, lock, sleep, shutdown, screenshot
- **Media keys** — play/pause/next/prev for Spotify, YouTube, etc.
- **Reminders** — "Remind me to call amma tomorrow at 9am" (voice alert when due)

### Code & shell
- **Read & write files** — "Open my python file and add a function that…"
- **Run PowerShell** — with a destructive-command blocklist
- **List directories** — "What files are in my Desktop?"

### Apps & install
- **Install any app via winget** — "Install Spotify" → confirms → installs
- **Search winget catalog**

### Web, mail, messages
- **Web search & YouTube** — "Search for lofi" / "Play music on YouTube"
- **Read Gmail** (after OAuth setup) — "Any unread emails?"
- **Send Gmail** — confirms recipient + body before sending
- **WhatsApp Web** — read recent chats, read messages, send

### Memory & vision
- **Long-term memory** — "Remember my work hours are 10 to 6" / "What's my amma's number?"
- **Screen vision** — "Hey Jarvis, what's on my screen?"

---

## 🔧 Tech stack

| Layer | Tech | Notes |
|---|---|---|
| Wake word | openWakeWord (`hey_jarvis_v0.1.onnx`) | Fully local |
| STT | `faster-whisper` | Tamil + English auto-detect |
| TTS | `edge-tts` (Microsoft neural voices) | Free, has Tamil voices |
| Brain | Groq `llama-3.3-70b-versatile` | Free tier, fast |
| Vision | Groq `llama-4-scout-17b-16e-instruct` | Multimodal Llama 4 |
| Wake mic | `sounddevice` | int16 @ 16 kHz |
| WhatsApp | `selenium` + persistent Chrome profile | One-time QR scan |
| Gmail | `google-api-python-client` | OAuth 2.0 |

---

## 🔌 Optional setup per feature

### Gmail (if you want email features)

1. https://console.cloud.google.com/ → create a project (free)
2. **APIs & Services → Library** → search "Gmail API" → **Enable**
3. **OAuth consent screen** → External → fill app name + your email → add yourself as a **Test user**
4. **Credentials → Create Credentials → OAuth client ID** → **Desktop app** → download JSON
5. Save it as `data/gmail_credentials.json` in this folder
6. First time Jarvis uses Gmail, browser opens — grant access → token cached at `data/gmail_token.json`

### WhatsApp Web

1. Make sure **Google Chrome** is installed (https://google.com/chrome)
2. First time you say "send WhatsApp" or "read WhatsApp", Chrome opens to https://web.whatsapp.com
3. On your phone: **WhatsApp → ⋮ → Linked Devices → Link a device → scan QR**
4. Done — session saved at `data/wa_chrome_profile/`

> To log out: delete `data/wa_chrome_profile/`.

---

## 🗣️ Example things to say

### English
- "Hey Jarvis, open YouTube and search for lofi music."
- "Remind me to submit the report tomorrow at 10am."
- "Read C colon backslash users backslash me backslash Desktop backslash todo dot txt."
- "Install VS Code."
- "What's on my screen?"
- "Check my unread emails."
- "Read the last 5 messages from Amma on WhatsApp."
- "Send a WhatsApp to Amma saying I'll be home by 7."
- "Remember my birthday is March 15."
- "Play music." / "Pause." / "Next song."

### Tamil
- "Hey Jarvis, YouTube-la lofi music podu."
- "Naalaiku kaalaila 9 mani-ku amma-ku phone pannanum nu nyabagam padutha."
- "Time enna sollu."
- "En screen-la enna irukku paaru."

---

## 📁 Project layout

```
Jarvis/
├── run.py                  entry point — three modes (text/voice/wake)
├── mic_check.py            standalone diagnostic for mic + wake word
├── requirements.txt
├── .env.example            template — copy to .env, add your key
├── data/                   (gitignored — local secrets and state)
│   ├── reminders.json
│   ├── memory.json
│   ├── conversation.log
│   ├── gmail_credentials.json   (place yours here)
│   ├── gmail_token.json    (auto)
│   └── wa_chrome_profile/  (auto)
└── jarvis/
    ├── config.py
    ├── brain.py            Groq brain + tool-calling loop
    ├── conversation_log.py
    ├── voice/
    │   ├── wake.py         openWakeWord ("hey_jarvis")
    │   ├── listen.py       faster-whisper STT (auto language)
    │   └── speak.py        Edge TTS (bilingual voices)
    └── tools/
        ├── apps.py         open apps, websites, searches
        ├── system.py       volume, lock, sleep, screenshot, media keys
        ├── reminders.py    persistent reminders + scheduler thread
        ├── memory.py       long-term fact storage
        ├── code.py         file ops + shell (with safety blocklist)
        ├── winget.py       install / uninstall / search apps
        ├── vision.py       screenshot + Llama 4 Scout vision
        ├── whatsapp.py     WhatsApp Web automation (read + send)
        └── gmail.py        Gmail read / search / send
```

---

## 🛡️ Safety

- **Destructive actions** (shutdown, sleep, send WhatsApp/email, install/uninstall apps, run shell)
  require verbal confirmation in the system prompt.
- **Shell blocklist** at the tool level: refuses `Remove-Item -Recurse -Force`, `Format-Volume`,
  `rm -rf /`, fork bombs, `iex (irm | iex)` malware patterns, auto-elevation, etc.
- **Mic is local-only for wake word**: Porcupine/openWakeWord processes audio entirely on-device.
  Nothing leaves your PC until you actually talk after the wake word.
- **Logs**: every voice turn (user + Jarvis) is written to `data/conversation.log` for transparency.

---

## 🩺 Troubleshooting

| Problem | Fix |
|---|---|
| `No module named X` | Activate the venv: `.\.venv\Scripts\Activate.ps1` |
| Mic not capturing | Windows Settings → Privacy → Microphone → on |
| Wake word never triggers | Run `python mic_check.py` to see live scores. Lower `DETECTION_THRESHOLD` in [jarvis/voice/wake.py](jarvis/voice/wake.py) |
| Whisper download slow | Set `WHISPER_MODEL=tiny` in `.env` (~39 MB vs ~500 MB) |
| Tamil voice sounds robotic | Try `TTS_VOICE_TAMIL=ta-IN-PallaviNeural` in `.env` |
| Gmail token expired | Delete `data/gmail_token.json` → re-auth on next run |
| WhatsApp selectors broken | WhatsApp Web's HTML changed — update selectors in [jarvis/tools/whatsapp.py](jarvis/tools/whatsapp.py) `_S` class |
| Pygame mixer fails | Set a default audio output in Windows Sound settings |
| `Refusing dangerous command` | Working as intended — Jarvis blocked a risky shell command |

---

## 🛣️ Roadmap

- [ ] Settings GUI (PySide6) so users don't edit `.env` manually
- [ ] Multi-provider brain (OpenAI / Claude / Gemini / Ollama in addition to Groq)
- [ ] System tray icon (always-on, right-click menu)
- [ ] PyInstaller bundle → single `Jarvis.exe` installer
- [ ] Recurring reminders ("every Monday at 9am")
- [ ] Google Calendar sync
- [ ] Custom wake word training

---

## 📝 License

Personal project. Use, fork, modify freely.
