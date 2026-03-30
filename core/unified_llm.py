# Lazy import to avoid hard crashes if ollama not installed
import os
import requests
from .model_version_detector import detect_model_version

class UnifiedLLM:
    def __init__(self, config):
        self.config = config
        self.ollama_client = None  # Lazy load
        self.gguf_model = None
        self.shadow_tiny_backend = None  # Lazy loading
        self.sils_backend = None  # SILS v1 backend
        self.detected_versions = {}  # Cache for auto-detected versions

    def _get_sils_backend(self):
        """Lazy-load and return the SILS backend."""
        if self.sils_backend is None:
            from .sils_backend import SILSBackend

            model_path = self.config.get("sils_model_path")
            tokenizer_path = self.config.get("sils_tokenizer_path")
            user_id = self.config.get("user_id", "default")

            self.sils_backend = SILSBackend(
                model_path=model_path,
                tokenizer_path=tokenizer_path,
                user_id=user_id
            )
        return self.sils_backend
        
    def generate(self, prompt, images=None):
        backend = self.config.get("backend", "shadow_tiny")  # Default to Shadow Tiny LM
        
        if backend == "sils":
            return self._generate_sils(prompt)
        elif backend == "shadow_tiny":
            return self._generate_shadow_tiny(prompt)
        elif backend == "ollama":
            return self._generate_ollama(prompt, images)
        elif backend == "gguf":
            return self._generate_gguf(prompt)
        elif backend == "api":
            return self._generate_api(prompt)
        else:
            return "Error: Unknown backend"
    
    def _generate_sils(self, prompt):
        """Generate using SILS v1 - complete dual-encoder system."""
        try:
            self._get_sils_backend()
            
            if not self.sils_backend.is_available():
                return "SILS backend not ready. Train model or switch to another backend."
            
            response = self.sils_backend.generate(
                prompt,
                max_new_tokens=self.config.get("max_new_tokens", 50),  # Generate 50 NEW tokens
                temperature=self.config.get("temperature", 0.8)  # Higher temp for creativity
            )
            return response
        except Exception as e:
            return f"SILS error: {str(e)}"

    def predict_intent(self, prompt):
        """Predict intent via SILS when a trained runtime model is available."""
        try:
            backend = self._get_sils_backend()
            if not backend.is_available():
                return None
            return backend.predict_intent(prompt)
        except Exception:
            return None
    
    def _generate_shadow_tiny(self, prompt):
        """Generate using Shadow Tiny LM - lean base model."""
        try:
            # Lazy load Shadow Tiny LM
            if self.shadow_tiny_backend is None:
                from .shadow_tiny_lm import ShadowTinyLMBackend
                self.shadow_tiny_backend = ShadowTinyLMBackend()
            
            if not self.shadow_tiny_backend.is_available():
                # Fallback to Ollama if Shadow Tiny not available
                return "Shadow Tiny LM not available. Switch to another backend."
            
            response = self.shadow_tiny_backend.generate(
                prompt,
                max_length=self.config.get("max_length", 100),
                temperature=self.config.get("temperature", 0.7)
            )
            return response
        except Exception as e:
            return f"Shadow Tiny LM error: {str(e)}"
    
    def _generate_ollama(self, prompt, images=None):
        try:
            # Lazy load ollama client
            if self.ollama_client is None:
                from ollama import Client
                self.ollama_client = Client(host='http://localhost:11434')
            
            model = self.config.get("ollama_model", "gemma2:2b")
            if images:
                response = self.ollama_client.generate(model=model, prompt=prompt, images=images)
            else:
                response = self.ollama_client.generate(model=model, prompt=prompt)
            
            if isinstance(response, dict):
                return response.get('response', '')
            elif hasattr(response, 'response'):
                return response.response
            else:
                return str(response)
        except Exception as e:
            return f"Ollama error: {str(e)}"
    
    def _generate_gguf(self, prompt):
        try:
            # Load model lazily
            if self.gguf_model is None:
                from llama_cpp import Llama
                gguf_path = self.config.get("gguf_path", "")
                if not gguf_path or not os.path.exists(gguf_path):
                    return "Error: No valid GGUF model loaded"
                
                self.gguf_model = Llama(model_path=gguf_path, n_ctx=2048, n_threads=2)
            
            output = self.gguf_model(prompt, max_tokens=512, stop=["User:", "\n\n\n"], echo=False)
            return output['choices'][0]['text'].strip()
        except Exception as e:
            return f"GGUF error: {str(e)}"
    
    def _generate_api(self, prompt):
        provider = self.config.get("api_provider", "local")
        api_key = self.config.get("api_key", "")
        
        if not api_key:
            return "Error: No API key configured"
        
        try:
            if provider == "grok":
                response, headers = self._call_grok(prompt, api_key)
            elif provider == "openai":
                response, headers = self._call_openai(prompt, api_key)
            elif provider == "claude":
                response, headers = self._call_claude(prompt, api_key)
            elif provider == "gemini":
                response, headers = self._call_gemini(prompt, api_key)
            elif provider in ["mistral", "cohere", "together", "perplexity", "groq", "deepseek", "huggingface", "openrouter", "anyscale", "fireworks"]:
                response, headers = self._call_openai_compatible(prompt, api_key, provider)
            else:
                return "Error: Unsupported API provider"
            
            # Auto-detect model version if not already known
            if provider not in self.detected_versions:
                detected = detect_model_version(provider, response, headers)
                if detected:
                    self.detected_versions[provider] = detected
                    print(f"Auto-detected {provider} model: {detected}")
            
            return response
        except Exception as e:
            return f"API error: {str(e)}"
    
    def _call_grok(self, prompt, api_key):
        # Grok uses OpenAI-compatible API
        # Use whatever model user configured, no default forcing
        model = self.config.get("api_model", "grok-beta")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048
        }
        response = requests.post("https://api.x.ai/v1/chat/completions", 
                               headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'], dict(response.headers)
    
    def _call_openai(self, prompt, api_key):
        model = self.config.get("api_model", "gpt-4")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048
        }
        response = requests.post("https://api.openai.com/v1/chat/completions",
                               headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'], dict(response.headers)
    
    def _call_claude(self, prompt, api_key):
        model = self.config.get("api_model", "claude-3-5-sonnet-20241022")
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post("https://api.anthropic.com/v1/messages",
                               headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()['content'][0]['text'], dict(response.headers)
    
    def _call_gemini(self, prompt, api_key):
        model = self.config.get("api_model", "gemini-pro")
        
        # Use v1beta for newer models like gemini-1.5-pro, gemini-1.5-flash
        api_version = "v1beta" if "1.5" in model else "v1"
        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text'], dict(response.headers)
    
    def _call_openai_compatible(self, prompt, api_key, provider):
        """Generic handler for OpenAI-compatible APIs."""
        model = self.config.get("api_model", "default")
        
        # Map provider to base URL
        provider_urls = {
            "mistral": "https://api.mistral.ai/v1/chat/completions",
            "cohere": "https://api.cohere.ai/v1/chat",
            "together": "https://api.together.xyz/v1/chat/completions",
            "perplexity": "https://api.perplexity.ai/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "huggingface": "https://api-inference.huggingface.co/models/" + model,
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "anyscale": "https://api.endpoints.anyscale.com/v1/chat/completions",
            "fireworks": "https://api.fireworks.ai/inference/v1/chat/completions"
        }
        
        url = provider_urls.get(provider)
        if not url:
            return f"Error: Unknown provider {provider}"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        # Most providers use OpenAI-compatible response format
        result = response.json()
        if 'choices' in result:
            return result['choices'][0]['message']['content'], dict(response.headers)
        elif 'text' in result:  # Some providers might use this
            return result['text'], dict(response.headers)
        else:
            return str(result), dict(response.headers)
    
    def get_detected_version(self, provider):
        """Get auto-detected model version for provider."""
        return self.detected_versions.get(provider, "Unknown")
    
    def list_models(self):
        model_list = []
        
        # Add TinyLM (SILS) if available
        try:
            from core.sils_backend import SILSBackend
            sils = SILSBackend()
            status = sils.get_status()
            if status.get("status") == "ready" and status.get("model"):
                model_list.append(status["model"])
        except Exception as e:
            print(f"SILS not available: {e}")
        
        # Add Ollama models
        try:
            models = self.ollama_client.list()
            if hasattr(models, 'models'):
                model_list.extend([m.model if hasattr(m, 'model') else m.get('model', m.get('name', str(m))) for m in models.models])
            elif isinstance(models, dict) and 'models' in models:
                model_list.extend([m.get('model', m.get('name', str(m))) for m in models['models']])
        except Exception as e:
            print(f"Error listing Ollama models: {e}")
        
        return model_list if model_list else []
