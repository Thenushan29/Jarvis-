"""Persistent reminders + background scheduler thread.

Reminders are stored in data/reminders.json as a list of dicts:
    {id, text, due_iso, lang, created_iso, fired}
"""
import json
import threading
import time
import uuid
import datetime as _dt
from typing import Callable

from ..config import REMINDERS_FILE

_lock = threading.Lock()


def _load() -> list[dict]:
    if not REMINDERS_FILE.exists():
        return []
    try:
        return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    REMINDERS_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_due(when: str) -> _dt.datetime | None:
    """Parse a natural-language or ISO datetime.

    Supports: 'YYYY-MM-DD HH:MM', 'YYYY-MM-DDTHH:MM', 'in 10 minutes', 'in 2 hours',
    'tomorrow 9am', 'today 6pm'.
    """
    when = when.strip().lower()
    now = _dt.datetime.now()

    # ISO-ish
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return _dt.datetime.strptime(when, fmt)
        except ValueError:
            pass

    # "in N minutes/hours/days"
    if when.startswith("in "):
        try:
            parts = when.split()
            n = int(parts[1])
            unit = parts[2]
            if "min" in unit:
                return now + _dt.timedelta(minutes=n)
            if "hour" in unit:
                return now + _dt.timedelta(hours=n)
            if "day" in unit:
                return now + _dt.timedelta(days=n)
            if "sec" in unit:
                return now + _dt.timedelta(seconds=n)
        except Exception:
            pass

    # "today 6pm" / "tomorrow 9am" / "tomorrow 09:30" / bare "tomorrow"
    base = None
    rest = when
    if when.startswith("tomorrow"):
        base = now + _dt.timedelta(days=1)
        rest = when.replace("tomorrow", "").strip()
    elif when.startswith("today"):
        base = now
        rest = when.replace("today", "").strip()

    if base is not None:
        if not rest:
            # "tomorrow" with no time -> default to 9 AM. Reasonable for a morning reminder.
            return _dt.datetime.combine(base.date(), _dt.time(9, 0))
        for fmt in ("%I%p", "%I %p", "%I:%M%p", "%I:%M %p", "%H:%M"):
            try:
                t = _dt.datetime.strptime(rest, fmt).time()
                return _dt.datetime.combine(base.date(), t)
            except ValueError:
                pass

    return None


def add_reminder(text: str, when: str, lang: str = "en") -> str:
    due = _parse_due(when)
    if due is None:
        return (f"Sorry, I couldn't parse the time '{when}'. "
                "Try formats like '2026-05-17 09:30', 'in 30 minutes', or 'tomorrow 9am'.")
    item = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "due_iso": due.isoformat(timespec="seconds"),
        "lang": lang,
        "created_iso": _dt.datetime.now().isoformat(timespec="seconds"),
        "fired": False,
    }
    with _lock:
        items = _load()
        items.append(item)
        _save(items)
    return f"Reminder set for {due.strftime('%a %d %b %I:%M %p')} — {text}"


def list_reminders(include_fired: bool = False) -> str:
    items = _load()
    if not include_fired:
        items = [r for r in items if not r.get("fired")]
    if not items:
        return "You have no pending reminders."
    items.sort(key=lambda r: r["due_iso"])
    lines = []
    for r in items:
        due = _dt.datetime.fromisoformat(r["due_iso"])
        lines.append(f"- [{r['id']}] {due.strftime('%a %d %b %I:%M %p')}: {r['text']}")
    return "Pending reminders:\n" + "\n".join(lines)


def delete_reminder(reminder_id: str) -> str:
    with _lock:
        items = _load()
        before = len(items)
        items = [r for r in items if r["id"] != reminder_id]
        _save(items)
    return "Reminder deleted." if len(items) < before else f"No reminder with id {reminder_id}."


class ReminderScheduler(threading.Thread):
    """Background thread that fires due reminders via a callback."""

    def __init__(self, on_fire: Callable[[dict], None], check_every: float = 20.0):
        super().__init__(daemon=True)
        self.on_fire = on_fire
        self.check_every = check_every
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                print(f"[scheduler] error: {e}")
            self._stop.wait(self.check_every)

    def _tick(self) -> None:
        now = _dt.datetime.now()
        with _lock:
            items = _load()
            changed = False
            for r in items:
                if r.get("fired"):
                    continue
                due = _dt.datetime.fromisoformat(r["due_iso"])
                if due <= now:
                    try:
                        self.on_fire(r)
                    except Exception as e:
                        print(f"[scheduler] on_fire failed: {e}")
                    r["fired"] = True
                    changed = True
            if changed:
                _save(items)

    def stop(self) -> None:
        self._stop.set()
