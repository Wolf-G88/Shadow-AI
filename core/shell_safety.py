"""
Shell command safety helpers for Shadow AI.
"""

import os
import re
import shlex
from typing import Dict, List, Optional


SAFE_STARTERS = {
    "ls", "dir", "pwd", "cd", "echo", "cat", "type", "grep", "find", "which",
    "where", "python", "python3", "py", "git", "ollama", "pip", "pip3",
    "uname", "whoami", "id", "env", "printenv", "tree"
}

READONLY_STARTERS = {
    "ls", "pwd", "cat", "type", "grep", "find", "which", "where",
    "uname", "whoami", "id", "env", "printenv", "tree"
}

READONLY_SUBCOMMANDS = {
    "git": {"status", "log", "diff", "show", "rev-parse"},
    "ollama": {"list", "ps", "show"},
    "python": {"--version", "-V", "--help", "-h"},
    "python3": {"--version", "-V", "--help", "-h"},
    "py": {"--version", "-V", "--help", "-h"},
    "pip": {"show", "list", "freeze", "--version", "help"},
    "pip3": {"show", "list", "freeze", "--version", "help"},
}

SHELL_BUILTINS = {"cd"}

CRITICAL_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\bdel\s+/(f|q|s)\b",
    r"\brd\s+/s\s+/q\b",
    r"\bformat\b",
    r"\bmkfs\b",
    r"\bdd\s+if=/dev/zero",
    r"\bwipefs\b",
    r"\bdiskpart\b",
    r"\bvssadmin\s+delete\s+shadows\b",
    r"\bbcdedit\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\bhalt\b",
    r"\bkill\s+-9\s+1\b",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
]

HIGH_PATTERNS = [
    r"\bsudo\b",
    r"\brm\b",
    r"\bdel\b",
    r"\bmv\b",
    r"\bmove\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\breg\s+delete\b",
    r"\btakeown\b",
    r"\bicacls\b",
    r"\bsc\s+config\b",
    r"\bnetsh\b",
]

MEDIUM_PATTERNS = [
    r"\bapt\s+remove\b",
    r"\bpip\s+uninstall\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-fd\b",
    r"\bpower(shell)?\b.+-enc(odedcommand)?\b",
]

SHELL_META_PATTERN = re.compile(r"(&&|\|\||[|;<>`])")
BANG_INLINE_PATTERN = re.compile(r"`(![^`\n]+)`")
BANG_LINE_PATTERN = re.compile(r"(?m)^\s*(![^\n]+)$")


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", (command or "").strip())


def contains_shell_metacharacters(command: str) -> bool:
    return bool(SHELL_META_PATTERN.search(command))


def _result(level: str, reason: str, profile: str, confirm: bool) -> Dict[str, object]:
    return {
        "level": level,
        "reason": reason,
        "profile": profile,
        "confirm": confirm,
    }


def _classify_by_tokens(parts: List[str]) -> Dict[str, object]:
    if not parts:
        return _result("medium", "empty command", "unknown", True)

    cmd_start = parts[0].lower()
    next_arg = parts[1].lower() if len(parts) > 1 else ""

    if cmd_start in READONLY_STARTERS:
        return _result("safe", "read-only inspection command", "readonly", False)

    if cmd_start == "echo":
        return _result("safe", "prints text only", "readonly", False)

    if cmd_start in {"python", "python3", "py"} and next_arg.endswith(".py"):
        return _result("medium", "runs a script which may change system state", "mutating", True)

    if cmd_start in READONLY_SUBCOMMANDS and next_arg in READONLY_SUBCOMMANDS[cmd_start]:
        return _result("safe", "known read-only subcommand", "readonly", False)

    if cmd_start in {"git", "ollama", "pip", "pip3", "python", "python3", "py"}:
        return _result("medium", "tool can change files, packages, or runtime state", "mutating", True)

    if cmd_start in SAFE_STARTERS:
        return _result("medium", "command starter is known but effect is unclear", "unknown", True)

    return _result("medium", "unknown command path", "unknown", True)


def assess_command_risk(command: str) -> Dict[str, object]:
    normalized = normalize_command(command)
    lowered = normalized.lower()

    for pattern in CRITICAL_PATTERNS:
        if re.search(pattern, lowered):
            return _result("critical", "matched critical destructive pattern", "destructive", False)

    if contains_shell_metacharacters(normalized):
        return _result("high", "contains shell chaining or redirection", "shell", True)

    for pattern in HIGH_PATTERNS:
        if re.search(pattern, lowered):
            return _result("high", "modifies files, permissions, or system state", "mutating", True)

    for pattern in MEDIUM_PATTERNS:
        if re.search(pattern, lowered):
            return _result("medium", "changes installed software or repo state", "mutating", True)

    parts = split_command_args(normalized)
    return _classify_by_tokens(parts or [])


def split_command_args(command: str) -> Optional[List[str]]:
    normalized = normalize_command(command)
    if not normalized or contains_shell_metacharacters(normalized):
        return None

    try:
        return shlex.split(normalized, posix=(os.name != "nt"))
    except ValueError:
        return None


def build_exec_plan(command: str) -> Dict[str, object]:
    normalized = normalize_command(command)
    argv = split_command_args(normalized)
    if argv and argv[0].lower() in SHELL_BUILTINS:
        return {"mode": "shell", "argv": None, "command": normalized}
    if argv:
        return {"mode": "direct", "argv": argv, "command": normalized}
    return {"mode": "shell", "argv": None, "command": normalized}


def extract_bang_commands(text: str) -> List[str]:
    """Extract distinct !commands from agent-style text."""
    if not text:
        return []

    found = []

    for match in BANG_INLINE_PATTERN.findall(text):
        command = normalize_command(match[1:])
        if command and command not in found:
            found.append(command)

    for match in BANG_LINE_PATTERN.findall(text):
        command = normalize_command(match[1:])
        if command and command not in found:
            found.append(command)

    return found


def summarize_command_policies(text: str) -> Optional[str]:
    """Build a short policy review block for any !commands in a reply."""
    commands = extract_bang_commands(text)
    if not commands:
        return None

    lines = ["[Action Review]"]
    for command in commands:
        risk = assess_command_risk(command)
        action = "blocked" if risk["level"] == "critical" else ("confirm" if risk["confirm"] else "run")
        lines.append(
            f"- !{command} -> {risk['profile']} | {action} | {risk['reason']}"
        )
    return "\n".join(lines)
