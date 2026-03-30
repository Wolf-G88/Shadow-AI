import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class AppPathTests(unittest.TestCase):
    def setUp(self):
        self.temp_home = tempfile.mkdtemp(prefix="shadow-ai-paths-")
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

    def test_windows_prefers_localappdata(self):
        from core import app_paths

        local_appdata = Path(self.temp_home) / "AppData" / "Local"
        path = app_paths._resolve_shadow_home(
            os_name="nt",
            home=Path(self.temp_home),
            localappdata=str(local_appdata),
            appdata="",
        )

        self.assertEqual(path, local_appdata / "Shadow AI")

    def test_unix_uses_hidden_shadow_dir(self):
        from core import app_paths

        path = app_paths._resolve_shadow_home(
            os_name="posix",
            home=Path(self.temp_home),
        )

        self.assertEqual(path, Path(self.temp_home) / ".shadow-ai")

    def test_runtime_components_share_same_base_dir(self):
        from core.app_paths import get_enhanced_learning_dir, get_memory_path, get_personalization_path, get_shadow_home
        from core.config import Config
        from core.enhanced_learning import EnhancedLearning
        from core.memory import MemoryBank
        from personalization.loop import PersonalizationLoop

        config = Config()
        memory = MemoryBank()
        learning = EnhancedLearning()
        profile = PersonalizationLoop(
            {
                "personalization": {
                    "ema_alpha": 0.85,
                    "style_dim": 64,
                }
            }
        )

        shadow_home = get_shadow_home()
        self.assertEqual(Path(config.config_path), shadow_home / "config.json")
        self.assertEqual(Path(memory.path), get_memory_path())
        self.assertEqual(Path(learning.data_dir), get_enhanced_learning_dir())
        self.assertEqual(profile.profile_path, get_personalization_path("default"))


if __name__ == "__main__":
    unittest.main()
