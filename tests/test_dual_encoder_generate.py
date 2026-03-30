import os
import sys
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


class _TinyTokenizer:
    pad_id = 0
    eos_id = 3


class DualEncoderGenerateTests(unittest.TestCase):
    def _make_config(self):
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
                "gate_dim": 64,
            },
        }

    def test_generate_handles_intent_mode_logits_shape(self):
        from model.dual_encoder import DualEncoder

        model = DualEncoder(self._make_config(), vocab_size=32)
        input_ids = torch.tensor([[2, 5, 6, 3]], dtype=torch.long)

        output = model.generate(
            input_ids,
            max_new_tokens=2,
            mode="intent",
            tokenizer=_TinyTokenizer(),
        )

        self.assertGreaterEqual(output.shape[1], input_ids.shape[1])


if __name__ == "__main__":
    unittest.main()
