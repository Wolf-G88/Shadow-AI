import os
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class _DummySILSBackend:
    def __init__(self, available=True, prediction=None):
        self._available = available
        self._prediction = prediction

    def is_available(self):
        return self._available

    def predict_intent(self, prompt):
        return self._prediction


class UnifiedLLMIntentTests(unittest.TestCase):
    def test_predict_intent_delegates_to_sils_backend(self):
        from core.unified_llm import UnifiedLLM

        llm = UnifiedLLM({})
        llm.sils_backend = _DummySILSBackend(
            available=True,
            prediction={"name": "capability_query", "confidence": 0.9}
        )

        prediction = llm.predict_intent("what can shadow do")
        self.assertEqual(prediction["name"], "capability_query")

    def test_predict_intent_returns_none_when_backend_unavailable(self):
        from core.unified_llm import UnifiedLLM

        llm = UnifiedLLM({})
        llm.sils_backend = _DummySILSBackend(available=False, prediction=None)

        self.assertIsNone(llm.predict_intent("what can shadow do"))


if __name__ == "__main__":
    unittest.main()
