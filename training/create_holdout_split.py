"""
Create a deterministic held-out validation split for Shadow training data.
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def load_examples(path: str) -> List[Dict]:
    examples: List[Dict] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def get_bucket_key(example: Dict) -> str:
    intent_name = example.get("intent")
    if isinstance(intent_name, str) and intent_name.strip():
        return f"intent:{intent_name.strip()}"

    intent_label = example.get("intent_label")
    if isinstance(intent_label, int):
        return f"label:{intent_label}"

    return "unknown"


def stratified_split(
    examples: List[Dict],
    val_ratio: float = 0.1,
    seed: int = 1337
) -> Tuple[List[Dict], List[Dict]]:
    rng = random.Random(seed)
    buckets: Dict[str, List[Dict]] = defaultdict(list)
    for example in examples:
        buckets[get_bucket_key(example)].append(example)

    train_examples: List[Dict] = []
    val_examples: List[Dict] = []

    for key in sorted(buckets):
        bucket = list(buckets[key])
        rng.shuffle(bucket)

        if len(bucket) <= 1:
            train_examples.extend(bucket)
            continue

        val_count = max(1, int(round(len(bucket) * val_ratio)))
        val_count = min(val_count, len(bucket) - 1)

        val_examples.extend(bucket[:val_count])
        train_examples.extend(bucket[val_count:])

    rng.shuffle(train_examples)
    rng.shuffle(val_examples)
    return train_examples, val_examples


def write_examples(path: str, examples: Iterable[Dict]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=True) + "\n")


def summarize_by_bucket(examples: List[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for example in examples:
        counts[get_bucket_key(example)] += 1
    return dict(sorted(counts.items()))


def main():
    parser = argparse.ArgumentParser(description="Create deterministic held-out split")
    parser.add_argument("--input", required=True, help="Input JSONL dataset")
    parser.add_argument("--train-output", required=True, help="Output JSONL for train split")
    parser.add_argument("--val-output", required=True, help="Output JSONL for validation split")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation ratio per intent bucket")
    parser.add_argument("--seed", type=int, default=1337, help="Shuffle seed")
    args = parser.parse_args()

    examples = load_examples(args.input)
    train_examples, val_examples = stratified_split(
        examples,
        val_ratio=args.val_ratio,
        seed=args.seed
    )

    write_examples(args.train_output, train_examples)
    write_examples(args.val_output, val_examples)

    print(f"Loaded {len(examples)} examples from {args.input}")
    print(f"Train split: {len(train_examples)} -> {args.train_output}")
    print(f"Val split: {len(val_examples)} -> {args.val_output}")
    print("Train buckets:", summarize_by_bucket(train_examples))
    print("Val buckets:", summarize_by_bucket(val_examples))


if __name__ == "__main__":
    main()
