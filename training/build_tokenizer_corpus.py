"""
Build supplemental tokenizer corpus and seed-token files from local project text.

This keeps the workflow lightweight:
- scan project docs/code/text assets
- extract useful text lines
- dedupe and normalize them
- write a corpus text file for tokenizer training
- optionally write a starter seed-token list
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".adoc", ".org", ".log", ".json", ".jsonl",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".html", ".sql",
    ".sh", ".bash", ".ps1"
}

SKIP_DIR_NAMES = {
    ".git", ".venv-win", "venv", "node_modules", "__pycache__", "checkpoints",
    "runtime_cleanup_baseline_600", "runtime_cleanup_vocab840_600",
    "runtime_shadow_core_30step", "runtime_shadow_core_intenthead_smoke",
    "runtime_shadow_core_smoke", "runtime_shadow_core_smoke_fast",
    "runtime_shadow_core_smoke_lean", "runtime_shadow_core_smoke_tf",
}

DEFAULT_SEED_TOKENS = [
    # recent internet / general language
    "rizz", "doomscroll", "doomscrolling", "brainrot", "brain-rot", "ragebait",
    "rage-bait", "delulu", "unalive", "situationship", "cringe", "mid", "sus",
    "slay", "goated", "based", "npc", "stan", "ghosted", "touchgrass", "touch-grass",
    "copypasta", "shitpost", "fyp", "irl", "afk", "lore", "vibecoding", "vibe-coding",
    "lowkey", "highkey", "idk", "imo", "imho", "tbh",
    # AI / dev / Shadow-relevant
    "agentic", "multimodal", "prompting", "prompt-engineering", "finetune", "fine-tune",
    "rag", "reranker", "embedding", "embeddings", "vectorstore", "tokenizer", "llm",
    "sils", "ollama", "gguf", "quantized", "quantization", "toolcall", "tool-calling",
    "selfhosted", "self-hosted", "localfirst", "local-first", "offlinefirst", "offline-first",
    "privacyfirst", "privacy-focused", "telemetry", "airgap", "sandboxed", "guardrail",
    "fallback", "backend", "router", "inference", "checkpoint", "dedupe", "deduplication",
    "speech-to-text", "stt", "docx", "chromebook", "copilot",
]


def normalize_line(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    text = text.replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[#>\-\*\d\.\)\(\[\]`\"':;,_/\\|]+", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def looks_useful(text: str) -> bool:
    if len(text) < 12:
        return False
    alpha_count = sum(ch.isalpha() for ch in text)
    if alpha_count < 4:
        return False
    if text.startswith("http://") or text.startswith("https://"):
        return False
    return True


def iter_project_texts(root: Path) -> Iterable[str]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if path.suffix.lower() == ".jsonl":
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    candidate = normalize_line(line)
                    if looks_useful(candidate):
                        yield candidate
                    continue

                if isinstance(payload, dict):
                    for key in ("input", "output", "cleaned", "text", "content", "guidance", "title"):
                        value = payload.get(key)
                        if isinstance(value, str):
                            candidate = normalize_line(value)
                            if looks_useful(candidate):
                                yield candidate
                elif isinstance(payload, str):
                    candidate = normalize_line(payload)
                    if looks_useful(candidate):
                        yield candidate
            continue

        for line in raw.splitlines():
            candidate = normalize_line(line)
            if looks_useful(candidate):
                yield candidate


def collect_seed_tokens(extra_seed_files: list[Path] | None = None) -> list[str]:
    tokens = list(DEFAULT_SEED_TOKENS)

    for seed_path in extra_seed_files or []:
        if not seed_path.exists():
            continue
        for raw_line in seed_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            token = raw_line.strip().lower()
            if token:
                tokens.append(token)

    deduped: list[str] = []
    seen = set()
    for token in tokens:
        token = token.strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build supplemental tokenizer corpus from local project text.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output-corpus", type=Path, default=Path(__file__).resolve().parent / "corpus" / "tokenizer_corpus_v2.txt")
    parser.add_argument("--output-seeds", type=Path, default=Path(__file__).resolve().parent / "corpus" / "tokenizer_seed_recent_v1.txt")
    parser.add_argument("--extra-seed-file", action="append", default=[], help="Optional extra seed-token text file")
    args = parser.parse_args()

    lines: list[str] = []
    seen_lines = set()
    for line in iter_project_texts(args.project_root):
        key = line.lower()
        if key in seen_lines:
            continue
        seen_lines.add(key)
        lines.append(line)

    seed_tokens = collect_seed_tokens([Path(p) for p in args.extra_seed_file])

    write_lines(args.output_corpus, lines)
    write_lines(args.output_seeds, seed_tokens)

    print(f"Project root: {args.project_root}")
    print(f"Corpus lines: {len(lines)}")
    print(f"Seed tokens: {len(seed_tokens)}")
    print(f"Wrote corpus: {args.output_corpus}")
    print(f"Wrote seeds: {args.output_seeds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
