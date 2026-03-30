import json
import tempfile
import unittest
from pathlib import Path

from training.dataset import ShadowDataset
from training.tokenizer import build_tokenizer_from_dataset, ShadowTokenizer


class TestTrainingDatasetCompat(unittest.TestCase):
    def _normalize_decoded(self, text):
        return " ".join(text.split())

    def _write_jsonl(self, examples):
        temp_dir = tempfile.TemporaryDirectory()
        path = Path(temp_dir.name) / "dataset.jsonl"
        with open(path, "w", encoding="utf-8") as handle:
            for example in examples:
                handle.write(json.dumps(example) + "\n")
        return temp_dir, path

    def test_new_schema_uses_cleaned_and_string_intents(self):
        temp_dir, path = self._write_jsonl([
            {
                "input": "what all can shadow do for me",
                "cleaned": "What can Shadow AI do for me?",
                "intent": "capability_query"
            },
            {
                "input": "remember my name is wolf",
                "cleaned": "Remember my name is Wolf.",
                "intent": "memory_store"
            }
        ])
        self.addCleanup(temp_dir.cleanup)

        tokenizer = build_tokenizer_from_dataset(str(path), vocab_size=64)
        dataset = ShadowDataset(str(path), tokenizer)

        self.assertEqual(
            dataset.get_intent_names(),
            ["memory_store", "capability_query"]
        )
        self.assertEqual(dataset.get_raw_example_count(), 2)
        self.assertGreater(dataset.get_training_example_count(), dataset.get_raw_example_count())

        first_item = dataset[0]
        second_item = dataset[1]
        decoded = self._normalize_decoded(tokenizer.decode(first_item["output_ids"].tolist()))
        self.assertTrue(decoded)
        self.assertEqual(first_item["intent_label"].item(), 1)
        self.assertEqual(second_item["intent_label"].item(), 1)
        self.assertGreater(len(second_item["input_ids"]), len(first_item["input_ids"]))

    def test_legacy_schema_still_works(self):
        temp_dir, path = self._write_jsonl([
            {
                "input": "run ls -la",
                "output": "Run ls -la",
                "intent_label": 4
            }
        ])
        self.addCleanup(temp_dir.cleanup)

        tokenizer = build_tokenizer_from_dataset(str(path), vocab_size=32)
        dataset = ShadowDataset(str(path), tokenizer)

        item = dataset[0]
        decoded = self._normalize_decoded(tokenizer.decode(item["output_ids"].tolist()))

        self.assertTrue(decoded)
        self.assertEqual(item["intent_label"].item(), 4)
        self.assertEqual(dataset.get_intent_names()[-1], "intent_4")
        self.assertEqual(len(dataset.get_intent_names()), 5)
        self.assertEqual(dataset.get_raw_example_count(), 1)
        self.assertGreater(dataset.get_training_example_count(), 1)

    def test_cleanup_boost_repeats_noisy_examples_more_than_clean_ones(self):
        temp_dir, path = self._write_jsonl([
            {
                "input": "hey what all can shadow do 4 me pls",
                "cleaned": "What can Shadow AI do for me?",
                "intent": "capability_query"
            },
            {
                "input": "What can Shadow AI do for me?",
                "cleaned": "What can Shadow AI do for me?",
                "intent": "capability_query"
            }
        ])
        self.addCleanup(temp_dir.cleanup)

        tokenizer = build_tokenizer_from_dataset(str(path), vocab_size=64)
        plain_dataset = ShadowDataset(str(path), tokenizer, cleanup_boost=0)
        boosted_dataset = ShadowDataset(str(path), tokenizer, cleanup_boost=1, max_cleanup_repeats=4)

        plain_repeats = plain_dataset.get_example_repeat_counts()
        boosted_repeats = boosted_dataset.get_example_repeat_counts()
        summary = boosted_dataset.get_cleanup_repeat_summary()

        self.assertEqual(plain_repeats, [1, 1])
        self.assertGreater(boosted_repeats[0], 1)
        self.assertEqual(boosted_repeats[1], 1)
        self.assertGreater(boosted_dataset.get_training_example_count(), plain_dataset.get_training_example_count())
        self.assertEqual(summary["boosted_examples"], 1)
        self.assertGreater(summary["max_repeat"], 1)

    def test_tokenizer_min_frequency_allows_rare_tokens(self):
        temp_dir, path = self._write_jsonl([
            {
                "input": "alpha zebraunique",
                "cleaned": "alpha common",
                "intent": "capability_query"
            },
            {
                "input": "alpha common",
                "cleaned": "alpha common",
                "intent": "capability_query"
            }
        ])
        self.addCleanup(temp_dir.cleanup)

        tokenizer_default = build_tokenizer_from_dataset(str(path), vocab_size=128, min_frequency=2)
        tokenizer_relaxed = build_tokenizer_from_dataset(str(path), vocab_size=128, min_frequency=1)

        self.assertLess(tokenizer_default.get_vocab_size(), tokenizer_relaxed.get_vocab_size())
        self.assertIn("zebraunique</w>", tokenizer_relaxed.get_vocab())

    def test_tokenizer_can_add_seed_tokens_from_file(self):
        temp_dir, path = self._write_jsonl([
            {
                "input": "shadow helper",
                "cleaned": "shadow helper",
                "intent": "capability_query"
            }
        ])
        self.addCleanup(temp_dir.cleanup)

        seed_path = Path(temp_dir.name) / "seed_tokens.txt"
        seed_path.write_text("rizz\nunhingedmode\n", encoding="utf-8")

        tokenizer = build_tokenizer_from_dataset(
            str(path),
            vocab_size=64,
            seed_tokens_path=str(seed_path)
        )

        self.assertIn("rizz</w>", tokenizer.get_vocab())
        encoded = tokenizer.encode("rizz", add_special_tokens=False)
        decoded = tokenizer.decode(encoded)
        self.assertEqual(decoded, "rizz")

    def test_tokenizer_can_use_extra_corpus_texts(self):
        temp_dir, path = self._write_jsonl([
            {
                "input": "shadow helper",
                "cleaned": "shadow helper",
                "intent": "capability_query"
            }
        ])
        self.addCleanup(temp_dir.cleanup)

        extra_corpus_path = Path(temp_dir.name) / "extra_corpus.txt"
        extra_corpus_path.write_text("hyperpop mode engaged\ncodec whisper network\n", encoding="utf-8")

        base_tokenizer = build_tokenizer_from_dataset(str(path), vocab_size=64)
        boosted_tokenizer = build_tokenizer_from_dataset(
            str(path),
            vocab_size=96,
            min_frequency=1,
            extra_text_paths=[str(extra_corpus_path)]
        )

        self.assertGreater(boosted_tokenizer.get_vocab_size(), base_tokenizer.get_vocab_size())
        self.assertIn("hyperpop</w>", boosted_tokenizer.get_vocab())


if __name__ == "__main__":
    unittest.main()
