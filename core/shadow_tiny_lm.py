"""
Shadow Tiny LM - Lean Base Language Model
No user-specific data or personalization at deployment.
Learns only from each user after installation.
"""

import torch
import torch.nn as nn
import json
import os
from pathlib import Path
from .app_paths import get_models_dir
from .resource_paths import get_resource_root


class ShadowTokenizer:
    """Lightweight tokenizer for Shadow Tiny LM."""
    
    def __init__(self, token_to_id):
        self.token_to_id = token_to_id
        self.id_to_token = {v: k for k, v in token_to_id.items()}
        self.vocab_size = len(token_to_id)
        self.pad_id = token_to_id.get("<pad>", 0)
        self.unk_id = token_to_id.get("<unk>", 1)
        self.bos_id = token_to_id.get("<bos>", 2)
        self.eos_id = token_to_id.get("<eos>", 3)
    
    def encode(self, text, max_length=192):
        """Encode text to token IDs."""
        tokens = [self.bos_id]
        
        for char in text[:max_length-2]:  # Leave room for BOS/EOS
            token_id = self.token_to_id.get(char, self.unk_id)
            tokens.append(token_id)
        
        tokens.append(self.eos_id)
        
        # Pad to max_length
        while len(tokens) < max_length:
            tokens.append(self.pad_id)
        
        return tokens[:max_length]
    
    def decode(self, token_ids):
        """Decode token IDs to text."""
        text = ""
        for token_id in token_ids:
            if token_id == self.pad_id or token_id == self.eos_id:
                break
            if token_id == self.bos_id:
                continue
            text += self.id_to_token.get(token_id, "<unk>")
        return text


class ShadowTinyLM(nn.Module):
    """
    Shadow Tiny LM - Lean base model with no personalization.
    Designed to be a blank, lightweight foundation.
    """
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.vocab_size = len(config.get("tokenizer_base_tokens", [])) + 50  # Buffer for learned tokens
        self.d_model = config.get("d_model", 96)
        
        # Embedding layer
        self.embedding = nn.Embedding(self.vocab_size, self.d_model)
        
        # GRU backbone
        self.gru = nn.GRU(
            input_size=self.d_model,
            hidden_size=config.get("gru_hidden_size", 96),
            num_layers=config.get("gru_num_layers", 1),
            bidirectional=config.get("gru_bidirectional", False),
            dropout=config.get("dropout", 0.05) if config.get("gru_num_layers", 1) > 1 else 0,
            batch_first=True
        )
        
        # Output projection
        self.output_proj = nn.Linear(config.get("gru_hidden_size", 96), self.vocab_size)
        
        # Intent classifier (for command detection)
        if config.get("use_command_head", True):
            num_intents = len(config.get("intents", []))
            self.intent_head = nn.Linear(config.get("gru_hidden_size", 96), num_intents)
    
    def forward(self, input_ids):
        """Forward pass through the model."""
        # Embed tokens
        embedded = self.embedding(input_ids)
        
        # GRU processing
        gru_out, _ = self.gru(embedded)
        
        # Output logits
        logits = self.output_proj(gru_out)
        
        # Intent classification (if enabled)
        intent_logits = None
        if hasattr(self, 'intent_head'):
            # Use last hidden state for intent
            intent_logits = self.intent_head(gru_out[:, -1, :])
        
        return logits, intent_logits
    
    def generate(self, prompt, tokenizer, max_length=100, temperature=0.7):
        """Generate text from prompt."""
        self.eval()
        
        # Encode prompt
        input_ids = torch.tensor([tokenizer.encode(prompt)], dtype=torch.long)
        
        generated = input_ids[0].tolist()
        
        with torch.no_grad():
            for _ in range(max_length):
                # Forward pass
                logits, _ = self.forward(input_ids)
                
                # Get next token probabilities
                next_token_logits = logits[0, len(generated)-1, :] / temperature
                probs = torch.softmax(next_token_logits, dim=-1)
                
                # Sample next token
                next_token = torch.multinomial(probs, num_samples=1).item()
                
                # Stop if EOS
                if next_token == tokenizer.eos_id:
                    break
                
                generated.append(next_token)
                
                # Update input
                input_ids = torch.tensor([generated + [tokenizer.pad_id] * (192 - len(generated))], 
                                        dtype=torch.long)
        
        return tokenizer.decode(generated)


class ShadowTinyLMBackend:
    """
    Shadow Tiny LM Backend for Shadow AI.
    Lean base model with no user-specific data at deployment.
    """
    
    def __init__(self, model_path=None):
        self.model = None
        self.tokenizer = None
        self.config = None
        
        # Default paths
        if model_path is None:
            model_dir = get_models_dir()
            preferred_model = model_dir / "shadow_tiny_lm.pt"
            if preferred_model.exists():
                model_path = preferred_model
            else:
                bundled_model = get_resource_root() / "models" / "shadow_tiny_lm.pt"
                if bundled_model.exists():
                    model_path = bundled_model
                else:
                    # Legacy fallback for older dev layouts
                    shadow_training = Path.home() / "Downloads" / "Shadow training"
                    if shadow_training.exists():
                        model_path = shadow_training / "shadow_tiny_lm.pt"
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
    
    def load_model(self, model_path):
        """Load Shadow Tiny LM from checkpoint."""
        try:
            checkpoint = torch.load(model_path, map_location='cpu')
            
            # Load config
            self.config = checkpoint.get('config', {})
            
            # Load tokenizer
            token_to_id = checkpoint.get('token_to_id', {})
            self.tokenizer = ShadowTokenizer(token_to_id)
            
            # Initialize model
            self.model = ShadowTinyLM(self.config)
            
            # Load weights
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            
            self.model.eval()
            
            return True
        except Exception as e:
            print(f"Failed to load Shadow Tiny LM: {e}")
            return False
    
    def generate(self, prompt, max_length=100, temperature=0.7):
        """Generate response using Shadow Tiny LM."""
        if self.model is None or self.tokenizer is None:
            return "Shadow Tiny LM not loaded. Using fallback."
        
        try:
            response = self.model.generate(
                prompt, 
                self.tokenizer, 
                max_length=max_length,
                temperature=temperature
            )
            return response
        except Exception as e:
            return f"Generation error: {str(e)}"
    
    def is_available(self):
        """Check if Shadow Tiny LM is available."""
        return self.model is not None and self.tokenizer is not None
    
    def get_info(self):
        """Get model information."""
        if not self.is_available():
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "vocab_size": self.tokenizer.vocab_size,
            "d_model": self.config.get("d_model", 96),
            "parameters": sum(p.numel() for p in self.model.parameters()),
            "type": "Shadow Tiny LM - Lean Base (No Personalization)"
        }
