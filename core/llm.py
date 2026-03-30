from ollama import Client
import os

class LocalLLM:
    def __init__(self, model_name="gemma2:2b"):
        self.client = Client(host='http://localhost:11434')  # Ollama default
        self.model = model_name

    def generate(self, prompt, images=None):
        try:
            if images:
                # For vision models like llava
                response = self.client.generate(model=self.model, prompt=prompt, images=images)
            else:
                # For text-only models
                response = self.client.generate(model=self.model, prompt=prompt)
            
            # Handle different response formats
            if isinstance(response, dict):
                return response.get('response', '')
            elif hasattr(response, 'response'):
                return response.response
            else:
                return str(response)
        except Exception as e:
            print(f"Generate error: {e}")
            return f"Error: {str(e)}"

    def list_models(self):
        try:
            models = self.client.list()
            if hasattr(models, 'models'):
                return [m.model if hasattr(m, 'model') else m.get('model', m.get('name', str(m))) for m in models.models]
            elif isinstance(models, dict) and 'models' in models:
                return [m.get('model', m.get('name', str(m))) for m in models['models']]
            else:
                # Fallback: return empty list if structure is unexpected
                return []
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
