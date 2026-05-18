# Jarvis — Bilingual Voice Assistant (Tamil + English)

A personal AI voice agent for your Windows PC. Wake word, speech-to-text, Claude brain
with tool use, text-to-speech. Speaks Tamil and English (auto-detected per turn).

## What Jarvis can do

### Voice & system
- **Wake up on "Jarvis"** — always listening
- **Open apps & websites** — Chrome, YouTube, WhatsApp, VS Code, Spotify, anything
- **PC control** — volume, mute, lock, sleep, shutdown, screenshot, time
- **Reminders** — "Remind me to call amma tomorrow at 9am" (voice notification when due)

### Code & shell
- **Read & write code** — "Open my python file and add a function that…"
- **Run PowerShell commands** — with destructive-command blocklist
- **List directories** — "What files are in my Desktop?"

### Apps & install
- **Install any app via winget** — "Install Spotify" → confirms → installs
- **Search winget catalog** — "Search for VLC"

### Web, mail, messages
- **Web search & YouTube** — "Search for lofi" / "Play music on YouTube"
- **Read Gmail** — "Do I have any unread emails?" "Anything from boss this week?"
- **Send Gmail** — confirms recipient + body before sending
- **WhatsApp** — read recent chats, read messages with a contact, and send (via WhatsApp Web + Selenium)

### Memory & vision
- **Long-term memory** — "Remember my work hours are 10 to 6" / "What's my amma's number?"
- **Screen vision** — "Jarvis, what's on my screen?" "Help me read this error"

---

## Setup (one time)

### 1. Get a Groq API key (FREE — no credit card)

1. https://console.groq.com/keys → sign up (Google login works)
2. Click **Create API Key** → copy it (starts with `gsk_...`)
3. Free tier limits are generous — plenty for personal use.

> Wake word ("Jarvis") uses **openWakeWord** which runs fully locally — no second account needed.

### 2. Install Python packages

Open **PowerShell** in this folder:

```powershell
cd "C:\Users\ASUS\Desktop\Jarvis"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

First run will also download the Whisper STT model (~500 MB for "small").

### 3. Configure `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Paste your two keys, save, close.

### 4. Run

```powershell
python run.py
```

You should hear *"Jarvis online."* Say **"Jarvis"** to wake him.

---

## Optional setup per feature

### Gmail setup (if you want email features)

1. https://console.cloud.google.com/ → create a project (free)
2. **APIs & Services → Library** → search "Gmail API" → **Enable**
3. **APIs & Services → OAuth consent screen** → External → fill app name + your email
   - Add yourself as a **Test user**
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Download the JSON file
5. Save it as `data/gmail_credentials.json` in this folder
6. First time Jarvis uses Gmail, a browser opens — grant access. Token is cached.

### WhatsApp setup

WhatsApp uses Selenium with a **dedicated Chrome profile** stored at
`data/wa_chrome_profile/`. You only need to log in once.

1. Make sure **Google Chrome** is installed (download from google.com/chrome if not)
2. First time you say "Jarvis, read WhatsApp" or "send WhatsApp to ...", Chrome opens
   to https://web.whatsapp.com
3. On your phone: WhatsApp → ⋮ → **Linked Devices** → **Link a device** → scan the QR
4. Done — the session is saved. Future runs reuse it.

> If you ever want to log out, delete `data/wa_chrome_profile/` and re-link.

### Vision (already works)

Uses Claude's vision API — no extra setup. Just say "what's on my screen?".

---

## Example things to say

### English
- "Jarvis, open YouTube and search for lofi music."
- "Remind me to submit the report tomorrow at 10am."
- "Read C colon backslash users backslash ASUS backslash Desktop backslash todo dot txt."
- "Install VS Code."
- "What's on my screen?"
- "Check my unread emails."
- "Read my recent WhatsApp chats."
- "Read the last 5 messages from Amma on WhatsApp."
- "Send a WhatsApp to Amma saying 'I'll be home by 7'."
- "Remember that my birthday is March 15."

### Tamil
- "Jarvis, YouTube-la lofi music podu."
- "Naalaiku kaalaila 9 mani-ku amma-ku phone pannanum nu nyabagam padutha."
- "Time enna sollu."
- "En screen-la enna irukku paaru."

---

## Project layout

```
Jarvis/
├── run.py                  entry point — wake → listen → think → speak loop
├── requirements.txt
├── .env                    your keys (do not commit)
├── data/
│   ├── reminders.json      persistent reminders
│   ├── memory.json         long-term facts
│   ├── gmail_credentials.json  (you place this)
│   └── gmail_token.json    (auto-created after OAuth)
└── jarvis/
    ├── config.py
    ├── brain.py            Claude brain + tool-use loop + all tools wired
    ├── voice/
    │   ├── wake.py         Porcupine wake word ("Jarvis")
    │   ├── listen.py       faster-whisper STT (Tamil + English auto-detect)
    │   └── speak.py        Edge TTS (free neural voices)
    └── tools/
        ├── apps.py         open apps, websites, searches
        ├── system.py       volume, lock, sleep, screenshot
        ├── reminders.py    persistent reminders + scheduler
        ├── memory.py       long-term fact storage
        ├── code.py         read/write files, run shell (safety-checked)
        ├── winget.py       install/uninstall/search apps
        ├── vision.py       screenshot + Claude Vision
        ├── whatsapp.py     send WhatsApp Web messages
        └── gmail.py        read inbox, search, send email
```

## Safety notes

- **Destructive actions** (shutdown, sleep, send WhatsApp/email, install/uninstall apps, run shell)
  are gated by verbal confirmation in the system prompt — Jarvis will read back what it's about
  to do before doing it.
- **Shell commands** matching known-dangerous patterns (`rm -rf /`, `format c:`, fork bombs, etc.)
  are refused at the tool level even if Claude tries to run them.
- **Mic is always listening for the wake word.** Audio is processed locally by Porcupine — nothing
  leaves your machine until the wake word fires.

## Troubleshooting

- **"No module named X"** — activate the venv: `.\.venv\Scripts\Activate.ps1`
- **Mic not working** — Windows Settings → Privacy → Microphone → allow
- **Wake word not triggering** — speak clearly; or swap the keyword in
  [jarvis/voice/wake.py](jarvis/voice/wake.py) (Porcupine has built-in `alexa`, `computer`,
  `hey google`, `ok google`, etc.)
- **Whisper is slow** — set `WHISPER_MODEL=tiny` in `.env`
- **Tamil voice sounds robotic** — try `TTS_VOICE_TAMIL=ta-IN-PallaviNeural` in `.env`
- **Gmail token expired** — delete `data/gmail_token.json`, run again, re-auth in browser
- **"Refusing dangerous command"** — Jarvis blocked a risky shell command. This is by design.
