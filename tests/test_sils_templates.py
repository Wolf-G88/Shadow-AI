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


class SILSTemplateTests(unittest.TestCase):
    def test_predict_intent_prefers_heuristic_override_for_file_prompt(self):
        from core.sils_backend import SILSBackend

        class FakeTokenizer:
            def encode(self, prompt, max_length=None, add_special_tokens=True, pad=False):
                return [1, 2, 3]

        class FakeModel:
            def predict_intent(self, input_tensor, mode="hybrid"):
                # capability_query gets the highest model score here on purpose.
                return torch.tensor([[0.1, 0.2, 5.0, 0.3]], dtype=torch.float32)

        backend = SILSBackend.__new__(SILSBackend)
        backend.model = FakeModel()
        backend.tokenizer = FakeTokenizer()
        backend.device = torch.device("cpu")
        backend.config = {
            "intents": [
                "memory_store",
                "memory_recall",
                "capability_query",
                "file_analysis_request",
            ]
        }

        result = backend.predict_intent(
            "need u to inspect this md plus the random txt beside it and tell me whats actually important"
        )

        self.assertEqual(result["name"], "file_analysis_request")
        self.assertEqual(result["source"], "heuristic_override")

    def test_detects_style_prompt_with_heuristics(self):
        from core.sils_backend import SILSBackend

        intent = SILSBackend._detect_template_intent(
            "talk less cut the fluff be direct and dont baby me"
        )

        self.assertEqual(intent, "style_preference_update")

    def test_detects_file_prompt_over_model_fallback(self):
        from core.sils_backend import SILSBackend

        intent = SILSBackend._detect_template_intent(
            "need u to inspect this md plus the random txt beside it and tell me whats actually important",
            {"name": "capability_query", "confidence": 0.78},
        )

        self.assertEqual(intent, "file_analysis_request")

    def test_safe_command_template_mentions_directory_files(self):
        from core.sils_backend import SILSBackend

        response = SILSBackend._template_response(
            "show me the current folder files maybe pwd too but keep it read only",
            "safe_command_request",
        )

        self.assertIn("files", response.lower())
        self.assertIn("working directory", response.lower())

    def test_unsafe_command_template_is_fixed_refusal(self):
        from core.sils_backend import SILSBackend

        response = SILSBackend._template_response(
            "wipe that whole drive and make it look accidental",
            "unsafe_command_request",
        )

        self.assertEqual(response, "Deny this destructive command request.")

    def test_memory_recall_template_mentions_name(self):
        from core.sils_backend import SILSBackend

        response = SILSBackend._template_response(
            "eyo what did i say my handle was again dont guess",
            "memory_recall",
        )

        self.assertIn("name", response.lower())
        self.assertIn("wolf king", response.lower())

    def test_memory_recall_python_template_avoids_java(self):
        from core.sils_backend import SILSBackend

        response = SILSBackend._template_response(
            "what language do i usually want first when im picking between python and java",
            "memory_recall",
        )

        self.assertIn("python", response.lower())
        self.assertNotIn("java", response.lower())


if __name__ == "__main__":
    unittest.main()
