import os
import sys
import tempfile
import unittest
import warnings

warnings.filterwarnings(
    "ignore",
    message="The pynvml package is deprecated.*",
    category=FutureWarning,
)
import torch


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class SILSIntentHeadTests(unittest.TestCase):
    def _config(self):
        return {
            "embedding_dim": 32,
            "intent_encoder": {
                "type": "gru",
                "layers": 1,
                "hidden_size": 32,
                "bidirectional": True,
            },
            "tone_encoder": {
                "type": "transformer",
                "layers": 1,
                "heads": 4,
                "hidden_size": 64,
                "ff_size": 128,
            },
            "fusion": {
                "type": "gated",
                "gate_dim": 384,
            },
            "intents": [
                "memory_store",
                "memory_recall",
                "capability_query",
            ],
        }

    def test_model_outputs_intent_logits(self):
        from model.dual_encoder import DualEncoder

        model = DualEncoder(self._config(), vocab_size=32)
        output = model(torch.tensor([[2, 5, 6, 3]], dtype=torch.long), mode="hybrid")

        self.assertIn("intent_logits", output)
        self.assertEqual(tuple(output["intent_logits"].shape), (1, 3))

    def test_checkpoint_preserves_intent_head(self):
        from model.dual_encoder import DualEncoder

        model = DualEncoder(self._config(), vocab_size=32)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "model.pt")
            model.save_checkpoint(path)
            loaded = DualEncoder.load_checkpoint(path)
            self.assertIsNotNone(loaded.intent_head)
            self.assertEqual(loaded.intent_head.out_features, 3)


if __name__ == "__main__":
    unittest.main()
