import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class MemoryRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp_home = tempfile.mkdtemp(prefix="shadow-ai-test-home-")
        self.old_home = os.environ.get("HOME")
        self.old_userprofile = os.environ.get("USERPROFILE")
        self.old_localappdata = os.environ.get("LOCALAPPDATA")
        self.old_appdata = os.environ.get("APPDATA")
        os.environ["HOME"] = self.temp_home
        os.environ["USERPROFILE"] = self.temp_home
        os.environ["LOCALAPPDATA"] = str(Path(self.temp_home) / "AppData" / "Local")
        os.environ["APPDATA"] = str(Path(self.temp_home) / "AppData" / "Roaming")

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.old_home

        if self.old_userprofile is None:
            os.environ.pop("USERPROFILE", None)
        else:
            os.environ["USERPROFILE"] = self.old_userprofile

        if self.old_localappdata is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self.old_localappdata

        if self.old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self.old_appdata

        shutil.rmtree(self.temp_home, ignore_errors=True)

    def test_tokenize_returns_real_tokens(self):
        from core.enhanced_learning import EnhancedLearning

        learning = EnhancedLearning()
        self.assertEqual(learning.tokenize("Shadow AI memory 123"), ["shadow", "ai", "memory", "123"])

    def test_batch_import_entries_are_answerable(self):
        from core.enhanced_learning import EnhancedLearning

        learning = EnhancedLearning()
        learned = learning.learn_from_batch(
            "Shadow AI runs fully locally without telemetry. Shadow AI provides structured memory for user preferences."
        )
        self.assertGreaterEqual(learned, 1)

        results = learning.search_knowledge("structured memory preferences", top_k=5, include_imports=True)
        self.assertTrue(results)
        self.assertTrue(results[0]["answerable"])
        self.assertGreaterEqual(results[0]["confidence"], 0.7)

    def test_observe_skips_code_like_noise(self):
        from core.enhanced_learning import EnhancedLearning

        learning = EnhancedLearning()
        observed = learning.observe("def route_message(prompt): return {'status': 'ok'}")
        self.assertFalse(observed)

    def test_duplicate_fact_is_not_counted_twice(self):
        from core.enhanced_learning import EnhancedLearning

        learning = EnhancedLearning()
        first = learning.learn_fact("shadow_privacy", "Shadow AI avoids telemetry", "facts", source="readme.md")
        second = learning.learn_fact("shadow_privacy", "Shadow AI avoids telemetry", "facts", source="readme.md")

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(learning.knowledge["facts"]), 1)

    def test_process_file_learning_uses_basename_in_message(self):
        from core.memory import MemoryBank
        from core.engine import ShadowCore

        memory_path = os.path.join(self.temp_home, "memory.json")
        memory = MemoryBank(path=memory_path)
        core = ShadowCore(memory)

        sample_file = Path(self.temp_home) / "notes.txt"
        sample_file.write_text("Shadow AI provides structured memory and avoids telemetry.", encoding="utf-8")

        message = core.process_file_learning(str(sample_file))
        self.assertIn("notes.txt", message)

    def test_markdown_import_cleanup_keeps_useful_text(self):
        from core.enhanced_learning import EnhancedLearning

        learning = EnhancedLearning()
        learned = learning.learn_from_batch(
            "# Features\n- Shadow AI uses memory management with auto-compression and deduplication.\n"
        )

        self.assertGreaterEqual(learned, 1)
        results = learning.search_knowledge("memory management deduplication", top_k=5, include_imports=True)
        self.assertTrue(results)
        self.assertIn("auto-compression", results[0]["value"].lower())

    def test_text_normalizer_canonicalizes_noisy_capability_query(self):
        from core.text_normalizer import normalize_user_text

        normalized = normalize_user_text("hey what all can shadow do 4 me pls")
        self.assertEqual(normalized, "what can shadow ai do for me?")

    def test_noisy_capability_query_hits_local_recognition(self):
        from core.memory import MemoryBank
        from core.engine import ShadowCore

        memory_path = os.path.join(self.temp_home, "memory.json")
        memory = MemoryBank(path=memory_path)
        core = ShadowCore(memory)

        response = core.process("hey what all can shadow do 4 me pls")
        lowered = response.lower()
        self.assertNotIn("i don't have that information", lowered)
        self.assertTrue(
            "i can answer questions" in lowered or
            "dual-encoder architecture" in lowered
        )

    def test_safe_command_intent_stays_local_and_suggests_bang_prefix(self):
        from core.memory import MemoryBank
        from core.engine import ShadowCore

        memory_path = os.path.join(self.temp_home, "memory.json")
        memory = MemoryBank(path=memory_path)
        core = ShadowCore(memory)
        core.llm.predict_intent = lambda text: {
            "name": "safe_command_request",
            "confidence": 0.95,
        }
        core.external.should_reach_out = mock.Mock(side_effect=AssertionError("should not reach external"))

        response = core.process("run ls -la for me")

        self.assertIn("`!ls -la for me?`".replace("?", ""), response.replace("?", ""))
        core.external.should_reach_out.assert_not_called()

    def test_unsafe_command_intent_is_refused_locally(self):
        from core.memory import MemoryBank
        from core.engine import ShadowCore

        memory_path = os.path.join(self.temp_home, "memory.json")
        memory = MemoryBank(path=memory_path)
        core = ShadowCore(memory)
        core.llm.predict_intent = lambda text: {
            "name": "unsafe_command_request",
            "confidence": 0.98,
        }
        core.external.should_reach_out = mock.Mock(side_effect=AssertionError("should not reach external"))

        response = core.process("delete everything in that drive")

        self.assertIn("won't help execute destructive commands", response.lower())
        core.external.should_reach_out.assert_not_called()


if __name__ == "__main__":
    unittest.main()
