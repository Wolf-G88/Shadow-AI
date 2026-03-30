import json
import os
from .app_paths import get_memory_path

class MemoryBank:
    def __init__(self, path=None):
        if path is None:
            path = str(get_memory_path())
        self.path = path
        self.history = []

    def append(self, user_msg, assistant_msg):
        self.history.append({"user": user_msg, "assistant": assistant_msg})
        self.save()  # Auto-persist after each message

    def get_recent(self, n=10):
        recent = self.history[-n:]
        return "\n".join([f"User: {ex['user']}\nAssistant: {ex['assistant']}" for ex in recent])

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"Load error: {e}")

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
            if os.name != "nt":
                os.chmod(self.path, 0o600)  # Secure: owner read/write only
        except Exception as e:
            print(f"Save error: {e}")
