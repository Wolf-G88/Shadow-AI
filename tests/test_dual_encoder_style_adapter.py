import unittest
import warnings

warnings.filterwarnings(
    "ignore",
    message="The pynvml package is deprecated.*",
    category=FutureWarning,
)
import torch

from model.dual_encoder import DualEncoder


class TestDualEncoderStyleAdapter(unittest.TestCase):
    def _make_config(self):
        return {
            "embedding_dim": 256,
            "intent_encoder": {
                "hidden_size": 256,
                "layers": 2,
                "bidirectional": True,
            },
            "tone_encoder": {
                "hidden_size": 384,
                "layers": 2,
                "heads": 4,
                "ff_size": 1024,
            },
            "fusion": {
                "gate_dim": 384,
            },
            "personalization": {
                "style_dim": 64,
                "enabled": True,
                "ema_alpha": 0.85,
            },
        }

    def test_style_adapter_is_registered_at_init(self):
        model = DualEncoder(self._make_config(), vocab_size=64)
        self.assertTrue(hasattr(model, "style_adapter"))
        self.assertIn("style_adapter.weight", model.state_dict())

    def test_apply_user_style_keeps_tensor_on_embedding_device(self):
        model = DualEncoder(self._make_config(), vocab_size=64)
        tone_embedding = torch.randn(1, 384)
        user_style = torch.randn(1, 64)

        styled = model._apply_user_style(tone_embedding, user_style)

        self.assertEqual(styled.device, tone_embedding.device)
        self.assertEqual(tuple(styled.shape), (1, 384))


if __name__ == "__main__":
    unittest.main()
