import json
import os
from .app_paths import get_config_path

class Config:
    def __init__(self):
        self.config_path = str(get_config_path())
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default config
        return {
            "backend": "shadow_tiny",  # shadow_tiny, sils, ollama, gguf, api
            "ollama_model": "gemma2:2b",
            "gguf_path": "",
            "api_provider": "local",
            "api_key": "",
            "custom_models": [],
            "debug": False,
            "dns_server": "1.1.1.1",
            "user_id": "default",
            "max_new_tokens": 256,
            "temperature": 0.7,
            "max_length": 512,
            "api_model": "gpt-4",
            "sils_model_path": "",
            "sils_tokenizer_path": "",
            "deadman_lock": True,
            "deadman_message": "ACCESS DENIED STOP WHILE YOU ARE AHEAD!"
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            if os.name != "nt":
                os.chmod(self.config_path, 0o600)  # Secure: owner read/write only
        except Exception as e:
            print(f"Could not save config: {e}")
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        self.save()
