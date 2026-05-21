# Jarvis — Personal AI Voice Assistant (Tamil + English)

A powerful, fully-featured AI assistant for Windows. Talks in **Tamil and English**,
controls your whole PC, browses the web, manages your files & schedule, and can even
**operate your screen and write its own tools**.

**107 built-in tools. 8 LLM providers. Bring your own API key.**

---

## 🚀 Quick start (new users)

### 1. Clone
```powershell
git clone https://github.com/Thenushan29/Jarvis-.git
cd Jarvis-
```

### 2. Get a free API key
Pick any provider — **Groq is free and fast** (recommended to start):
- Groq → https://console.groq.com/keys  (free, no card)
- Or: OpenAI, Anthropic Claude, Google Gemini, OpenRouter, Together, or local **Ollama**

### 3. Install
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
> Requires **Python 3.11+** (3.12/3.13 work). First run downloads small voice models.

### 4. Run
```powershell
python jarvis_app.py     # Desktop GUI (recommended) — first-run setup wizard
```
or use the CLI:
```powershell
python run.py text       # type commands, no mic (best first test)
python run.py voice      # press ENTER, then speak
python run.py wake       # always-on "Hey Jarvis"
```

### 5. First-run wizard (GUI)
1. Pick provider → paste your API key → **Test connection** ✅
2. **Voice tab** → choose a voice (default is a deep British "J.A.R.V.I.S.") → ▶ Preview
3. Save → you'll hear *"Good evening. I am Jarvis. At your service."*

That's it. Everything works immediately except features needing a one-time login
(Gmail / Calendar / WhatsApp — see [Optional setup](#-optional-setup)).

---

## 🎯 What Jarvis can do

### 🗣️ Talk
- Wake word **"Hey Jarvis"**, global hotkey **Ctrl+Alt+J**, or type
- **Tamil + English** auto-detected each turn
- 10 voice presets (incl. Iron Man Jarvis, Indian, British, American)
- 5 personalities: *"be more casual / concise / witty / professional"*

### 🖥️ Control your PC
- Open **any** installed app (Start-menu + Microsoft Store, fuzzy-matched)
- Volume, mute, lock, sleep, shutdown, screenshot, media keys
- **Type, click, hotkeys, scroll** — operate any app's UI
- Window management (focus / minimize / maximize / close)
- System health (CPU / RAM / disk / battery / uptime), kill processes
- Network info (local + public IP, WiFi, connectivity)

### 📂 Files & data
- Find files by name or content; copy / move / rename / delete (→ Recycle Bin)
- Read & write code, run PowerShell (safety-blocklisted) + sandboxed Python
- **Spreadsheet Q&A** (CSV/Excel), **Document Q&A** (PDF/text)
- **Knowledge base** — index a folder, ask questions across all docs

### ⏰ Stay organized
- Reminders (recurring + proactive "in 10 min" heads-up), notes, clipboard
- **Long-term memory** — auto-remembers facts about you
- Daily briefing, timers
- **Scheduled routines** — autonomous recurring tasks (e.g. morning brief)

### 🌐 Information
- Real web search, fetch + summarize any URL, **deep research** (multi-source)
- News, weather, stock prices, cricket scores
- Currency + unit conversion, translate (any language)

### 📧 Communication
- **Gmail** — read / search / send / draft replies
- **WhatsApp** — read chats, send messages
- **Google Calendar** — view + add events

### 🎨 Create & see
- **Generate images** from a prompt (saves to Desktop)
- **OCR** — extract text from screen or image
- **Screen vision** — *"what's on my screen?"*

### 🤖 Agentic (the powerful part)
- **Autonomous agent** — *"do this whole multi-step task"* (plans + executes)
- **Computer-use** — sees the screen, clicks, types, re-checks, repeats until done
- **Self-extension** — *writes its own new tools* on request and loads them live
- **Plugins** — drop a `.py` into `plugins/` to add tools (see `plugins/README.md`)

---

## 🔌 Optional setup

### Gmail + Calendar (Google)
1. https://console.cloud.google.com/ → new project (free)
2. Enable **Gmail API** + **Google Calendar API**
3. OAuth consent screen → External → add yourself as a **Test user**
4. Credentials → OAuth client ID → **Desktop app** → download JSON
5. Save it as `data/gmail_credentials.json`
6. First use opens a browser to grant access (token cached after)

### WhatsApp Web
1. Have **Google Chrome** installed
2. First WhatsApp command opens web.whatsapp.com → scan the QR with your phone
3. Session is saved in `data/wa_chrome_profile/` (one-time)

### Local OCR (optional)
Install Tesseract + `pip install pytesseract` for fast local OCR. Otherwise Jarvis
falls back to LLM vision automatically.

---

## 🧠 Choosing a provider

Set in the GUI (Settings → Brain) or in `.env`:

```env
LLM_PROVIDER=groq          # groq | openai | anthropic | gemini | openrouter | ollama | together
LLM_API_KEY=your_key_here
# LLM_MODEL=               # optional — defaults are sensible per provider
```

| Provider | Free? | Notes |
|---|---|---|
| **Groq** | ✅ free tier | Fast; default Llama 3.3 70B |
| **Gemini** | ✅ free tier | Good Tamil |
| **Ollama** | ✅ local | No internet, no key — runs on your PC |
| OpenAI / Anthropic / OpenRouter / Together | 💳 paid | GPT-4o, Claude, etc. |

---

## 🧩 Tech stack

| Layer | Tech |
|---|---|
| Brain | Any of 8 LLM providers (OpenAI-compatible + Anthropic) |
| Wake word | openWakeWord ("hey_jarvis", local) |
| Speech-to-text | faster-whisper (Tamil + English) |
| Text-to-speech | Edge TTS (free neural voices) |
| Vision | Multimodal LLM (Llama 4 Scout / GPT-4o / Claude) |
| Automation | pyautogui + pygetwindow |
| GUI | PySide6 (tray + window + settings) |

---

## 🖥️ Run modes

| Command | Mode |
|---|---|
| `python jarvis_app.py` | GUI desktop app + system tray |
| `python run.py text` | Type commands (no mic) |
| `python run.py voice` | Press ENTER to talk |
| `python run.py wake` | Always-on "Hey Jarvis" |

Build a standalone `.exe`: `.\build_exe.ps1` → `dist\Jarvis\Jarvis.exe`

---

## 🛡️ Safety

- Destructive actions (shutdown, delete, send email/WhatsApp, uninstall, kill process)
  require **verbal confirmation**.
- Shell commands are screened by a **blocklist** (refuses `Remove-Item -Recurse`,
  `Format-Volume`, fork bombs, `iex (irm | iex)`, etc.).
- Self-written plugins are sandbox-validated (no `os.system` / `subprocess` / file deletion).
- Wake-word audio is processed **locally** — nothing leaves your PC until you talk.
- Every turn is logged to `data/conversation.log`.

---

## 🩺 Troubleshooting

| Problem | Fix |
|---|---|
| `No module named X` | Activate venv: `.\.venv\Scripts\Activate.ps1` |
| Mic not working | Windows Settings → Privacy → Microphone → on |
| Wake word won't trigger | Run `python mic_check.py`; lower `DETECTION_THRESHOLD` in `jarvis/voice/wake.py` |
| Whisper slow | Set `WHISPER_MODEL=tiny` in `.env` |
| Rate limited (Groq) | Free tier has a daily token cap; wait or switch provider |
| Run validation | `python test_all.py` (full feature test) or `python audit.py` |

---

## 📁 Project layout

```
Jarvis/
├── jarvis_app.py          GUI entry (window + tray + wizard)
├── run.py                 CLI entry (text / voice / wake)
├── test_all.py            full feature test harness
├── audit.py               validation battery
├── jarvis/
│   ├── brain.py           LLM brain + 107-tool registry
│   ├── agent.py           autonomous multi-step agent
│   ├── routines.py        scheduled autonomous routines
│   ├── llm/               provider adapters (openai-compat + anthropic)
│   ├── voice/             wake word, STT, TTS, voice presets
│   ├── gui/               window, settings, tray, waveform, worker
│   └── tools/             ~40 tool modules (apps, files, web, vision, ...)
└── plugins/               drop-in user plugins (auto-loaded)
```

---

## 📝 License

Personal project by **Thenushan**. Use, fork, and modify freely.
