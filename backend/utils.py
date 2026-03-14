"""
Shared utility helpers for LocalVoiceAI backend.
"""
import json
import re


def extract_tool_call(text: str) -> dict | None:
    """Extract a tool_call JSON object from LLM response text.

    The LLM is expected to output a JSON object of the form::

        {"tool_call": {"tool": "tool_name", "args": {...}}}

    This function scans for balanced JSON objects in *text* and returns the
    first one that contains a ``tool_call`` key, or ``None`` if no such
    object is found.
    """
    try:
        for match in re.finditer(r'\{', text):
            start = match.start()
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i + 1]
                        try:
                            parsed = json.loads(candidate)
                            if "tool_call" in parsed:
                                return parsed["tool_call"]
                        except json.JSONDecodeError:
                            pass
                        break
    except Exception:
        pass
    return None
