"""Autonomous agent — completes a whole multi-step goal on its own.

Unlike Brain.think() (one conversational turn, ~6 tool steps), the Agent:
  - Gets a dedicated "complete this task autonomously" system prompt
  - Plans, then executes step by step using the full tool registry
  - Sees tool results and self-corrects on failure
  - Runs more steps (default 12) with a hard cap + token-aware bailout
  - Emits progress so the GUI/console can show what it's doing

It reuses the Brain's LLM client + TOOLS + TOOL_HANDLERS, but keeps its OWN
short-lived message history so the main conversation stays clean.
"""
from __future__ import annotations
from typing import Callable

AGENT_SYSTEM = """You are Jarvis operating in AUTONOMOUS AGENT mode.

You are given a GOAL and must complete it end-to-end by calling tools, one or more
per step, observing the results, and adapting. You have the user's full tool set
(open apps, files, web search/research, screen vision + clicking, type/keys, email,
calendar, reminders, etc.).

How to work:
1. Briefly PLAN the steps in your head (don't over-explain).
2. Execute with tools. Prefer concrete tool calls over describing intentions.
3. After each tool result, decide the next action. If a step fails, try a different
   approach rather than repeating the same call.
4. For UI tasks, use screen vision (describe_screen / find_on_screen) to check state,
   then click_on_screen / type_text / press_keys to act.
5. STOP and produce a final summary when the goal is achieved OR genuinely blocked.

Safety:
- Do NOT send emails/messages, delete files, uninstall, or shut down without it being
  an explicit part of the goal. If the goal is ambiguous on a destructive action, stop
  and report what you'd do instead.
- Keep going without asking for confirmation for non-destructive steps — you are autonomous.

When done, reply with a short plain-text summary of what you accomplished (no tool call).
Current local time: {now}
"""


class Agent:
    def __init__(self, brain) -> None:
        # Reuse the brain's client + tool registry.
        self.brain = brain

    def run(self, goal: str, max_steps: int = 12,
            progress: Callable[[str], None] | None = None) -> str:
        import datetime as _dt
        from . import brain as _b   # TOOLS + TOOL_HANDLERS live here

        def emit(msg: str):
            if progress:
                try:
                    progress(msg)
                except Exception:
                    pass

        client = self.brain.client
        # Exclude meta/agent tools so the agent can't recursively invoke itself.
        excluded = {"accomplish", "plan_task"}
        agent_tools = [t for t in _b.TOOLS if t["name"] not in excluded]
        system = AGENT_SYSTEM.format(now=_dt.datetime.now().strftime("%A %d %B %Y, %I:%M %p"))
        history = [client.make_user_message(f"GOAL: {goal}")]

        emit(f"[agent] starting: {goal}")
        steps_taken = 0
        try:
            for step in range(max_steps):
                response = client.chat(system, history, agent_tools)
                history.append(client.make_assistant_message(response))

                if not response.tool_calls:
                    final = response.text or "Task finished."
                    emit(f"[agent] done after {steps_taken} action(s)")
                    return final

                results = []
                for tc in response.tool_calls:
                    steps_taken += 1
                    emit(f"[agent] step {steps_taken}: {tc.name}({_short(tc.arguments)})")
                    result = self.brain._exec_tool(tc.name, tc.arguments, "en")
                    results.append((tc.id, str(result)))

                tool_msg = client.make_tool_results(results)
                if isinstance(tool_msg, list):
                    history.extend(tool_msg)
                else:
                    history.append(tool_msg)

            emit("[agent] hit step limit")
            # Ask for a wrap-up summary without more tools.
            history.append(client.make_user_message(
                "You've reached the step limit. Summarize what you accomplished and what remains."
            ))
            wrap = client.chat(system, history, [])
            return (wrap.text or "Reached step limit.").strip()
        except Exception as e:
            return f"Agent stopped on error: {e}"


def _short(args: dict, limit: int = 80) -> str:
    s = ", ".join(f"{k}={v}" for k, v in (args or {}).items())
    return s if len(s) <= limit else s[:limit] + "..."


def accomplish(goal: str, max_steps: int = 12) -> str:
    """Entry point used as a brain tool. Spins a fresh Agent that shares the brain's client."""
    from .brain import Brain
    # A lightweight brain instance reuses the configured client + tool registry.
    agent = Agent(Brain())
    return agent.run(goal, max_steps=max_steps,
                     progress=lambda m: print(m))
