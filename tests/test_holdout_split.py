import json
import tempfile
import unittest
from pathlib import Path

from training.create_holdout_split import load_examples, stratified_split, write_examples


class TestHoldoutSplit(unittest.TestCase):
    def _write_jsonl(self, examples):
        temp_dir = tempfile.TemporaryDirectory()
        path = Path(temp_dir.name) / "dataset.jsonl"
        with open(path, "w", encoding="utf-8") as handle:
            for example in examples:
                handle.write(json.dumps(example) + "\n")
        return temp_dir, path

    def test_stratified_split_preserves_each_intent_bucket(self):
        examples = []
        for intent in ("memory_store", "capability_query", "file_analysis_request"):
            for index in range(10):
                examples.append({
                    "input": f"{intent} input {index}",
                    "cleaned": f"{intent} cleaned {index}",
                    "intent": intent,
                })

        train_examples, val_examples = stratified_split(examples, val_ratio=0.2, seed=7)

        self.assertEqual(len(train_examples), 24)
        self.assertEqual(len(val_examples), 6)

        train_intents = {example["intent"] for example in train_examples}
        val_intents = {example["intent"] for example in val_examples}
        self.assertEqual(train_intents, {"memory_store", "capability_query", "file_analysis_request"})
        self.assertEqual(val_intents, {"memory_store", "capability_query", "file_analysis_request"})

    def test_split_is_deterministic_and_writable(self):
        temp_dir, path = self._write_jsonl([
            {"input": f"remember item {index}", "cleaned": f"remember item {index}", "intent": "memory_store"}
            for index in range(8)
        ] + [
            {"input": f"what can shadow do {index}", "cleaned": f"what can shadow do {index}", "intent": "capability_query"}
            for index in range(8)
        ])
        self.addCleanup(temp_dir.cleanup)

        examples = load_examples(str(path))
        train_a, val_a = stratified_split(examples, val_ratio=0.25, seed=1337)
        train_b, val_b = stratified_split(examples, val_ratio=0.25, seed=1337)

        self.assertEqual(train_a, train_b)
        self.assertEqual(val_a, val_b)

        train_out = Path(temp_dir.name) / "train.jsonl"
        val_out = Path(temp_dir.name) / "val.jsonl"
        write_examples(str(train_out), train_a)
        write_examples(str(val_out), val_a)

        self.assertEqual(len(load_examples(str(train_out))), len(train_a))
        self.assertEqual(len(load_examples(str(val_out))), len(val_a))


if __name__ == "__main__":
    unittest.main()
