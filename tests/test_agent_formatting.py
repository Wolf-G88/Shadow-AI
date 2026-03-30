import os
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class AgentFormattingTests(unittest.TestCase):
    def test_extract_agent_steps_from_numbered_lines(self):
        from core.agent_formatting import extract_agent_steps

        text = "1. Check repo status\n2. Review recent commits\n3. Decide next action"
        steps = extract_agent_steps(text)
        self.assertEqual(
            steps,
            ["Check repo status", "Review recent commits", "Decide next action"]
        )

    def test_format_agent_reply_adds_plan_and_commands(self):
        from core.agent_formatting import format_agent_reply

        reply = "Check repo status first. Then switch branches carefully. Use `!git status` and `!git checkout main`."
        formatted = format_agent_reply(reply)

        self.assertIn("Plan:", formatted)
        self.assertIn("Suggested Commands:", formatted)
        self.assertIn("`!git status`", formatted)
        self.assertIn("`!git checkout main`", formatted)

    def test_format_agent_reply_preserves_existing_sections(self):
        from core.agent_formatting import format_agent_reply

        reply = "Plan:\n1. Inspect files\n\nSuggested Commands:\n- `!ls -la`"
        self.assertEqual(format_agent_reply(reply), reply)


if __name__ == "__main__":
    unittest.main()
