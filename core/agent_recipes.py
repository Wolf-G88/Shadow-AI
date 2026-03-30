"""
Small built-in recipes for common Agent Mode tasks.
"""

import re
from typing import Optional, Dict


def _repo_recipe() -> Dict[str, str]:
    return {
        "name": "repo_review",
        "title": "Repository Review",
        "guidance": (
            "Prefer a fast local inspection flow.\n"
            "1. Inspect repo status and top-level structure first.\n"
            "2. Summarize what the project appears to be.\n"
            "3. Suggest only read-only commands unless the user explicitly asks to modify something.\n"
            "4. If you suggest commands, prefer `!git status`, `!git log --oneline -5`, and `!ls -la` style inspection commands."
        ),
    }


def _file_recipe() -> Dict[str, str]:
    return {
        "name": "file_triage",
        "title": "File Triage",
        "guidance": (
            "Focus on understanding attached or mentioned files.\n"
            "1. Summarize file types and likely purpose.\n"
            "2. Identify the most important file or folder first.\n"
            "3. Prefer read-only inspection suggestions.\n"
            "4. Do not suggest mutating commands unless the user explicitly asks for changes."
        ),
    }


def _env_recipe() -> Dict[str, str]:
    return {
        "name": "environment_check",
        "title": "Environment Check",
        "guidance": (
            "Treat this like a cautious local diagnostics pass.\n"
            "1. Prefer version checks, status commands, and inventory commands first.\n"
            "2. Call out platform assumptions clearly.\n"
            "3. Suggest only read-only commands unless the user explicitly asks to install, remove, or reconfigure something."
        ),
    }


def _debug_recipe() -> Dict[str, str]:
    return {
        "name": "debug_troubleshoot",
        "title": "Debug and Troubleshoot",
        "guidance": (
            "Treat this like a careful debugging pass.\n"
            "1. Start by identifying the concrete symptom, error, or failing behavior.\n"
            "2. Prefer local read-only inspection steps first, such as logs, status, and version checks.\n"
            "3. State the most likely causes in order of confidence.\n"
            "4. If you suggest commands, prefer inspection commands before anything mutating.\n"
            "5. Only suggest changes, installs, or resets after explaining why they are needed."
        ),
    }


def _audit_recipe() -> Dict[str, str]:
    return {
        "name": "project_audit",
        "title": "Project Audit",
        "guidance": (
            "Treat this like a high-signal project audit.\n"
            "1. Map the main parts of the project first.\n"
            "2. Call out risks, missing pieces, and likely weak spots before suggesting fixes.\n"
            "3. Prefer read-only inspection commands and summarize findings clearly.\n"
            "4. Group recommendations by impact so the next step is obvious."
        ),
    }


def detect_agent_recipe(user_input: str, has_attachments: bool = False) -> Optional[Dict[str, str]]:
    """Pick a lightweight recipe for common agent tasks."""
    text = (user_input or "").lower()

    repo_patterns = [
        r"\brepo\b", r"\brepository\b", r"\bgit\b", r"\bcodebase\b",
        r"\bproject structure\b", r"\bbranch\b", r"\bcommit\b",
    ]
    file_patterns = [
        r"\bfile\b", r"\bfiles\b", r"\bfolder\b", r"\bdocument\b",
        r"\banalyze this\b", r"\battachment\b", r"\buploaded\b",
    ]
    env_patterns = [
        r"\benvironment\b", r"\bsystem\b", r"\bsetup\b", r"\bversions?\b",
        r"\binstalled\b", r"\bcheck my\b", r"\bdiagnostic\b", r"\bdeps?\b",
    ]
    debug_patterns = [
        r"\bdebug\b", r"\bbug\b", r"\berror\b", r"\bcrash\b", r"\bfailing\b",
        r"\bfails?\b", r"\bissue\b", r"\bproblem\b", r"\btraceback\b",
        r"\bstack trace\b", r"\bnot working\b", r"\bbroken\b",
    ]
    audit_patterns = [
        r"\baudit\b", r"\breview the project\b", r"\breview this project\b",
        r"\bproject audit\b", r"\bcode audit\b", r"\barchitecture review\b",
        r"\bwhat'?s weak\b", r"\bwhat is weak\b", r"\bwhat needs work\b",
    ]

    if any(re.search(pattern, text) for pattern in debug_patterns):
        return _debug_recipe()

    if any(re.search(pattern, text) for pattern in audit_patterns):
        return _audit_recipe()

    if any(re.search(pattern, text) for pattern in repo_patterns):
        return _repo_recipe()

    if has_attachments or any(re.search(pattern, text) for pattern in file_patterns):
        return _file_recipe()

    if any(re.search(pattern, text) for pattern in env_patterns):
        return _env_recipe()

    return None


def format_task_recipe_notice(task_recipe: Optional[Dict[str, str]], agent_mode: bool = False) -> Optional[str]:
    """Create a short user-visible notice for the detected task recipe."""
    if not task_recipe:
        return None

    label = "Agent Recipe" if agent_mode else "Task Recipe"
    title = task_recipe.get("title") or task_recipe.get("name") or "Task Guidance"
    guidance = (task_recipe.get("guidance") or "").strip()
    first_line = guidance.splitlines()[0].strip() if guidance else ""

    if first_line:
        return f"[{label}] {title} - {first_line}"
    return f"[{label}] {title}"


def format_task_recipe_status(task_recipe: Optional[Dict[str, str]], agent_mode: bool = False) -> str:
    """Create a compact status-bar label for the current task recipe."""
    if not task_recipe:
        return "Agent Mode: ON" if agent_mode else "Shadow is thinking..."

    title = task_recipe.get("title") or task_recipe.get("name") or "Task Guidance"
    if agent_mode:
        return f"Agent Mode: {title}"
    return f"Shadow is thinking... [{title}]"


def build_agent_prompt(user_input: str, has_attachments: bool = False) -> str:
    """Build a guided Agent Mode prompt with an optional recipe."""
    base = "You are in Agent Mode. Provide stepwise plans and be explicit about actions."
    recipe = detect_agent_recipe(user_input, has_attachments=has_attachments)
    if not recipe:
        return f"{base}\n\n{user_input}"

    return (
        f"{base}\n\n"
        f"[Agent Recipe: {recipe['title']}]\n"
        f"{recipe['guidance']}\n\n"
        f"{user_input}"
    )
