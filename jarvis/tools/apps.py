"""Launch apps and websites on Windows."""
import os
import subprocess
import webbrowser
from urllib.parse import quote_plus

# Friendly aliases -> Windows executables / commands
APP_ALIASES: dict[str, str] = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "paint": "mspaint.exe",
    "vscode": "code.cmd",
    "vs code": "code.cmd",
    "visual studio code": "code.cmd",
    "settings": "ms-settings:",
    "whatsapp": "https://web.whatsapp.com",
    "youtube": "https://youtube.com",
    "gmail": "https://mail.google.com",
    "spotify": "spotify.exe",
}


def open_app(name: str) -> str:
    """Open an app by friendly name or executable."""
    target = APP_ALIASES.get(name.lower().strip(), name)
    try:
        if target.startswith(("http://", "https://", "ms-settings:")):
            webbrowser.open(target) if target.startswith("http") else os.startfile(target)
        else:
            subprocess.Popen(target, shell=True)
        return f"Opened {name}."
    except Exception as e:
        return f"Could not open {name}: {e}"


def open_website(url: str) -> str:
    """Open a URL in default browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        webbrowser.open(url)
        return f"Opened {url}."
    except Exception as e:
        return f"Could not open {url}: {e}"


def web_search(query: str) -> str:
    """Open a Google search for the query."""
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searched for: {query}"


def play_on_youtube(query: str) -> str:
    """Open the first YouTube search result page."""
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    webbrowser.open(url)
    return f"Opened YouTube search for: {query}"
