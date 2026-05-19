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
- Use the `remember` tool to save useful facts the user shares (name, preferences, important
  numbers, recurring tasks). Use `recall` when relevant.

Current local time: {now}

What you remember about the user:
{memory}
"""


def _tool(name: str, description: str, properties: dict, required: list | None = None) -> dict:
    params: dict = {"type": "object", "properties": properties}
    if required:
        params["required"] = required
    return {"name": name, "description": description, "parameters": params}


TOOLS: list[dict] = [
    # --- apps / web ---
    _tool("open_app", "Open an app or website by friendly name (chrome, youtube, whatsapp, vscode, notepad, spotify, etc).",
          {"name": {"type": "string"}}, ["name"]),
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
]

TOOL_HANDLERS: dict[str, Any] = {
    "open_app": lambda i: t_apps.open_app(i["name"]),
    "open_website": lambda i: t_apps.open_website(i["url"]),
    "web_search": lambda i: t_apps.web_search(i["query"]),
    "play_on_youtube": lambda i: t_apps.play_on_youtube(i["query"]),
    "add_reminder": lambda i, lang="en": t_reminders.add_reminder(
        i["text"], i["when"], lang, i.get("recurrence", "once")
    ),
    "list_reminders": lambda i: t_reminders.list_reminders(),
    "delete_reminder": lambda i: t_reminders.delete_reminder(i["reminder_id"]),
    "volume_up": lambda i: t_system.volume_up(i.get("steps", 5)),
    "volume_down": lambda i: t_system.volume_down(i.get("steps", 5)),
    "mute_toggle": lambda i: t_system.mute_toggle(),
    "lock_pc": lambda i: t_system.lock_pc(),
    "sleep_pc": lambda i: t_system.sleep_pc(),
    "shutdown_pc": lambda i: t_system.shutdown_pc(i.get("seconds", 30)),
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
    "run_shell": lambda i: t_code.run_shell(i["command"], i.get("timeout", 30)),
    "winget_search": lambda i: t_winget.winget_search(i["query"]),
    "winget_install": lambda i: t_winget.winget_install(i["package_id"]),
    "winget_uninstall": lambda i: t_winget.winget_uninstall(i["package_id"]),
    "describe_screen": lambda i: t_vision.describe_screen(i.get("question", "")),
    "send_whatsapp": lambda i: t_whatsapp.send_whatsapp(i["recipient"], i["message"]),
    "list_whatsapp_chats": lambda i: t_whatsapp.list_recent_chats(i.get("count", 10)),
    "read_whatsapp_chat": lambda i: t_whatsapp.read_chat(i["name"], i.get("count", 10)),
    "list_inbox": lambda i: t_gmail.list_inbox(i.get("max_results", 5)),
    "search_emails": lambda i: t_gmail.search_emails(i["query"], i.get("max_results", 5)),
    "send_email": lambda i: t_gmail.send_email(i["to"], i["subject"], i["body"]),
    "daily_briefing": lambda i: t_briefing.daily_briefing(),
}


MAX_HISTORY_MESSAGES = 40


class Brain:
    def __init__(self, client: LLMClient | None = None) -> None:
        self.client: LLMClient = client or make_llm_client()
        self.history: list = []

    def _system(self) -> str:
        mem = t_memory.memory_summary_for_prompt() or "(nothing yet)"
        return SYSTEM_PROMPT.format(
            now=_dt.datetime.now().strftime("%A %d %B %Y, %I:%M %p"),
            memory=mem,
        )

    def _exec_tool(self, name: str, args: dict, lang: str) -> str:
        fn = TOOL_HANDLERS.get(name)
        if not fn:
            return f"Unknown tool: {name}"
        try:
            if name == "add_reminder":
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
