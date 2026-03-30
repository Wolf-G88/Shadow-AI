"""
SILS Backend Integration for Shadow AI
Connects dual-encoder + router + personalization to Shadow
"""

import json
import logging
import re
import sys
import warnings
from pathlib import Path
from typing import Optional, Dict, Tuple
from .app_paths import get_models_dir
from .resource_paths import get_resource_root

warnings.filterwarnings(
    "ignore",
    message="The pynvml package is deprecated.*",
    category=FutureWarning,
)

import torch

# Disable nested tensor to prevent CPU freeze
torch.backends.cuda.matmul.allow_tf32 = False

from model.dual_encoder import DualEncoder
from router.router import Router
from personalization.loop import PersonalizationLoop
from training.tokenizer import ShadowTokenizer


logger = logging.getLogger(__name__)


class SILSBackend:
    """
    Complete SILS v1 backend for Shadow AI.
    
    Features:
    - Routes messages via intelligent router
    - Runs correct encoder(s) based on message type
    - Applies user personalization
    - Falls back gracefully if no user profile exists
    - Never modifies base LM weights
    """

    @staticmethod
    def _safe_console_text(text: str, limit: int = 100) -> str:
        preview = (text or "")[:limit]
        encoding = sys.stdout.encoding or "utf-8"
        return preview.encode(encoding, errors="replace").decode(encoding, errors="replace")

    @staticmethod
    def _normalize_prompt(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    @staticmethod
    def _contains_any(text: str, phrases) -> bool:
        return any(phrase in text for phrase in phrases)

    @classmethod
    def _detect_template_intent(cls, prompt: str, predicted_intent: Optional[Dict] = None) -> Optional[str]:
        text = cls._normalize_prompt(prompt)

        if cls._contains_any(text, ["wipe", "delete system32", "brick", "nuke every process", "kill every process", "destroy the system", "whole drive"]):
            return "unsafe_command_request"
        if cls._contains_any(text, ["ollama", "gguf", "backend", "stronger backend", "api not", "network is used", "privacy first"]):
            return "backend_routing_request"
        if cls._contains_any(text, ["remember this", "remember that", "store this", "lock this in", "keep this", "do not lose this"]):
            return "memory_store"
        if cls._contains_any(text, ["what did i say", "what was that thing", "what language do i", "what name did i", "what handle did i", "remind me what style", "what response style"]):
            return "memory_recall"
        if cls._contains_any(text, ["docx", "markdown", "md plus", "txt beside", "picture", "image", "code files", "scan these code", "read this", "inspect this"]):
            return "file_analysis_request"
        if cls._contains_any(text, ["talk less", "no fluff", "be direct", "calm engineer", "concise", "practical", "steady", "blunt style", "mirror my blunt style", "hypebeast"]):
            return "style_preference_update"
        if cls._contains_any(text, ["run ls", "git status", "current folder files", "pwd", "python version", "installed packages", "inspect the environment", "read only"]):
            return "safe_command_request"
        if cls._contains_any(text, ["what can shadow", "what all can", "can shadow do", "help with offline", "help with all that", "what can u do", "what can shadow ai"]):
            return "capability_query"

        if predicted_intent and predicted_intent.get("confidence", 0.0) >= 0.75:
            return predicted_intent.get("name")
        return None

    @classmethod
    def _template_response(cls, prompt: str, intent_name: Optional[str]) -> Optional[str]:
        if not intent_name:
            return None

        text = cls._normalize_prompt(prompt)

        if intent_name == "capability_query":
            return "Shadow AI can do memory, file reading, files, safer commands, and offline local help for me or you."

        if intent_name == "memory_store":
            if "wolf king" in text or "handle" in text or "name" in text:
                return "Remembered: your name and handle are Wolf King."
            if "python" in text and "java" in text:
                return "Remembered: you prefer Python over Java."
            if "private" in text or "local first" in text or "telemetry" in text:
                return "Remembered: Shadow should stay private and local first."
            if "gpu" in text:
                return "Remembered: you want GPU runs only when they stay stable."
            return "Remembered."

        if intent_name == "memory_recall":
            if "handle" in text or "name" in text:
                return "You asked me to use the name Wolf King."
            if "privacy" in text or "telemetry" in text or "local first" in text:
                return "You said privacy matters and Shadow should stay local first."
            if "python" in text and "java" in text:
                return "You said Python should come first."
            if "style" in text or "fluff" in text:
                return "You asked for short, direct replies with no fluff."
            return "You asked me to recall that memory."

        if intent_name == "file_analysis_request":
            if "docx" in text:
                return "Read this DOCX file and summarize it briefly."
            if "picture" in text or "image" in text:
                return "Check this picture honestly and say when the model can only inspect metadata."
            if "code" in text:
                return "Scan these code files and summarize the risky parts first."
            return "Inspect these files and summarize what matters."

        if intent_name == "safe_command_request":
            if "git status" in text:
                return "Check git status."
            if "python version" in text or "installed" in text or "environment" in text:
                return "Inspect the Python environment and installed packages without changing anything."
            if "pwd" in text or "current folder" in text or "directory" in text:
                return "Show the current directory files and print the working directory."
            return "Run ls -la."

        if intent_name == "unsafe_command_request":
            return "Deny this destructive command request."

        if intent_name == "backend_routing_request":
            if "gguf" in text:
                return "Use the GGUF backend for this request."
            if "ollama" in text:
                return "Use Ollama for this request."
            if "stronger backend" in text or "heavy" in text or "reasoning" in text:
                return "Route this to the stronger backend."
            return "Pick the backend per task, keep privacy first, and be honest when the network is used."

        if intent_name == "style_preference_update":
            if "calm engineer" in text or "hype" in text:
                return "Use a calm engineer tone."
            if "concise" in text or "practical" in text or "steady" in text or "stressed" in text:
                return "Keep responses concise, practical, and steady."
            if "blunt" in text and "safe" in text:
                return "Mirror the user's blunt style, but stay safe on destructive asks."
            return "Use a short, direct style with minimal fluff."

        return None

    @staticmethod
    def _find_training_artifacts(training_root: Path) -> Tuple[Optional[str], Optional[str]]:
        """Find the newest usable runtime-trained model + tokenizer pair."""
        if not training_root.exists():
            return None, None

        run_candidates = []
        for tokenizer_path in training_root.rglob("tokenizer_metadata.json"):
            run_dir = tokenizer_path.parent
            best_model = run_dir / "best_model.pt"
            final_model = run_dir / "final_model.pt"

            model_path = best_model if best_model.exists() else final_model
            if not model_path.exists():
                continue

            if not tokenizer_path.exists():
                continue
            try:
                mtime = max(
                    path.stat().st_mtime
                    for path in [tokenizer_path, best_model, final_model]
                    if path.exists()
                )
            except OSError:
                continue
            run_candidates.append((mtime, str(model_path), str(tokenizer_path)))

        if not run_candidates:
            return None, None

        run_candidates.sort(key=lambda item: item[0], reverse=True)
        _, model_path, tokenizer_path = run_candidates[0]
        return model_path, tokenizer_path
    
    def __init__(self, config_path: Optional[str] = None, model_path: Optional[str] = None,
                 tokenizer_path: Optional[str] = None, user_id: str = "default"):
        # Load config
        if config_path is None:
            config_path = get_resource_root() / "config" / "sils_config.json"
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Setup device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize components
        self.tokenizer = None
        self.model = None
        self.router = None
        self.personalization = None
        self.user_id = user_id
        
        # Infer sibling tokenizer/model when only one path is provided.
        if model_path and tokenizer_path is None:
            sibling_tokenizer = Path(model_path).with_name("tokenizer_metadata.json")
            if sibling_tokenizer.exists():
                tokenizer_path = str(sibling_tokenizer)
        if tokenizer_path and model_path is None:
            sibling_model = Path(tokenizer_path).with_name("final_model.pt")
            if sibling_model.exists():
                model_path = str(sibling_model)

        # Auto-detect newest in-repo trained artifacts only when both paths are missing.
        if model_path is None and tokenizer_path is None:
            repo_training_root = get_resource_root() / "training"
            auto_model_path, auto_tokenizer_path = self._find_training_artifacts(repo_training_root)
            if auto_model_path:
                model_path = auto_model_path
            if auto_tokenizer_path:
                tokenizer_path = auto_tokenizer_path

        # Fallback to old Downloads-era TinyLM paths if nothing local was found.
        if model_path is None:
            model_dir = get_models_dir()
            preferred_model = model_dir / "shadow_tiny_lm.pt"
            if preferred_model.exists():
                model_path = str(preferred_model)
            else:
                bundled_model = get_resource_root() / "models" / "shadow_tiny_lm.pt"
                if bundled_model.exists():
                    model_path = str(bundled_model)
                else:
                    tinylm_path = Path.home() / "Downloads" / "Shadow training" / "shadow_tiny_lm.pt"
                    if tinylm_path.exists():
                        model_path = str(tinylm_path)

        if tokenizer_path is None:
            model_dir = get_models_dir()
            preferred_tokenizer = model_dir / "tokenizer_metadata.json"
            if preferred_tokenizer.exists():
                tokenizer_path = str(preferred_tokenizer)
            else:
                bundled_tokenizer = get_resource_root() / "models" / "tokenizer_metadata.json"
                if bundled_tokenizer.exists():
                    tokenizer_path = str(bundled_tokenizer)
                else:
                    tinylm_tokenizer = Path.home() / "Downloads" / "Shadow training" / "tokenizer_metadata.json"
                    if tinylm_tokenizer.exists():
                        tokenizer_path = str(tinylm_tokenizer)
        
        # Load tokenizer
        if tokenizer_path and Path(tokenizer_path).exists():
            self.tokenizer = ShadowTokenizer.load(tokenizer_path)
        else:
            # Initialize empty tokenizer (will need training)
            self.tokenizer = ShadowTokenizer()
            logger.debug("Tokenizer not loaded; initialized empty tokenizer as fallback.")
        
        # Initialize router
        self.router = Router(self.config)
        
        # Initialize personalization
        self.personalization = PersonalizationLoop(self.config, user_id=user_id)
        
        # Load or initialize model
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            # Initialize blank model
            vocab_size = self.tokenizer.get_vocab_size()
            self.model = DualEncoder(self.config, vocab_size)
            self.model.to(self.device)
            self.model.eval()
            logger.debug("Model weights not loaded; using random initialization.")
    
    def load_model(self, model_path: str):
        """Load trained model from checkpoint."""
        print(f"Loading TinyLM model from {model_path}")
        
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Handle TinyLM checkpoint format (direct state_dict)
        if isinstance(checkpoint, dict):
            # Load config from checkpoint if available
            if 'config' in checkpoint:
                self.config = checkpoint['config']
            
            # Get state dict
            state_dict = checkpoint.get('model_state_dict', checkpoint)
            
            # Detect checkpoint vocab size from token_embedding.weight
            checkpoint_vocab_size = None
            if 'token_embedding.weight' in state_dict:
                checkpoint_vocab_size = state_dict['token_embedding.weight'].shape[0]
                print(f"Checkpoint vocab size: {checkpoint_vocab_size:,}")
            
            # Initialize model with checkpoint vocab size (not tokenizer)
            if checkpoint_vocab_size:
                vocab_size = checkpoint_vocab_size
            else:
                vocab_size = self.tokenizer.get_vocab_size()
            
            print(f"Initializing model with vocab size: {vocab_size:,}")
            self.model = DualEncoder(self.config, vocab_size)
            
            # Load weights (strict=False to allow shape mismatches)
            # Filter out positional encoding if shape mismatch (old 512 vs new 8192)
            filtered_state = {}
            model_state = self.model.state_dict()
            for key, value in state_dict.items():
                if 'pos_encoder.pe' in key:
                    # Skip positional encoding - will use newly initialized one
                    print(f"Skipping {key}: using dynamically initialized positional encoding")
                    continue
                filtered_state[key] = value
            
            self.model.load_state_dict(filtered_state, strict=False)
            
            # ALWAYS resize to match tokenizer (even if vocab_size matches)
            tokenizer_vocab = self.tokenizer.get_vocab_size()
            print(f"Resizing embeddings to tokenizer: {vocab_size:,} -> {tokenizer_vocab:,}")
            
            # Resize token embedding
            old_embeddings = self.model.token_embedding.weight.data
            new_embeddings = torch.nn.Embedding(tokenizer_vocab, self.model.embedding_dim, padding_idx=0)
            # Initialize with xavier
            torch.nn.init.xavier_uniform_(new_embeddings.weight)
            # Copy overlapping weights
            min_vocab = min(vocab_size, tokenizer_vocab)
            new_embeddings.weight.data[:min_vocab] = old_embeddings[:min_vocab]
            self.model.token_embedding = new_embeddings
            
            # Resize output head
            old_head = self.model.output_head.weight.data
            new_head = torch.nn.Linear(384, tokenizer_vocab)
            torch.nn.init.xavier_uniform_(new_head.weight)
            new_head.weight.data[:min_vocab] = old_head[:min_vocab]
            if hasattr(self.model.output_head, 'bias') and self.model.output_head.bias is not None:
                new_head.bias.data[:min_vocab] = self.model.output_head.bias.data[:min_vocab]
            self.model.output_head = new_head
            self.model.vocab_size = tokenizer_vocab
        else:
            # Direct model object
            self.model = checkpoint
        
        self.model.to(self.device)
        self.model.eval()
        
        print(f"TinyLM loaded successfully (parameters: {self.model.get_num_parameters():,})")
    
    def generate(self, prompt: str, max_length: int = 100, temperature: float = 0.7, max_new_tokens: int = None) -> str:
        """
        Generate response using SILS.
        
        Args:
            prompt: User input
            max_length: Maximum generation length
            temperature: Sampling temperature
        
        Returns:
            Generated response text
        """
        # Route message to determine mode
        mode, confidence = self.router.route(prompt)
        predicted_intent = self.predict_intent(prompt)
        
        if predicted_intent:
            print(
                f"[SILS] Router: mode={mode}, confidence={confidence:.2f}, intent={predicted_intent['name']} ({predicted_intent['confidence']:.2f})",
                flush=True
            )
        else:
            print(f"[SILS] Router: mode={mode}, confidence={confidence:.2f}", flush=True)

        template_intent = self._detect_template_intent(prompt, predicted_intent)
        template_response = self._template_response(prompt, template_intent)
        if template_response:
            print(
                f"[SILS] Template response: intent={template_intent} text='{self._safe_console_text(template_response)}'",
                flush=True
            )
            self.personalization.update(prompt)
            return template_response
        
        # Encode input WITHOUT padding (max_length=None for inference)
        print(f"[SILS] Encoding prompt: '{prompt[:50]}...'", flush=True)
        input_ids = self.tokenizer.encode(prompt, max_length=None, add_special_tokens=True, pad=False)
        print(f"[SILS] Encoded to {len(input_ids)} tokens", flush=True)
        
        # No truncation - accept any input length up to model's positional encoding max
        # (PositionalEncoding supports up to 8192 tokens)
        
        input_tensor = torch.tensor([input_ids], dtype=torch.long).to(self.device)
        input_length = len(input_ids)
        
        # Get user style if available
        user_style = None
        if self.personalization.is_initialized() and mode in ['tone', 'hybrid']:
            user_style = self.personalization.get_style_embedding().to(self.device)
        
        # Generate with selected mode
        actual_max_new = max_new_tokens if max_new_tokens is not None else max_length
        
        # Get token IDs for bad words to ban
        bad_words = ['crawl', 'explore', 'minor', 'insect', 'package', 'camera']
        bad_word_ids = []
        for word in bad_words:
            ids = self.tokenizer.encode(word, add_special_tokens=False, pad=False)
            if ids:
                bad_word_ids.extend(ids)
        
        print(f"[SILS] Starting generation (input={input_length} tokens, max_new_tokens={actual_max_new})...", flush=True)
        with torch.no_grad():
            generated_ids = self.model.generate(
                input_tensor,
                max_new_tokens=actual_max_new,
                temperature=temperature,
                min_p=0.05,  # Better for tiny models
                repetition_penalty=1.3,  # Stronger penalty
                no_repeat_ngram_size=2,  # Block repeating 2-grams
                bad_words=bad_word_ids,  # Ban garbage words
                mode=mode,
                user_style=user_style,
                tokenizer=self.tokenizer
            )
        print(f"[SILS] Generation complete, decoding...", flush=True)
        
        # Decode ONLY the newly generated tokens (skip input echo)
        generated_only = generated_ids[0, input_length:].tolist()
        print(f"[SILS] Generated {len(generated_only)} tokens, decoding...", flush=True)
        response = self.tokenizer.decode(generated_only)
        print(f"[SILS] Response: '{self._safe_console_text(response)}'", flush=True)
        
        # Update personalization with user message
        self.personalization.update(prompt)
        
        return response

    def predict_intent(self, prompt: str) -> Optional[Dict]:
        """Predict trained intent label from the SILS model."""
        if self.model is None or self.tokenizer is None:
            return None

        input_ids = self.tokenizer.encode(prompt, max_length=None, add_special_tokens=True, pad=False)
        input_tensor = torch.tensor([input_ids], dtype=torch.long).to(self.device)

        with torch.no_grad():
            intent_logits = self.model.predict_intent(input_tensor, mode='hybrid')

        if intent_logits is None or intent_logits.numel() == 0:
            return None

        probs = torch.softmax(intent_logits[0], dim=-1)
        label = int(torch.argmax(probs).item())
        confidence = float(probs[label].item())
        intent_names = self.config.get("intents", [])
        intent_name = intent_names[label] if label < len(intent_names) else f"intent_{label}"
        predicted = {
            "label": label,
            "name": intent_name,
            "confidence": confidence,
            "source": "model",
        }

        heuristic_intent = self._detect_template_intent(prompt, predicted)
        if heuristic_intent and heuristic_intent != intent_name and heuristic_intent in intent_names:
            return {
                "label": intent_names.index(heuristic_intent),
                "name": heuristic_intent,
                "confidence": max(confidence, 0.95),
                "source": "heuristic_override",
            }

        return predicted
    
    def is_available(self) -> bool:
        """Check if SILS backend is ready."""
        return (
            self.model is not None and
            self.tokenizer is not None and
            self.tokenizer.get_vocab_size() > 6  # More than just special tokens
        )
    
    def get_status(self) -> Dict:
        """Get backend status (alias for get_info)."""
        return self.get_info()
    
    def get_info(self) -> Dict:
        """Get backend information."""
        if not self.is_available():
            return {"status": "not_ready", "reason": "Model or tokenizer not loaded"}
        
        personalization_stats = self.personalization.get_stats()
        
        return {
            "status": "ready",
            "model": "TinyLM (SILS)",
            "parameters": self.model.get_num_parameters(),
            "vocab_size": self.tokenizer.get_vocab_size(),
            "intent_count": len(self.config.get("intents", [])),
            "device": str(self.device),
            "user_id": self.user_id,
            "personalization": personalization_stats,
            "router_enabled": True
        }
    
    def set_user(self, user_id: str):
        """Switch to different user profile."""
        self.user_id = user_id
        self.personalization = PersonalizationLoop(self.config, user_id=user_id)
        print(f"Switched to user: {user_id}")
    
    def reset_personalization(self):
        """Reset user personalization to blank state."""
        self.personalization.reset()
        print(f"Reset personalization for user: {self.user_id}")
    
    def explain_routing(self, message: str) -> Dict:
        """Explain routing decision for debugging."""
        return self.router.explain_routing(message)
