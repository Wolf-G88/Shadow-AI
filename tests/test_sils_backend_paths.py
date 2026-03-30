import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class SILSBackendPathTests(unittest.TestCase):
    def test_finds_newest_runtime_artifact_pair(self):
        from core.sils_backend import SILSBackend

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            older = root / "older_run"
            newer = root / "newer_run"
            older.mkdir()
            newer.mkdir()

            older_model = older / "final_model.pt"
            older_tokenizer = older / "tokenizer_metadata.json"
            newer_model = newer / "final_model.pt"
            newer_tokenizer = newer / "tokenizer_metadata.json"

            older_model.write_text("old", encoding="utf-8")
            older_tokenizer.write_text("{}", encoding="utf-8")
            newer_model.write_text("new", encoding="utf-8")
            newer_tokenizer.write_text("{}", encoding="utf-8")

            os.utime(older_model, (1, 1))
            os.utime(newer_model, (2, 2))

            model_path, tokenizer_path = SILSBackend._find_training_artifacts(root)

            self.assertEqual(model_path, str(newer_model))
            self.assertEqual(tokenizer_path, str(newer_tokenizer))

    def test_prefers_best_model_within_newest_run(self):
        from core.sils_backend import SILSBackend

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "run"
            run_dir.mkdir()

            tokenizer = run_dir / "tokenizer_metadata.json"
            final_model = run_dir / "final_model.pt"
            best_model = run_dir / "best_model.pt"

            tokenizer.write_text("{}", encoding="utf-8")
            final_model.write_text("final", encoding="utf-8")
            best_model.write_text("best", encoding="utf-8")

            os.utime(tokenizer, (1, 1))
            os.utime(best_model, (2, 2))
            os.utime(final_model, (3, 3))

            model_path, tokenizer_path = SILSBackend._find_training_artifacts(root)

            self.assertEqual(model_path, str(best_model))
            self.assertEqual(tokenizer_path, str(tokenizer))


if __name__ == "__main__":
    unittest.main()
