import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class EngineTaskRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp_home = tempfile.mkdtemp(prefix="shadow-ai-test-home-")
        self.old_home = os.environ.get("HOME")
        self.old_userprofile = os.environ.get("USERPROFILE")
        os.environ["HOME"] = self.temp_home
        os.environ["USERPROFILE"] = self.temp_home

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.old_home

        if self.old_userprofile is None:
            os.environ.pop("USERPROFILE", None)
        else:
            os.environ["USERPROFILE"] = self.old_userprofile

        shutil.rmtree(self.temp_home, ignore_errors=True)

    def _make_core(self):
        from core.engine import ShadowCore
        from core.memory import MemoryBank

        memory_path = os.path.join(self.temp_home, "memory.json")
        memory = MemoryBank(path=memory_path)
        return ShadowCore(memory)

    def test_task_recipe_is_included_only_in_generation_fallback(self):
        from core.agent_recipes import detect_agent_recipe

        core = self._make_core()
        core.config.set("backend", "api")
        core.llm.predict_intent = lambda text: None
        core.learning.extract_and_learn = lambda text: None
        core.learning.is_question = lambda text: True
        core.learning.answer_question = lambda text: None
        core.learning.search_knowledge = lambda *args, **kwargs: []
        core.recognition.recognize = lambda text, learning: (None, 0.0, None)
        core.external.should_reach_out = lambda confidence, threshold=0.3: False
        core.llm.generate = lambda prompt, images=None: prompt

        recipe = detect_agent_recipe("debug this crash")
        response = core.process("debug this crash", task_recipe=recipe, agent_mode=True)

        self.assertIn("[Task Recipe: Debug and Troubleshoot]", response)
        self.assertIn("Agent Mode is active.", response)
        self.assertIn("User: debug this crash", response)

    def test_task_recipe_does_not_override_local_recognition(self):
        from core.agent_recipes import detect_agent_recipe

        core = self._make_core()
        core.config.set("backend", "api")
        core.llm.predict_intent = lambda text: None
        core.learning.extract_and_learn = lambda text: None
        core.learning.is_question = lambda text: True
        core.learning.answer_question = lambda text: None
        core.learning.search_knowledge = lambda *args, **kwargs: []
        core.recognition.recognize = lambda text, learning: ("Local answer", 0.95, "capability")
        core.external.should_reach_out = mock.Mock(side_effect=AssertionError("should not reach external"))
        core.llm.generate = mock.Mock(side_effect=AssertionError("should not generate"))

        recipe = detect_agent_recipe("do a project audit and tell me what's weak")
        response = core.process("what can shadow do", task_recipe=recipe, agent_mode=True)

        self.assertEqual(response, "Local answer")
        core.external.should_reach_out.assert_not_called()
        core.llm.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
