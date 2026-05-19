# Jarvis Plugins

Drop a `.py` file into this folder and Jarvis will auto-load it the next time the brain starts.

## Plugin contract

Each plugin file must define **two module-level names**:

```python
TOOLS = [
    {
        "name": "my_tool",
        "description": "What it does — used by the LLM to decide when to call it.",
        "parameters": {
            "type": "object",
            "properties": {
                "arg1": {"type": "string"},
            },
            "required": ["arg1"],
        },
    },
]

def my_tool_handler(args: dict) -> str:
    return f"Processed: {args['arg1']}"

HANDLERS = {
    "my_tool": my_tool_handler,
}
```

Optional: a `setup()` function called once on load (good for caching HTTP sessions, etc.).

## Rules

- Tool names must be unique. If you try to shadow a built-in tool, your version is skipped with a warning.
- Errors during plugin load are logged but never crash Jarvis.
- Return a **plain string** from your handler — that's what gets sent back to the LLM.
- Keep the JSON-schema in `parameters` simple: `string`, `integer`, `boolean` types work best with current LLMs.

## Examples shipped with the project

- [`weather.py`](weather.py) — fetches current weather + 3-day forecast from `wttr.in` (no API key).

## Distribute

Plugins are just Python. Share them as gists, repos, or paste-and-save.
