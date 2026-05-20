"""Provider-agnostic brain: takes user text, plans, calls tools, returns spoken reply.

Uses an LLMClient (see jarvis/llm/) so users can swap providers via .env
without changing this file. Long-term memory is injected into the system prompt.
"""
from __future__ import annotations
import datetime as _dt
from typing import Any

from .llm import make_llm_client, LLMClient
from .tools import apps as t_apps
from .tools import system as t_system
from .tools import reminders as t_reminders
from .tools import memory as t_memory
from .tools import code as t_code
from .tools import winget as t_winget
from .tools import vision as t_vision
from .tools import whatsapp as t_whatsapp
from .tools import gmail as t_gmail
from .tools import briefing as t_briefing
from .tools import notes as t_notes
from .tools import clipboard as t_clipboard
from .tools import translate as t_translate
from .tools import file_search as t_file_search
from .tools import calendar_gcal as t_calendar
from .tools import recall_similar as t_recall
from .tools import web_fetch as t_web
from .tools import news as t_news
from .tools import document as t_doc
from .tools import skills as t_skills
from .tools import python_exec as t_pyexec
from .tools import image_gen as t_img
from .tools import file_ops as t_fileops
from .tools import convert as t_convert
from .tools import web_search_real as t_websearch
from .tools import ocr as t_ocr
from .tools import quotes as t_quotes
from .tools import automation as t_auto
from .tools import windows_mgmt as t_win
from .tools import timer as t_timer
from .tools import research as t_research
from .tools import vision_click as t_vclick
from .tools import email_draft as t_edraft
from .tools import planner as t_planner
from .plugins_loader import load_plugins, reserved_names_check
from .personality import get_guidance as _personality_guidance
from . import settings as _settings

SYSTEM_PROMPT = """You are Jarvis, a personal voice assistant for the user on their Windows PC.

Rules:
- You can hear and speak in BOTH Tamil and English. Reply in the SAME language the user just spoke.
- Keep voice replies SHORT — 1 to 2 sentences. This is voice, not chat.
- Prefer using a tool over describing what you would do.
- Always confirm what you did in one short sentence so the user hears it.
- Never invent results. If a tool fails, say so honestly.
- For DESTRUCTIVE actions (shutdown, sleep, delete files, uninstall, run risky shell commands,
  send emails or WhatsApp messages), briefly confirm verbally first — unless the user already
  said a confirmation word like "yes", "do it", "go", "okay", or "seri" (Tamil).
- For sending messages (WhatsApp/email) ALWAYS read back the recipient + body, then wait
  for confirmation before actually sending.

LEARN ABOUT THE USER — IMPORTANT:
- Proactively call the `remember` tool whenever the user shares a fact about themselves:
  name, age, birthday, family members' names/phones, work, location, preferences (foods,
  music, shows), habits, schedules, goals, allergies, or any recurring identifier.
- Use short kebab-case keys (e.g., "user-name", "amma-phone", "morning-routine").
- When the user asks something that might be in past conversations, call `recall_similar` first.
- Use `recall` to look up specific saved facts when relevant.

Personality / tone:
{personality}

Current local time: {now}

What you already remember about the user:
{memory}
"""


def _tool(name: str, description: str, properties: dict, required: list | None = None) -> dict:
    # Strip 'default' from property declarations — Python handlers already use
    # .get(key, default), and including JSON-Schema 'default' makes some models
    # (notably Llama via Groq) wrap integer args as strings (e.g. "25" instead of 25),
    # which Groq's strict schema validator then rejects.
    cleaned_props = {k: {kk: vv for kk, vv in v.items() if kk != "default"}
                     for k, v in properties.items()}
    params: dict = {"type": "object", "properties": cleaned_props}
    if required:
        params["required"] = required
    return {"name": name, "description": description, "parameters": params}


def _int(value, default: int) -> int:
    """Coerce tool arguments to int (defensive against models that send '25' instead of 25)."""
    try:
        return int(value) if value is not None and value != "" else default
    except (TypeError, ValueError):
        return default


def _set_personality(personality_id: str) -> str:
    """Switch Jarvis's tone for future replies — persists across sessions."""
    from .personality import PERSONALITY_PRESETS
    pid = (personality_id or "").lower().strip()
    if pid not in PERSONALITY_PRESETS:
        return (f"Unknown personality '{personality_id}'. Choose from: "
                f"{', '.join(PERSONALITY_PRESETS.keys())}")
    _settings.save({"personality": pid})
    return f"Personality switched to '{pid}'. New tone applies to the next reply."


TOOLS: list[dict] = [
    # --- apps / web ---
    _tool("open_app", "Open ANY installed app or website by name. Searches the full Start-menu + "
                      "Microsoft Store app list, so it works for apps beyond the common ones.",
          {"name": {"type": "string"}}, ["name"]),
    _tool("list_apps", "List installed apps on this PC, optionally filtered by a search term.",
          {"query": {"type": "string"}, "limit": {"type": "integer"}}),
    _tool("refresh_apps", "Rebuild the installed-app index (use after installing new software).", {}),
    _tool("open_website", "Open a URL in the default browser.",
          {"url": {"type": "string"}}, ["url"]),
    _tool("web_search", "Open Google search results for the query.",
          {"query": {"type": "string"}}, ["query"]),
    _tool("play_on_youtube", "Open YouTube search results for the query.",
          {"query": {"type": "string"}}, ["query"]),

    # --- reminders ---
    _tool("add_reminder",
          "Add a reminder. 'when' accepts 'YYYY-MM-DD HH:MM', 'in 30 minutes', 'in 2 hours', "
          "'tomorrow 9am', 'today 6pm', or a day-of-week like 'monday 9am'. "
          "'recurrence' is one of: once (default) | daily | weekly | weekdays | monthly | yearly.",
          {"text": {"type": "string"},
           "when": {"type": "string"},
           "recurrence": {"type": "string", "default": "once"}},
          ["text", "when"]),
    _tool("list_reminders", "List pending reminders.", {}),
    _tool("delete_reminder", "Delete a reminder by short id.",
          {"reminder_id": {"type": "string"}}, ["reminder_id"]),

    # --- system ---
    _tool("volume_up", "Increase volume.", {"steps": {"type": "integer", "default": 5}}),
    _tool("volume_down", "Decrease volume.", {"steps": {"type": "integer", "default": 5}}),
    _tool("mute_toggle", "Toggle mute.", {}),
    _tool("lock_pc", "Lock the PC.", {}),
    _tool("sleep_pc", "Put PC to sleep. Destructive — confirm first.", {}),
    _tool("shutdown_pc", "Shutdown PC. Destructive — confirm first.",
          {"seconds": {"type": "integer", "default": 30}}),
    _tool("cancel_shutdown", "Cancel pending shutdown.", {}),
    _tool("screenshot", "Save a screenshot to Desktop.", {}),
    _tool("current_time", "Get the current local time.", {}),

    # --- media keys ---
    _tool("media_play_pause", "Play or pause whatever is currently playing music or video (Spotify, YouTube, etc).", {}),
    _tool("media_next", "Skip to the next track.", {}),
    _tool("media_prev", "Go to the previous track.", {}),
    _tool("media_stop", "Stop media playback.", {}),

    # --- long-term memory ---
    _tool("remember",
          "Save a fact for later sessions. Use short kebab-case keys (e.g., 'birthday', 'amma-phone').",
          {"key": {"type": "string"}, "value": {"type": "string"}}, ["key", "value"]),
    _tool("recall", "Recall a saved fact by key, or list all if no key.", {"key": {"type": "string"}}),
    _tool("forget", "Delete a saved fact by key.", {"key": {"type": "string"}}, ["key"]),

    # --- code / files / shell ---
    _tool("read_file", "Read a text file from disk.", {"path": {"type": "string"}}, ["path"]),
    _tool("write_file", "Write content to a file (overwrites).",
          {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    _tool("append_file", "Append content to a file.",
          {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    _tool("list_dir", "List the contents of a directory.", {"path": {"type": "string", "default": "."}}),
    _tool("run_shell",
          "Run a PowerShell command on Windows. Dangerous commands are refused. Confirm with user first.",
          {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 30}}, ["command"]),

    # --- winget ---
    _tool("winget_search", "Search winget for an app.", {"query": {"type": "string"}}, ["query"]),
    _tool("winget_install", "Install an app by winget package ID. Confirm with user first.",
          {"package_id": {"type": "string"}}, ["package_id"]),
    _tool("winget_uninstall", "Uninstall an app by winget package ID. Confirm with user first.",
          {"package_id": {"type": "string"}}, ["package_id"]),

    # --- vision ---
    _tool("describe_screen",
          "Take a screenshot and ask the vision model what's on it.",
          {"question": {"type": "string"}}),

    # --- whatsapp ---
    _tool("send_whatsapp",
          "Send a WhatsApp message via WhatsApp Web. Recipient can be a contact name OR phone with country code. Confirm first.",
          {"recipient": {"type": "string"}, "message": {"type": "string"}}, ["recipient", "message"]),
    _tool("list_whatsapp_chats", "List the most recent WhatsApp chats with last-message preview.",
          {"count": {"type": "integer", "default": 10}}),
    _tool("read_whatsapp_chat",
          "Open a WhatsApp chat by contact name and read the last N messages.",
          {"name": {"type": "string"}, "count": {"type": "integer", "default": 10}}, ["name"]),

    # --- gmail ---
    _tool("list_inbox", "List the latest N inbox emails.", {"max_results": {"type": "integer", "default": 5}}),
    _tool("search_emails", "Search Gmail. Examples: 'from:boss', 'is:unread', 'subject:invoice newer_than:7d'.",
          {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}}, ["query"]),
    _tool("send_email", "Send an email via Gmail. Confirm recipient + body with user first.",
          {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
          ["to", "subject", "body"]),

    # --- daily briefing ---
    _tool("daily_briefing",
          "Give a short voice-friendly daily briefing: greeting, today's reminders, "
          "and unread emails. Use when the user says 'good morning', 'brief me', "
          "'what's my day', or asks for a summary.",
          {}),

    # --- semantic recall + personality ---
    _tool("recall_similar",
          "Search the user's past conversations, notes, and saved memories for anything "
          "relevant to a query. Use when the user references something that might be in "
          "history ('what did I say about X?', 'I told you something about...').",
          {"query": {"type": "string"}, "k": {"type": "integer"}}, ["query"]),
    _tool("set_personality",
          "Change Jarvis's tone of voice. personality_id is one of: "
          "jarvis | casual | concise | witty | professional. "
          "Use when the user says 'be more X' or 'switch to Y mode'.",
          {"personality_id": {"type": "string"}}, ["personality_id"]),

    # --- v6: web + news + documents + skills + sandbox ---
    _tool("fetch_url",
          "Fetch a URL, extract the readable text, and answer a question about it "
          "(or summarize if no question). Use for 'what's on this page', "
          "'summarize this article', 'what does Wikipedia say about X'.",
          {"url": {"type": "string"}, "question": {"type": "string"}}, ["url"]),
    _tool("news_briefing",
          "Get top news headlines. Optional `topic` filters to a subject (e.g. 'AI', "
          "'Tamil Nadu', 'climate'). With no topic, returns Hacker News top + general world headlines.",
          {"topic": {"type": "string"}, "count": {"type": "integer"}}),
    _tool("ask_document",
          "Read a local file (PDF or text) and answer a question about its contents. "
          "Use when user asks 'what's in this file', 'summarize this PDF', 'what does X say about Y'.",
          {"path": {"type": "string"}, "question": {"type": "string"}}, ["path"]),
    _tool("create_skill",
          "Save a sequence of tool calls as a named skill the user can replay later. "
          "Steps is a list of {tool, args} dicts. Use when user says 'create a skill called X that does Y, Z'.",
          {"name": {"type": "string"}, "steps": {"type": "array"}}, ["name", "steps"]),
    _tool("run_skill",
          "Replay a previously saved skill by name. Use when user says 'run my morning routine' etc.",
          {"name": {"type": "string"}}, ["name"]),
    _tool("list_skills", "List all saved skill macros.", {}),
    _tool("delete_skill", "Delete a saved skill by name.",
          {"name": {"type": "string"}}, ["name"]),
    _tool("run_python",
          "Execute a Python snippet in an isolated subprocess for calculations / data "
          "manipulation / date math. Has a hard timeout. Use for things the LLM can't "
          "compute reliably (precise arithmetic, regex, date arithmetic).",
          {"code": {"type": "string"}, "timeout": {"type": "integer"}}, ["code"]),

    # ===== v7: image gen / file ops / convert / web search / OCR / quotes =====
    _tool("generate_image",
          "Generate an image from a text prompt (saves to Desktop). Uses Pollinations.ai (free).",
          {"prompt": {"type": "string"},
           "width": {"type": "integer"}, "height": {"type": "integer"}}, ["prompt"]),

    _tool("copy_file",   "Copy a file or directory. Confirm with user first.",
          {"src": {"type": "string"}, "dst": {"type": "string"}}, ["src", "dst"]),
    _tool("move_file",   "Move (or rename across folders) a file. Confirm with user first.",
          {"src": {"type": "string"}, "dst": {"type": "string"}}, ["src", "dst"]),
    _tool("rename_file", "Rename a file in place. Confirm with user first.",
          {"path": {"type": "string"}, "new_name": {"type": "string"}}, ["path", "new_name"]),
    _tool("make_dir",    "Create a directory (and any missing parents).",
          {"path": {"type": "string"}}, ["path"]),
    _tool("delete_file",
          "Delete a file. By default sends to Recycle Bin (reversible). "
          "Set permanent=true ONLY when the user explicitly says 'permanently delete'.",
          {"path": {"type": "string"}, "permanent": {"type": "boolean"}}, ["path"]),

    _tool("convert_currency",
          "Convert an amount from one currency to another using live FX rates.",
          {"amount": {"type": "number"},
           "from_currency": {"type": "string"}, "to_currency": {"type": "string"}},
          ["amount", "from_currency", "to_currency"]),
    _tool("convert_unit",
          "Convert between physical units. Supports length, mass, time, volume, temperature.",
          {"amount": {"type": "number"},
           "from_unit": {"type": "string"}, "to_unit": {"type": "string"}},
          ["amount", "from_unit", "to_unit"]),

    _tool("web_search_real",
          "Run a real web search and return top result titles + URLs + snippets. "
          "Different from `web_search` which only opens a browser tab.",
          {"query": {"type": "string"}, "max_results": {"type": "integer"}}, ["query"]),

    _tool("ocr_screen",
          "Take a screenshot and extract all visible text from it. Optional 'question' "
          "narrows the output to lines matching the question's keywords.",
          {"question": {"type": "string"}}),
    _tool("ocr_image",
          "Extract text from a local image file.",
          {"path": {"type": "string"}, "question": {"type": "string"}}, ["path"]),

    _tool("stock_quote",
          "Get current stock price + day change. Examples: AAPL, MSFT, TCS.NS, INFY.NS.",
          {"symbol": {"type": "string"}}, ["symbol"]),
    _tool("cricket_score",
          "Live cricket scores from cricbuzz. Optional `query` filters (e.g. 'India', 'IPL').",
          {"query": {"type": "string"}}),

    # ===== v8: screen automation / windows / timers =====
    _tool("type_text",
          "Type text into whatever currently has keyboard focus. Confirm with user before "
          "typing into anything sensitive.",
          {"text": {"type": "string"}}, ["text"]),
    _tool("press_keys",
          "Press a key or hotkey combo. Examples: 'enter', 'ctrl+s', 'alt+tab', 'win+d', 'ctrl+c'.",
          {"keys": {"type": "string"}}, ["keys"]),
    _tool("mouse_click",
          "Click the mouse. Provide x,y to click a specific point, or omit to click the current "
          "position. button = left|right|middle. Confirm before clicking.",
          {"x": {"type": "integer"}, "y": {"type": "integer"},
           "button": {"type": "string"}, "clicks": {"type": "integer"}}),
    _tool("scroll", "Scroll the active window. Negative = down, positive = up.",
          {"amount": {"type": "integer"}}),
    _tool("screen_size", "Get the screen resolution.", {}),

    _tool("list_windows", "List the titles of all open windows.", {}),
    _tool("active_window", "Get the title of the currently focused window.", {}),
    _tool("focus_window", "Bring a window to the front by a title substring.",
          {"title": {"type": "string"}}, ["title"]),
    _tool("minimize_window", "Minimize a window by title substring.",
          {"title": {"type": "string"}}, ["title"]),
    _tool("maximize_window", "Maximize a window by title substring.",
          {"title": {"type": "string"}}, ["title"]),
    _tool("close_window", "Close a window by title substring. Confirm with user first.",
          {"title": {"type": "string"}}, ["title"]),

    _tool("set_timer",
          "Set a countdown timer that fires like a reminder. Provide minutes and/or seconds.",
          {"minutes": {"type": "number"}, "seconds": {"type": "number"},
           "label": {"type": "string"}}),

    # ===== v9: agentic — research / vision-click / email drafting =====
    _tool("research",
          "Deep-research a topic: searches the web, reads the top results, and synthesizes "
          "a briefing with sources. Use for 'research X', 'find out about Y', 'compare Z'.",
          {"topic": {"type": "string"}, "depth": {"type": "integer"},
           "save_note": {"type": "boolean"}}, ["topic"]),
    _tool("find_on_screen",
          "Locate a UI element on screen by description and return its coordinates (no click).",
          {"description": {"type": "string"}}, ["description"]),
    _tool("click_on_screen",
          "Find a UI element by description (e.g. 'the blue Submit button', 'the search box') "
          "using screen vision, then click it. Confirm with the user before clicking.",
          {"description": {"type": "string"}, "button": {"type": "string"},
           "double": {"type": "boolean"}}, ["description"]),
    _tool("draft_email_reply",
          "Read a recent email (by Gmail query, default unread) and draft a reply for review. "
          "Does NOT send. `instructions` steers tone/content.",
          {"query": {"type": "string"}, "instructions": {"type": "string"}}),

    # ===== v10: autonomous agent =====
    _tool("accomplish",
          "Autonomously complete a COMPLEX multi-step goal end-to-end (plans, executes many "
          "tools, self-corrects). Use ONLY for genuinely multi-step tasks like 'research X and "
          "save a note', 'open Y, find Z, and do W'. For single actions, call the specific tool "
          "directly instead.",
          {"goal": {"type": "string"}, "max_steps": {"type": "integer"}}, ["goal"]),
    _tool("plan_task",
          "Produce a step-by-step plan for a goal WITHOUT executing it. Use when the user asks "
          "'how would you do X' or wants to review a plan first.",
          {"goal": {"type": "string"}}, ["goal"]),

    # --- notes ---
    _tool("add_note",
          "Save a quick note to the user's notes file. Use when the user says "
          "'take a note', 'remember this', or wants to jot down something they don't "
          "need a reminder for. 'tag' is an optional category like 'idea' or 'todo'.",
          {"text": {"type": "string"}, "tag": {"type": "string", "default": ""}}, ["text"]),
    _tool("list_notes", "List recent notes, optionally filtered by a query.",
          {"max_results": {"type": "integer", "default": 10},
           "query": {"type": "string", "default": ""}}),

    # --- clipboard ---
    _tool("read_clipboard", "Read the current Windows clipboard contents.", {}),
    _tool("write_clipboard", "Replace clipboard contents with the given text.",
          {"text": {"type": "string"}}, ["text"]),
    _tool("append_clipboard", "Append text to the current clipboard contents.",
          {"text": {"type": "string"}}, ["text"]),

    # --- translation ---
    _tool("translate",
          "Translate text into a target language (e.g. 'tamil', 'english', 'hindi'). "
          "Use when user explicitly asks to translate something.",
          {"text": {"type": "string"},
           "target_language": {"type": "string", "default": "english"}}, ["text"]),

    # --- file search ---
    _tool("find_files",
          "Search the user's Desktop / Documents / Downloads for files by name "
          "(substring or glob like '*.pdf') and optionally by content. Use when "
          "user says 'find my resume', 'where is the X file', etc.",
          {"name_pattern": {"type": "string", "default": ""},
           "content_query": {"type": "string", "default": ""},
           "max_results": {"type": "integer", "default": 25}}),

    # --- google calendar ---
    _tool("list_today_events", "List today's events from the user's primary Google Calendar.", {}),
    _tool("list_week_events", "List events for the next 7 days from Google Calendar.", {}),
    _tool("add_calendar_event",
          "Add an event to the user's Google Calendar. start_time accepts "
          "'YYYY-MM-DD HH:MM'. duration_minutes defaults to 60. Confirm with user before adding.",
          {"summary": {"type": "string"},
           "start_time": {"type": "string"},
           "duration_minutes": {"type": "integer", "default": 60},
           "description": {"type": "string", "default": ""},
           "location": {"type": "string", "default": ""}},
          ["summary", "start_time"]),
]

TOOL_HANDLERS: dict[str, Any] = {
    "open_app": lambda i: t_apps.open_app(i["name"]),
    "list_apps": lambda i: __import__("jarvis.tools.app_index", fromlist=["list_apps"]).list_apps(
        i.get("query", ""), _int(i.get("limit"), 30)
    ),
    "refresh_apps": lambda i: __import__("jarvis.tools.app_index", fromlist=["refresh_apps"]).refresh_apps(),
    "open_website": lambda i: t_apps.open_website(i["url"]),
    "web_search": lambda i: t_apps.web_search(i["query"]),
    "play_on_youtube": lambda i: t_apps.play_on_youtube(i["query"]),
    "add_reminder": lambda i, lang="en": t_reminders.add_reminder(
        i["text"], i["when"], lang, i.get("recurrence", "once")
    ),
    "list_reminders": lambda i: t_reminders.list_reminders(),
    "delete_reminder": lambda i: t_reminders.delete_reminder(i["reminder_id"]),
    "volume_up": lambda i: t_system.volume_up(_int(i.get("steps"), 5)),
    "volume_down": lambda i: t_system.volume_down(_int(i.get("steps"), 5)),
    "mute_toggle": lambda i: t_system.mute_toggle(),
    "lock_pc": lambda i: t_system.lock_pc(),
    "sleep_pc": lambda i: t_system.sleep_pc(),
    "shutdown_pc": lambda i: t_system.shutdown_pc(_int(i.get("seconds"), 30)),
    "cancel_shutdown": lambda i: t_system.cancel_shutdown(),
    "screenshot": lambda i: t_system.screenshot(),
    "current_time": lambda i: t_system.current_time(),
    "media_play_pause": lambda i: t_system.media_play_pause(),
    "media_next": lambda i: t_system.media_next(),
    "media_prev": lambda i: t_system.media_prev(),
    "media_stop": lambda i: t_system.media_stop(),
    "remember": lambda i: t_memory.remember(i["key"], i["value"]),
    "recall": lambda i: t_memory.recall(i.get("key")),
    "forget": lambda i: t_memory.forget(i["key"]),
    "read_file": lambda i: t_code.read_file(i["path"]),
    "write_file": lambda i: t_code.write_file(i["path"], i["content"]),
    "append_file": lambda i: t_code.append_file(i["path"], i["content"]),
    "list_dir": lambda i: t_code.list_dir(i.get("path", ".")),
    "run_shell": lambda i: t_code.run_shell(i["command"], _int(i.get("timeout"), 30)),
    "winget_search": lambda i: t_winget.winget_search(i["query"]),
    "winget_install": lambda i: t_winget.winget_install(i["package_id"]),
    "winget_uninstall": lambda i: t_winget.winget_uninstall(i["package_id"]),
    "describe_screen": lambda i: t_vision.describe_screen(i.get("question", "")),
    "send_whatsapp": lambda i: t_whatsapp.send_whatsapp(i["recipient"], i["message"]),
    "list_whatsapp_chats": lambda i: t_whatsapp.list_recent_chats(_int(i.get("count"), 10)),
    "read_whatsapp_chat": lambda i: t_whatsapp.read_chat(i["name"], _int(i.get("count"), 10)),
    "list_inbox": lambda i: t_gmail.list_inbox(_int(i.get("max_results"), 5)),
    "search_emails": lambda i: t_gmail.search_emails(i["query"], _int(i.get("max_results"), 5)),
    "send_email": lambda i: t_gmail.send_email(i["to"], i["subject"], i["body"]),
    "daily_briefing": lambda i: t_briefing.daily_briefing(),
    "recall_similar": lambda i: t_recall.recall_similar(i["query"], _int(i.get("k"), 5)),
    "set_personality": lambda i: _set_personality(i["personality_id"]),
    "fetch_url": lambda i: t_web.fetch_url(i["url"], i.get("question", "")),
    "news_briefing": lambda i: t_news.news_briefing(i.get("topic", ""), _int(i.get("count"), 5)),
    "ask_document": lambda i: t_doc.ask_document(i["path"], i.get("question", "")),
    "create_skill": lambda i: t_skills.create_skill(i["name"], i.get("steps") or []),
    "run_skill": lambda i: t_skills.run_skill(i["name"]),
    "list_skills": lambda i: t_skills.list_skills(),
    "delete_skill": lambda i: t_skills.delete_skill(i["name"]),
    "run_python": lambda i: t_pyexec.run_python(i["code"], _int(i.get("timeout"), 5)),
    # v7
    "generate_image": lambda i: t_img.generate_image(
        i["prompt"], _int(i.get("width"), 1024), _int(i.get("height"), 1024)
    ),
    "copy_file":   lambda i: t_fileops.copy_file(i["src"], i["dst"]),
    "move_file":   lambda i: t_fileops.move_file(i["src"], i["dst"]),
    "rename_file": lambda i: t_fileops.rename_file(i["path"], i["new_name"]),
    "make_dir":    lambda i: t_fileops.make_dir(i["path"]),
    "delete_file": lambda i: t_fileops.delete_file(i["path"], bool(i.get("permanent", False))),
    "convert_currency": lambda i: t_convert.convert_currency(
        i["amount"], i["from_currency"], i["to_currency"]
    ),
    "convert_unit": lambda i: t_convert.convert_unit(
        i["amount"], i["from_unit"], i["to_unit"]
    ),
    "web_search_real": lambda i: t_websearch.web_search(i["query"], _int(i.get("max_results"), 5)),
    "ocr_screen": lambda i: t_ocr.ocr_screen(i.get("question", "")),
    "ocr_image":  lambda i: t_ocr.ocr_image(i["path"], i.get("question", "")),
    "stock_quote": lambda i: t_quotes.stock_quote(i["symbol"]),
    "cricket_score": lambda i: t_quotes.cricket_score(i.get("query", "")),
    "add_note": lambda i: t_notes.add_note(i["text"], i.get("tag", "")),
    "list_notes": lambda i: t_notes.list_notes(_int(i.get("max_results"), 10), i.get("query", "")),
    "read_clipboard": lambda i: t_clipboard.read_clipboard(),
    "write_clipboard": lambda i: t_clipboard.write_clipboard(i["text"]),
    "append_clipboard": lambda i: t_clipboard.append_clipboard(i["text"]),
    "translate": lambda i: t_translate.translate(i["text"], i.get("target_language", "english")),
    "find_files": lambda i: t_file_search.find_files(
        i.get("name_pattern", ""), i.get("content_query", ""), _int(i.get("max_results"), 25)
    ),
    "list_today_events": lambda i: t_calendar.list_today_events(),
    "list_week_events": lambda i: t_calendar.list_week_events(),
    "add_calendar_event": lambda i: t_calendar.add_event(
        i["summary"], i["start_time"], _int(i.get("duration_minutes"), 60),
        i.get("description", ""), i.get("location", "")
    ),
    # v8 — screen automation / windows / timers
    "type_text": lambda i: t_auto.type_text(i["text"]),
    "press_keys": lambda i: t_auto.press_keys(i["keys"]),
    "mouse_click": lambda i: t_auto.mouse_click(
        i.get("x"), i.get("y"), i.get("button", "left"), _int(i.get("clicks"), 1)
    ),
    "scroll": lambda i: t_auto.scroll(_int(i.get("amount"), -500)),
    "screen_size": lambda i: t_auto.screen_size(),
    "list_windows": lambda i: t_win.list_windows(),
    "active_window": lambda i: t_win.active_window(),
    "focus_window": lambda i: t_win.focus_window(i["title"]),
    "minimize_window": lambda i: t_win.minimize_window(i["title"]),
    "maximize_window": lambda i: t_win.maximize_window(i["title"]),
    "close_window": lambda i: t_win.close_window(i["title"]),
    "set_timer": lambda i, lang="en": t_timer.set_timer(
        i.get("minutes", 0), i.get("seconds", 0), i.get("label", "Timer"), lang
    ),
    # v9 — agentic
    "research": lambda i: t_research.research(
        i["topic"], _int(i.get("depth"), 3), bool(i.get("save_note", False))
    ),
    "find_on_screen": lambda i: t_vclick.find_on_screen(i["description"]),
    "click_on_screen": lambda i: t_vclick.click_on_screen(
        i["description"], i.get("button", "left"), bool(i.get("double", False))
    ),
    "draft_email_reply": lambda i: t_edraft.draft_email_reply(
        i.get("query", "is:unread"), i.get("instructions", "")
    ),
    # v10 — autonomous agent
    "accomplish": lambda i: __import__("jarvis.agent", fromlist=["accomplish"]).accomplish(
        i["goal"], _int(i.get("max_steps"), 12)
    ),
    "plan_task": lambda i: t_planner.plan_task(i["goal"]),
}


MAX_HISTORY_MESSAGES = 40


_plugins_loaded_once = False


def _load_plugins_once() -> None:
    """Discover and merge plugins exactly once per process."""
    global _plugins_loaded_once
    if _plugins_loaded_once:
        return
    _plugins_loaded_once = True
    try:
        plugin_tools, plugin_handlers = load_plugins()
        builtin_names = {t["name"] for t in TOOLS}
        plugin_tools = reserved_names_check(builtin_names, plugin_tools)
        if plugin_tools:
            TOOLS.extend(plugin_tools)
            TOOL_HANDLERS.update({
                name: handler for name, handler in plugin_handlers.items()
                if name in {t["name"] for t in plugin_tools}
            })
            print(f"[brain] plugins loaded: +{len(plugin_tools)} tool(s)")
    except Exception as e:
        print(f"[brain] plugin load skipped: {e}")


class Brain:
    def __init__(self, client: LLMClient | None = None) -> None:
        self.client: LLMClient = client or make_llm_client()
        self.history: list = []
        _load_plugins_once()

    def _system(self) -> str:
        mem = t_memory.memory_summary_for_prompt() or "(nothing yet)"
        personality_id = _settings.get("personality", "jarvis")
        return SYSTEM_PROMPT.format(
            now=_dt.datetime.now().strftime("%A %d %B %Y, %I:%M %p"),
            memory=mem,
            personality=_personality_guidance(personality_id),
        )

    def _exec_tool(self, name: str, args: dict, lang: str) -> str:
        fn = TOOL_HANDLERS.get(name)
        if not fn:
            return f"Unknown tool: {name}"
        try:
            if name in ("add_reminder", "set_timer"):
                return fn(args, lang=lang)
            return fn(args)
        except Exception as e:
            return f"Tool '{name}' failed: {e}"

    def _trim_history(self) -> None:
        if len(self.history) <= MAX_HISTORY_MESSAGES:
            return
        drop = len(self.history) - MAX_HISTORY_MESSAGES
        # Walk forward to a safe boundary — never start with an orphan tool response.
        while drop < len(self.history):
            m = self.history[drop]
            role = m.get("role")
            if role == "tool":
                drop += 1
                continue
            if role == "assistant" and self.client.has_unresolved_tool_calls(m):
                drop += 1
                continue
            if role == "user" and isinstance(m.get("content"), list):
                # Anthropic-style tool_result block — skip past it.
                if any((isinstance(b, dict) and b.get("type") == "tool_result") for b in m["content"]):
                    drop += 1
                    continue
            break
        self.history = self.history[drop:]

    def _drop_unresolved_tail(self) -> None:
        if not self.history:
            return
        last = self.history[-1]
        if last.get("role") == "assistant" and self.client.has_unresolved_tool_calls(last):
            self.history.pop()
            if self.history and self.history[-1].get("role") == "user":
                self.history.pop()

    def reset(self) -> None:
        self.history = []

    def think(self, user_text: str, lang: str = "en") -> str:
        """Run one user turn. Handles multi-step tool calling. Returns final spoken reply."""
        self.history.append(self.client.make_user_message(user_text))
        try:
            for _ in range(6):
                response = self.client.chat(self._system(), self.history, TOOLS)
                self.history.append(self.client.make_assistant_message(response))

                if not response.tool_calls:
                    self._trim_history()
                    return response.text or "Done."

                # Execute every tool call from this turn.
                results: list[tuple[str, str]] = []
                for tc in response.tool_calls:
                    result = self._exec_tool(tc.name, tc.arguments, lang)
                    print(f"[tool] {tc.name}({tc.arguments}) -> {str(result)[:200]}")
                    results.append((tc.id, str(result)))

                tool_msg = self.client.make_tool_results(results)
                if isinstance(tool_msg, list):
                    self.history.extend(tool_msg)
                else:
                    self.history.append(tool_msg)

            self._drop_unresolved_tail()
            return "Sorry, I got stuck in a tool loop."
        except Exception:
            self._drop_unresolved_tail()
            raise
