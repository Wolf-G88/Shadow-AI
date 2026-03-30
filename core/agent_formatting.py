"""
Lightweight formatting helpers for Agent Mode replies.
"""

import re
from typing import List

from core.shell_safety import extract_bang_commands


NUMBERED_PATTERN = re.compile(r"^\s*(?:\d+\.|[-*])\s+(.+?)\s*$")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


def _clean_line(line: str) -> str:
    cleaned = re.sub(r"\s+", " ", (line or "").strip())
    return cleaned.strip("-* ").strip()


def extract_agent_steps(text: str, max_steps: int = 5) -> List[str]:
    """Extract a compact list of actionable steps from freeform agent text."""
    if not text:
        return []

    steps = []
    seen = set()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        match = NUMBERED_PATTERN.match(line)
        if match:
            step = _clean_line(match.group(1))
            if step and step not in seen:
                steps.append(step)
                seen.add(step)

    if steps:
        return steps[:max_steps]

    flattened = " ".join(lines)
    for sentence in SENTENCE_SPLIT_PATTERN.split(flattened):
        step = _clean_line(sentence)
        if not step:
            continue
        if step.startswith("!") or step.startswith("["):
            continue
        if len(step) < 12:
            continue
        if step not in seen:
            steps.append(step)
            seen.add(step)
        if len(steps) >= max_steps:
            break

    return steps


def format_agent_reply(text: str) -> str:
    """
    Format a freeform agent reply into clearer sections when possible.

    Keeps the output lightweight and avoids rewriting when the reply is already
    obviously structured.
    """
    text = (text or "").strip()
    if not text:
        return text

    commands = extract_bang_commands(text)
    steps = extract_agent_steps(text)

    has_explicit_sections = "Plan:" in text or "Suggested Commands:" in text or "[Action Review]" in text
    if has_explicit_sections:
        return text

    sections = []
    if steps:
        plan_lines = ["Plan:"]
        for index, step in enumerate(steps, start=1):
            plan_lines.append(f"{index}. {step}")
        sections.append("\n".join(plan_lines))
    else:
        sections.append(text)

    if commands:
        command_lines = ["Suggested Commands:"]
        for command in commands:
            command_lines.append(f"- `!{command}`")
        sections.append("\n".join(command_lines))
    elif not steps:
        sections.append("Next Step:\n1. Review the request and choose the safest local action.")

    return "\n\n".join(section.strip() for section in sections if section.strip())
