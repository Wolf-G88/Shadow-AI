"""
Dataset loader for SILS v1 training.

Supports both:
- legacy examples with `output` + numeric `intent_label`
- newer Shadow-core examples with `cleaned` + string `intent`
"""

import json
import re
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from typing import List, Dict, Optional
from difflib import SequenceMatcher


DEFAULT_INTENT_NAMES = [
    "memory_store",
    "memory_recall",
    "capability_query",
    "file_analysis_request",
    "safe_command_request",
    "unsafe_command_request",
    "backend_routing_request",
    "style_preference_update",
]


class ShadowDataset(Dataset):
    """
    Dataset for Shadow AI training.
    
    Format: JSONL with fields:
    - input: user message
    - output: AI response
    - intent_label: intent classification (0-5)
    - tone_label: tone classification (optional)
    - metadata: additional info
    """
    
    NOISE_MARKER_PATTERN = re.compile(
        r"\b(?:pls|plz|u|ur|im|dont|alot|gonna|wanna|thru|cause|cuz|btw|idk|lemme|gotta)\b"
        r"|(?<!\w)[42](?!\w)|\?{2,}|!{2,}",
        re.IGNORECASE
    )

    def __init__(self, data_path: str, tokenizer, max_length: int = 192,
                 intent_to_label: Optional[Dict[str, int]] = None,
                 cleanup_boost: int = 0,
                 max_cleanup_repeats: int = 4):
        self.data_path = Path(data_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.cleanup_boost = max(0, int(cleanup_boost or 0))
        self.max_cleanup_repeats = max(1, int(max_cleanup_repeats or 1))
        
        # Load data
        self.examples = self._load_data()
        self.intent_to_label = self._build_intent_map(intent_to_label)
        self.label_to_intent = self._invert_intent_map()
        self.example_repeat_counts: List[int] = []
        self.training_examples = self._build_training_examples()
    
    def _load_data(self) -> List[Dict]:
        """Load JSONL dataset."""
        examples = []
        
        if not self.data_path.exists():
            print(f"Warning: Dataset not found at {self.data_path}")
            return examples
        
        with open(self.data_path, 'r') as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)
                    examples.append(example)
        
        print(f"Loaded {len(examples)} examples from {self.data_path}")
        return examples

    def _build_intent_map(self, explicit_map: Optional[Dict[str, int]]) -> Dict[str, int]:
        """Build stable string->label mapping for mixed dataset formats."""
        if explicit_map:
            return dict(explicit_map)

        discovered = []
        numeric_labels = set()

        for example in self.examples:
            intent_name = example.get('intent')
            if isinstance(intent_name, str):
                intent_name = intent_name.strip()
                if intent_name and intent_name not in discovered:
                    discovered.append(intent_name)

            label = example.get('intent_label')
            if isinstance(label, int):
                numeric_labels.add(label)

        if discovered:
            ordered_names = [name for name in DEFAULT_INTENT_NAMES if name in discovered]
            ordered_names.extend(sorted(name for name in discovered if name not in ordered_names))
            return {name: idx for idx, name in enumerate(ordered_names)}

        if numeric_labels:
            return {f"intent_{label}": label for label in sorted(numeric_labels)}

        return {name: idx for idx, name in enumerate(DEFAULT_INTENT_NAMES)}

    def _invert_intent_map(self) -> List[str]:
        """Create label->name list."""
        if not self.intent_to_label:
            return []

        max_label = max(self.intent_to_label.values())
        label_to_intent = [f"intent_{i}" for i in range(max_label + 1)]
        for name, label in self.intent_to_label.items():
            if label >= len(label_to_intent):
                label_to_intent.extend(f"intent_{i}" for i in range(len(label_to_intent), label + 1))
            label_to_intent[label] = name
        return label_to_intent

    def _get_output_text(self, example: Dict) -> str:
        """Resolve target text across legacy and newer schemas."""
        return example.get('output') or example.get('cleaned') or ""

    def _get_intent_label(self, example: Dict) -> int:
        """Resolve numeric intent label across legacy and newer schemas."""
        label = example.get('intent_label')
        if isinstance(label, int):
            return label

        intent_name = example.get('intent')
        if isinstance(intent_name, str):
            return self.intent_to_label.get(intent_name.strip(), 0)

        return 0

    def get_intent_names(self) -> List[str]:
        """Get ordered intent names for the active dataset."""
        return list(self.label_to_intent)

    def get_raw_example_count(self) -> int:
        """Get the number of raw JSONL rows."""
        return len(self.examples)

    def get_training_example_count(self) -> int:
        """Get the expanded training-example count."""
        return len(self.training_examples)

    def get_example_repeat_counts(self) -> List[int]:
        """Get repeat counts per raw example after cleanup boosting."""
        return list(self.example_repeat_counts)

    def get_cleanup_repeat_summary(self) -> Dict[str, float]:
        """Summarize cleanup repeat behavior for logging/debugging."""
        if not self.example_repeat_counts:
            return {
                "cleanup_boost": self.cleanup_boost,
                "boosted_examples": 0,
                "avg_repeat": 0.0,
                "max_repeat": 0,
            }

        boosted = sum(1 for count in self.example_repeat_counts if count > 1)
        avg_repeat = sum(self.example_repeat_counts) / len(self.example_repeat_counts)
        return {
            "cleanup_boost": self.cleanup_boost,
            "boosted_examples": boosted,
            "avg_repeat": avg_repeat,
            "max_repeat": max(self.example_repeat_counts),
        }

    def _normalize_cleanup_text(self, text: str) -> str:
        text = (text or "").lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _has_noise_markers(self, text: str) -> bool:
        return bool(self.NOISE_MARKER_PATTERN.search(text or ""))

    def _estimate_cleanup_difficulty(self, input_text: str, output_text: str) -> int:
        source = self._normalize_cleanup_text(input_text)
        target = self._normalize_cleanup_text(output_text)

        if not source or not target or source == target:
            return 0

        ratio = SequenceMatcher(None, source, target).ratio()
        source_words = source.split()
        target_words = target.split()

        difficulty = 1
        if (
            ratio < 0.82 or
            self._has_noise_markers(input_text) or
            len(source_words) != len(target_words)
        ):
            difficulty = 2
        if ratio < 0.67 and len(source) > 12:
            difficulty = 3

        return difficulty

    def _get_example_repeat_count(self, example: Dict) -> int:
        if self.cleanup_boost <= 0:
            return 1

        output_text = self._get_output_text(example)
        difficulty = self._estimate_cleanup_difficulty(example.get('input', ''), output_text)
        if difficulty < 2:
            return 1

        return min(
            self.max_cleanup_repeats,
            1 + ((difficulty - 1) * self.cleanup_boost)
        )

    def _build_training_examples(self) -> List[Dict]:
        """
        Expand each row into autoregressive prefix->next-token examples.

        This matches runtime generation more closely:
        - input starts as the user prompt
        - generated tokens are appended over time
        - the model predicts one next token at each step
        """
        training_examples = []

        for example_index, example in enumerate(self.examples):
            input_text = example.get('input', '')
            output_text = self._get_output_text(example)
            if not input_text or not output_text:
                self.example_repeat_counts.append(0)
                continue

            prompt_ids = self.tokenizer.encode(
                input_text,
                max_length=None,
                add_special_tokens=True,
                pad=False
            )
            target_tokens = self.tokenizer.encode(
                output_text,
                max_length=None,
                add_special_tokens=False,
                pad=False
            )
            if not target_tokens:
                continue

            target_tokens = target_tokens + [self.tokenizer.eos_id]
            intent_label = self._get_intent_label(example)
            tone_label = example.get('tone_label', 0)
            repeat_count = self._get_example_repeat_count(example)
            self.example_repeat_counts.append(repeat_count)

            for repeat_index in range(repeat_count):
                for step, target_id in enumerate(target_tokens):
                    prefix_ids = prompt_ids + target_tokens[:step]
                    if len(prefix_ids) > self.max_length:
                        prefix_ids = prefix_ids[-self.max_length:]

                    training_examples.append({
                        'input_ids': prefix_ids,
                        'target_id': target_id,
                        'intent_label': intent_label,
                        'tone_label': tone_label,
                        'raw_example_index': example_index,
                        'step': step,
                        'repeat_index': repeat_index,
                        'repeat_count': repeat_count,
                    })

        print(
            f"Expanded {len(self.examples)} raw examples into "
            f"{len(training_examples)} autoregressive training examples"
        )
        return training_examples
    
    def __len__(self):
        return len(self.training_examples)
    
    def __getitem__(self, idx):
        example = self.training_examples[idx]
        
        return {
            'input_ids': torch.tensor(example['input_ids'], dtype=torch.long),
            'output_ids': torch.tensor([example['target_id']], dtype=torch.long),
            'intent_label': torch.tensor(example['intent_label'], dtype=torch.long),
            'tone_label': torch.tensor(example['tone_label'], dtype=torch.long)
        }


def collate_fn(batch):
    """Collate function for batching."""
    # Pad sequences to same length
    input_ids = [item['input_ids'] for item in batch]
    output_ids = [item['output_ids'] for item in batch]
    intent_labels = [item['intent_label'] for item in batch]
    tone_labels = [item['tone_label'] for item in batch]
    
    # Pad to max length in batch
    max_input_len = max(len(ids) for ids in input_ids)
    max_output_len = max(len(ids) for ids in output_ids)
    
    input_ids_padded = torch.stack([
        torch.cat([ids, torch.zeros(max_input_len - len(ids), dtype=torch.long)])
        for ids in input_ids
    ])
    
    output_ids_padded = torch.stack([
        torch.cat([ids, torch.zeros(max_output_len - len(ids), dtype=torch.long)])
        for ids in output_ids
    ])
    
    intent_labels = torch.stack(intent_labels)
    tone_labels = torch.stack(tone_labels)
    
    return {
        'input_ids': input_ids_padded,
        'output_ids': output_ids_padded,
        'intent_labels': intent_labels,
        'tone_labels': tone_labels
    }


def create_dataloader(data_path: str, tokenizer, batch_size: int = 16, shuffle: bool = True,
                      return_dataset: bool = False, intent_to_label: Optional[Dict[str, int]] = None,
                      cleanup_boost: int = 0, max_cleanup_repeats: int = 4):
    """Create DataLoader for training."""
    dataset = ShadowDataset(
        data_path,
        tokenizer,
        intent_to_label=intent_to_label,
        cleanup_boost=cleanup_boost,
        max_cleanup_repeats=max_cleanup_repeats
    )

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collate_fn,
        num_workers=0  # Use 0 for compatibility
    )

    if return_dataset:
        return loader, dataset

    return loader
