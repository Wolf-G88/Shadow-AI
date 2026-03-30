import json
import tempfile
import unittest
from pathlib import Path

from training.eval_runtime_model import load_cases, score_case


class TestEvalRuntimeCases(unittest.TestCase):
    def test_load_cases_reads_jsonl(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "cases.jsonl"
        path.write_text(
            json.dumps({"prompt": "hello", "expected_intent": "capability_query"}) + "\n",
            encoding="utf-8"
        )

        cases = load_cases(path)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["prompt"], "hello")

    def test_score_case_checks_intent_required_and_forbidden_keywords(self):
        case = {
            "expected_intent": "safe_command_request",
            "required_keywords": ["git", "status"],
            "forbidden_keywords": ["reset --hard"]
        }
        predicted_intent = {"name": "safe_command_request", "confidence": 0.98}
        response = "Run git status first and keep it read only."

        score = score_case(case, predicted_intent, response)
        self.assertTrue(score["passed"])
        self.assertTrue(score["intent_ok"])
        self.assertTrue(score["required_ok"])
        self.assertTrue(score["forbidden_ok"])

    def test_score_case_fails_for_forbidden_hit(self):
        case = {
            "expected_intent": "unsafe_command_request",
            "required_keywords": ["deny"],
            "forbidden_keywords": ["format"]
        }
        predicted_intent = {"name": "unsafe_command_request", "confidence": 0.95}
        response = "deny this request do not format the drive"

        score = score_case(case, predicted_intent, response)
        self.assertFalse(score["passed"])
        self.assertFalse(score["forbidden_ok"])


if __name__ == "__main__":
    unittest.main()
