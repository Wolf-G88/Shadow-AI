import os
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class ShellSafetyTests(unittest.TestCase):
    def test_safe_command_assessment(self):
        from core.shell_safety import assess_command_risk

        risk = assess_command_risk("git status")
        self.assertEqual(risk["level"], "safe")
        self.assertEqual(risk["profile"], "readonly")
        self.assertFalse(risk["confirm"])

    def test_critical_command_assessment(self):
        from core.shell_safety import assess_command_risk

        risk = assess_command_risk("rm -rf /")
        self.assertEqual(risk["level"], "critical")

    def test_shell_metacharacters_escalate_to_high(self):
        from core.shell_safety import assess_command_risk

        risk = assess_command_risk("echo hi && whoami")
        self.assertEqual(risk["level"], "high")
        self.assertTrue(risk["confirm"])

    def test_python_script_execution_requires_confirmation(self):
        from core.shell_safety import assess_command_risk

        risk = assess_command_risk("python my_script.py")
        self.assertEqual(risk["level"], "medium")
        self.assertEqual(risk["profile"], "mutating")
        self.assertTrue(risk["confirm"])

    def test_git_write_operation_requires_confirmation(self):
        from core.shell_safety import assess_command_risk

        risk = assess_command_risk("git checkout main")
        self.assertEqual(risk["level"], "medium")
        self.assertTrue(risk["confirm"])

    def test_build_exec_plan_prefers_direct_for_simple_command(self):
        from core.shell_safety import build_exec_plan

        plan = build_exec_plan("python script.py --help")
        self.assertEqual(plan["mode"], "direct")
        self.assertEqual(plan["argv"][0].lower(), "python")

    def test_build_exec_plan_uses_shell_for_chained_command(self):
        from core.shell_safety import build_exec_plan

        plan = build_exec_plan("echo hi | findstr hi")
        self.assertEqual(plan["mode"], "shell")
        self.assertIsNone(plan["argv"])

    def test_build_exec_plan_uses_shell_for_cd_builtin(self):
        from core.shell_safety import build_exec_plan

        plan = build_exec_plan("cd ..")
        self.assertEqual(plan["mode"], "shell")

    def test_extract_bang_commands_finds_inline_and_line_commands(self):
        from core.shell_safety import extract_bang_commands

        text = "Try `!git status` first.\nThen run:\n!python script.py --help\n"
        commands = extract_bang_commands(text)
        self.assertEqual(commands, ["git status", "python script.py --help"])

    def test_summarize_command_policies_builds_action_review(self):
        from core.shell_safety import summarize_command_policies

        summary = summarize_command_policies("Use `!git status` then `!git checkout main`.")
        self.assertIsNotNone(summary)
        self.assertIn("[Action Review]", summary)
        self.assertIn("!git status -> readonly | run", summary)
        self.assertIn("!git checkout main -> mutating | confirm", summary)


if __name__ == "__main__":
    unittest.main()
