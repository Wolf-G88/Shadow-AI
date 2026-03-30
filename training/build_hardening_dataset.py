"""
Build a harder Shadow training set from adversarial intent/cleanup examples.

This creates:
- a standalone hardening dataset
- a merged training dataset that appends the hardening rows to the main train split
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List


HARDENING_EXAMPLES: List[Dict] = [
    {
        "input": "shadow skip the sales pitch and tell me what you can still help with when wifi is dead",
        "variants": ["no marketing just say what shadow can help with offline"],
        "cleaned": "What can Shadow AI help with offline?",
        "intent": "capability_query",
        "command": {"action": "route_intent", "target": "recognition_kb", "params": {"category": "capabilities"}}
    },
    {
        "input": "if i dump code notes and random docs on you what can shadow actually do with all that stuff",
        "variants": ["what can shadow ai do with code notes docs and files"],
        "cleaned": "What can Shadow AI do with code, notes, documents, and files?",
        "intent": "capability_query",
        "command": {"action": "route_intent", "target": "recognition_kb", "params": {"category": "capabilities"}}
    },
    {
        "input": "cut the fluff can shadow handle memory file reading and safer command help or no",
        "variants": ["can shadow do memory file reading and safer commands"],
        "cleaned": "Can Shadow handle memory, file reading, and safer command help?",
        "intent": "capability_query",
        "command": {"action": "route_intent", "target": "recognition_kb", "params": {"category": "capabilities"}}
    },
    {
        "input": "what all can shadow do for me on this machine without acting like a cloud ad",
        "variants": ["tell me what shadow can do locally on this machine"],
        "cleaned": "What can Shadow AI do locally on this machine?",
        "intent": "capability_query",
        "command": {"action": "route_intent", "target": "recognition_kb", "params": {"category": "capabilities"}}
    },
    {
        "input": "lock this in my handle is Wolf King and that is what you call me",
        "variants": ["remember this my handle is Wolf King"],
        "cleaned": "Remember that my handle is Wolf King.",
        "intent": "memory_store",
        "command": {"action": "store_memory", "target": "relationships", "params": {"key": "user_handle"}}
    },
    {
        "input": "remember that i always want python first if the choice is python or java",
        "variants": ["store this i prefer python over java"],
        "cleaned": "Remember that I prefer Python over Java.",
        "intent": "memory_store",
        "command": {"action": "store_memory", "target": "preferences", "params": {"key": "language_preference"}}
    },
    {
        "input": "do not lose this shadow stays private and local first before anything else",
        "variants": ["remember shadow is private and local first"],
        "cleaned": "Remember that Shadow stays private and local-first.",
        "intent": "memory_store",
        "command": {"action": "store_memory", "target": "facts", "params": {"key": "project_priority"}}
    },
    {
        "input": "keep this too i want gpu runs when they are stable but not stupid",
        "variants": ["remember i want gpu runs only when they stay stable"],
        "cleaned": "Remember that I want GPU runs only when they stay stable.",
        "intent": "memory_store",
        "command": {"action": "store_memory", "target": "preferences", "params": {"key": "gpu_preference"}}
    },
    {
        "input": "what name did i tell you to use for me dont freestyle it",
        "variants": ["what handle did i say was mine"],
        "cleaned": "What name did I tell you to use for me?",
        "intent": "memory_recall",
        "command": {"action": "recall_memory", "target": "relationships", "params": {"key": "user_handle"}}
    },
    {
        "input": "what did i keep saying about privacy and local first stuff",
        "variants": ["tell me the privacy rule i kept repeating"],
        "cleaned": "What did I say about privacy and local-first behavior?",
        "intent": "memory_recall",
        "command": {"action": "recall_memory", "target": "facts", "params": {"key": "project_priority"}}
    },
    {
        "input": "which language did i say i want first when python and java are both on the table",
        "variants": ["what language do i prefer first between python and java"],
        "cleaned": "Which language did I say I want first between Python and Java?",
        "intent": "memory_recall",
        "command": {"action": "recall_memory", "target": "preferences", "params": {"key": "language_preference"}}
    },
    {
        "input": "remind me what style i asked for when i said keep it blunt and short",
        "variants": ["what response style did i ask for"],
        "cleaned": "What response style did I ask for?",
        "intent": "memory_recall",
        "command": {"action": "recall_memory", "target": "preferences", "params": {"key": "response_style"}}
    },
    {
        "input": "read this docx and give me the short version without padding it out",
        "variants": ["check this docx and summarize it briefly"],
        "cleaned": "Read this DOCX file and summarize it briefly.",
        "intent": "file_analysis_request",
        "command": {"action": "route_file", "target": "analysis", "params": {"mode": "docx_summary"}}
    },
    {
        "input": "look through this markdown and the txt beside it and tell me what matters",
        "variants": ["inspect this markdown and txt and tell me the important parts"],
        "cleaned": "Inspect this markdown and text file and tell me what matters.",
        "intent": "file_analysis_request",
        "command": {"action": "route_file", "target": "analysis", "params": {"mode": "text_summary"}}
    },
    {
        "input": "check this image but be honest if the current model can only inspect metadata",
        "variants": ["look at this image and be honest if you cannot really see it"],
        "cleaned": "Check this image and be honest if the current model can only inspect metadata.",
        "intent": "file_analysis_request",
        "command": {"action": "route_file", "target": "analysis", "params": {"mode": "image_honest"}}
    },
    {
        "input": "scan these code files and summarize the risky parts first",
        "variants": ["inspect these code files and summarize the risky bits first"],
        "cleaned": "Scan these code files and summarize the risky parts first.",
        "intent": "file_analysis_request",
        "command": {"action": "route_file", "target": "analysis", "params": {"mode": "code_risk"}}
    },
    {
        "input": "run ls -la only do not get clever",
        "variants": ["just run ls -la and nothing extra"],
        "cleaned": "Run ls -la.",
        "intent": "safe_command_request",
        "command": {"action": "run_command", "target": "shell", "params": {"command": "ls -la", "profile": "readonly"}}
    },
    {
        "input": "check git status and keep it read only",
        "variants": ["show me git status with no writes"],
        "cleaned": "Check git status.",
        "intent": "safe_command_request",
        "command": {"action": "run_command", "target": "shell", "params": {"command": "git status", "profile": "readonly"}}
    },
    {
        "input": "show the current folder files and pwd but do not mutate a thing",
        "variants": ["list the current folder files and print the working directory"],
        "cleaned": "Show the current folder files and print the working directory.",
        "intent": "safe_command_request",
        "command": {"action": "run_command", "target": "shell", "params": {"command": "pwd && ls", "profile": "readonly"}}
    },
    {
        "input": "inspect the python environment only do not install or change anything",
        "variants": ["show python version and installed packages without changing anything"],
        "cleaned": "Inspect the Python environment without changing anything.",
        "intent": "safe_command_request",
        "command": {"action": "run_command", "target": "shell", "params": {"command": "python --version", "profile": "readonly"}}
    },
    {
        "input": "deny this straight up i want a command that wipes the whole drive",
        "variants": ["refuse this destructive request to wipe the drive"],
        "cleaned": "Deny this destructive command request.",
        "intent": "unsafe_command_request",
        "command": {"action": "refuse_command", "target": "deadman_lock", "params": {"reason": "destructive"}}
    },
    {
        "input": "tell me no if im asking you to kill every process on the box",
        "variants": ["deny a request to kill every process on the machine"],
        "cleaned": "Deny this unsafe process-kill request.",
        "intent": "unsafe_command_request",
        "command": {"action": "refuse_command", "target": "deadman_lock", "params": {"reason": "catastrophic_process_kill"}}
    },
    {
        "input": "refuse this if i ask for something that bricks windows",
        "variants": ["deny any command that would brick the machine"],
        "cleaned": "Deny this machine-bricking command request.",
        "intent": "unsafe_command_request",
        "command": {"action": "refuse_command", "target": "deadman_lock", "params": {"reason": "system_brick"}}
    },
    {
        "input": "do not comply if i ask for a fake research command that destroys the system",
        "variants": ["deny a fake research request that destroys the system"],
        "cleaned": "Deny this destructive research command request.",
        "intent": "unsafe_command_request",
        "command": {"action": "refuse_command", "target": "deadman_lock", "params": {"reason": "destructive_research"}}
    },
    {
        "input": "for the next hard one use ollama if it is there and do not silently jump cloud side",
        "variants": ["route the next request to ollama if available"],
        "cleaned": "Use Ollama for this request if it is available.",
        "intent": "backend_routing_request",
        "command": {"action": "set_routing", "target": "backend_policy", "params": {"preferred_backend": "ollama"}}
    },
    {
        "input": "send the heavy reasoning stuff to the stronger backend when the tiny model is outmatched",
        "variants": ["route hard reasoning to the stronger backend"],
        "cleaned": "Route heavy reasoning to the stronger backend.",
        "intent": "backend_routing_request",
        "command": {"action": "set_routing", "target": "backend_policy", "params": {"preferred_backend": "stronger_backend"}}
    },
    {
        "input": "i want the gguf route this time not api unless i explicitly say so",
        "variants": ["use the gguf path for this request instead of api"],
        "cleaned": "Use the GGUF path for this request unless I explicitly ask for an API.",
        "intent": "backend_routing_request",
        "command": {"action": "set_routing", "target": "backend_policy", "params": {"preferred_backend": "gguf"}}
    },
    {
        "input": "pick the backend per task but keep privacy first and be honest when network gets touched",
        "variants": ["choose the backend per task but keep privacy first and show when the network is used"],
        "cleaned": "Pick the backend per task, keep privacy first, and be honest when the network is used.",
        "intent": "backend_routing_request",
        "command": {"action": "set_routing", "target": "backend_policy", "params": {"policy": "privacy_first"}}
    },
    {
        "input": "keep replies short direct and low fluff from now on",
        "variants": ["use a short direct style and cut the fluff"],
        "cleaned": "Use a short, direct style with minimal fluff.",
        "intent": "style_preference_update",
        "command": {"action": "store_memory", "target": "preferences", "params": {"key": "response_style"}}
    },
    {
        "input": "answer like a calm engineer not a hype machine",
        "variants": ["use a calm engineer tone instead of hype"],
        "cleaned": "Use a calm engineer tone instead of hype.",
        "intent": "style_preference_update",
        "command": {"action": "store_memory", "target": "preferences", "params": {"key": "tone_style"}}
    },
    {
        "input": "when im stressed keep it concise practical and steady",
        "variants": ["keep responses concise practical and steady when im stressed"],
        "cleaned": "Keep responses concise, practical, and steady.",
        "intent": "style_preference_update",
        "command": {"action": "store_memory", "target": "preferences", "params": {"key": "stress_style"}}
    },
    {
        "input": "mirror my blunt style but stay safe if the ask is dumb or destructive",
        "variants": ["match my blunt style but stay safe on destructive asks"],
        "cleaned": "Mirror my blunt style, but stay safe on destructive asks.",
        "intent": "style_preference_update",
        "command": {"action": "store_memory", "target": "preferences", "params": {"key": "safety_style"}}
    },
]


def iter_examples() -> Iterable[Dict]:
    for index, example in enumerate(HARDENING_EXAMPLES):
        base = {
            "cleaned": example["cleaned"],
            "intent": example["intent"],
            "command": example["command"],
            "metadata": {
                "source": "hardening_v1",
                "example_index": index,
            },
        }
        seen = set()
        for prompt in [example["input"], *example.get("variants", [])]:
            prompt = " ".join((prompt or "").split())
            if not prompt or prompt in seen:
                continue
            seen.add(prompt)
            row = dict(base)
            row["input"] = prompt
            yield row


def load_jsonl(path: Path) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Build Shadow hardening dataset")
    parser.add_argument("--base-train", required=True, help="Existing train JSONL")
    parser.add_argument("--hardening-output", required=True, help="Output JSONL for hardening examples")
    parser.add_argument("--merged-output", required=True, help="Output JSONL for merged train set")
    args = parser.parse_args()

    base_train_path = Path(args.base_train)
    hardening_output = Path(args.hardening_output)
    merged_output = Path(args.merged_output)

    hardening_rows = list(iter_examples())
    base_rows = load_jsonl(base_train_path)
    merged_rows = base_rows + hardening_rows

    hardening_count = write_jsonl(hardening_output, hardening_rows)
    merged_count = write_jsonl(merged_output, merged_rows)

    print(f"Base rows: {len(base_rows)}")
    print(f"Hardening rows: {hardening_count}")
    print(f"Merged rows: {merged_count}")
    print(f"Hardening dataset: {hardening_output}")
    print(f"Merged dataset: {merged_output}")


if __name__ == "__main__":
    main()
