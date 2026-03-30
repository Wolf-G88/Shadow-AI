import os
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class AgentRecipeTests(unittest.TestCase):
    def test_detects_repo_recipe(self):
        from core.agent_recipes import detect_agent_recipe

        recipe = detect_agent_recipe("review this repo and tell me the project structure")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "repo_review")

    def test_detects_file_recipe_from_attachments(self):
        from core.agent_recipes import detect_agent_recipe

        recipe = detect_agent_recipe("help me understand this", has_attachments=True)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "file_triage")

    def test_detects_environment_recipe(self):
        from core.agent_recipes import detect_agent_recipe

        recipe = detect_agent_recipe("check my python environment and installed deps")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "environment_check")

    def test_detects_debug_recipe(self):
        from core.agent_recipes import detect_agent_recipe

        recipe = detect_agent_recipe("debug this crash and traceback for me")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "debug_troubleshoot")

    def test_detects_project_audit_recipe(self):
        from core.agent_recipes import detect_agent_recipe

        recipe = detect_agent_recipe("do a project audit and tell me what's weak")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "project_audit")

    def test_build_agent_prompt_includes_recipe_header(self):
        from core.agent_recipes import build_agent_prompt

        prompt = build_agent_prompt("review this repo for me")
        self.assertIn("[Agent Recipe: Repository Review]", prompt)
        self.assertIn("Prefer a fast local inspection flow.", prompt)

    def test_build_agent_prompt_falls_back_without_recipe(self):
        from core.agent_recipes import build_agent_prompt

        prompt = build_agent_prompt("just think through this with me")
        self.assertNotIn("[Agent Recipe:", prompt)
        self.assertIn("You are in Agent Mode.", prompt)

    def test_build_agent_prompt_includes_debug_recipe_header(self):
        from core.agent_recipes import build_agent_prompt

        prompt = build_agent_prompt("debug this failing test")
        self.assertIn("[Agent Recipe: Debug and Troubleshoot]", prompt)
        self.assertIn("careful debugging pass", prompt)

    def test_format_task_recipe_notice_for_non_agent_mode(self):
        from core.agent_recipes import detect_agent_recipe, format_task_recipe_notice

        recipe = detect_agent_recipe("do a project audit and tell me what's weak")
        notice = format_task_recipe_notice(recipe, agent_mode=False)

        self.assertEqual(
            notice,
            "[Task Recipe] Project Audit - Treat this like a high-signal project audit."
        )

    def test_format_task_recipe_notice_for_agent_mode(self):
        from core.agent_recipes import detect_agent_recipe, format_task_recipe_notice

        recipe = detect_agent_recipe("debug this crash and traceback for me")
        notice = format_task_recipe_notice(recipe, agent_mode=True)

        self.assertEqual(
            notice,
            "[Agent Recipe] Debug and Troubleshoot - Treat this like a careful debugging pass."
        )

    def test_format_task_recipe_status_with_recipe_in_agent_mode(self):
        from core.agent_recipes import detect_agent_recipe, format_task_recipe_status

        recipe = detect_agent_recipe("review this repo and tell me the project structure")
        status = format_task_recipe_status(recipe, agent_mode=True)

        self.assertEqual(status, "Agent Mode: Repository Review")

    def test_format_task_recipe_status_with_recipe_in_normal_mode(self):
        from core.agent_recipes import detect_agent_recipe, format_task_recipe_status

        recipe = detect_agent_recipe("do a project audit and tell me what's weak")
        status = format_task_recipe_status(recipe, agent_mode=False)

        self.assertEqual(status, "Shadow is thinking... [Project Audit]")

    def test_format_task_recipe_status_without_recipe(self):
        from core.agent_recipes import format_task_recipe_status

        self.assertEqual(format_task_recipe_status(None, agent_mode=True), "Agent Mode: ON")
        self.assertEqual(format_task_recipe_status(None, agent_mode=False), "Shadow is thinking...")


if __name__ == "__main__":
    unittest.main()
