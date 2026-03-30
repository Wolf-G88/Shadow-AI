"""
Dual Encoder Architecture - Complete SILS v1 model
Shadow Intelligence Layer Specification
"""

import torch
import torch.nn as nn
from model.intent_encoder import IntentEncoder
from model.tone_encoder import ToneEncoder
from model.fusion import GatedFusion


class DualEncoder(nn.Module):
    """
    Complete dual-encoder architecture for Shadow AI.
    
    Components:
    - Shared embedding layer (256-dim)
    - Intent encoder (GRU, fast command understanding)
    - Tone encoder (Transformer, style/emotion understanding)
    - Gated fusion layer (blends embeddings)
    - Output head (vocabulary projection)
    """
    
    def __init__(self, config, vocab_size):
        super().__init__()
        
        self.config = config
        self.vocab_size = vocab_size
        self.embedding_dim = config.get("embedding_dim", 256)
        
        # Shared embedding layer
        self.token_embedding = nn.Embedding(vocab_size, self.embedding_dim, padding_idx=0)
        
        # Dual encoders
        self.intent_encoder = IntentEncoder(config)
        self.tone_encoder = ToneEncoder(config)
        
        # Fusion layer
        self.fusion = GatedFusion(config)
        
        # Output head
        self.output_head = nn.Linear(384, vocab_size)
        self.intent_count = len(config.get("intents", [])) or config.get("intent_count", 0)
        self.intent_head = nn.Linear(384, self.intent_count) if self.intent_count > 0 else None
        self.style_adapter = nn.Linear(64, 384)
        
        self.dropout = nn.Dropout(0.1)
    
    def embed_input(self, input_ids):
        """
        Convert token IDs to embeddings.
        
        Args:
            input_ids: (batch, seq_len)
        
        Returns:
            embedded: (batch, seq_len, embedding_dim)
            attention_mask: (batch, seq_len)
        """
        # Token embeddings
        embedded = self.token_embedding(input_ids)
        embedded = self.dropout(embedded)
        
        # Create attention mask (1 for valid tokens, 0 for padding)
        attention_mask = (input_ids != 0).long()
        
        return embedded, attention_mask
    
    def forward(self, input_ids, mode='hybrid', user_style=None):
        """
        Forward pass through dual encoder.
        
        Args:
            input_ids: (batch, seq_len)
            mode: 'intent', 'tone', or 'hybrid'
            user_style: (batch, 64) optional user style embedding
        
        Returns:
            dict with:
                - logits: (batch, vocab_size)
                - embedding: final embedding used
                - mode: mode used
                - gate_values: if hybrid mode
        """
        # Embed input
        embedded, attention_mask = self.embed_input(input_ids)
        
        result = {
            'mode': mode,
            'logits': None,
            'embedding': None,
            'gate_values': None,
            'intent_logits': None,
        }
        
        if mode == 'intent':
            # Intent-only mode
            intent_emb = self.intent_encoder(embedded, attention_mask)  # (batch, 384)
            result['embedding'] = intent_emb
            # For language modeling, expand to sequence and apply output head
            # Expand intent_emb to (batch, seq_len, 384)
            batch_size, seq_len = input_ids.shape
            intent_seq = intent_emb.unsqueeze(1).expand(batch_size, seq_len, -1)
            result['logits'] = self.output_head(intent_seq)  # (batch, seq_len, vocab)
            if self.intent_head is not None:
                result['intent_logits'] = self.intent_head(intent_emb)
        
        elif mode == 'tone':
            # Tone-only mode
            tone_emb = self.tone_encoder(embedded, attention_mask)
            
            # Apply user style if available
            if user_style is not None:
                tone_emb = self._apply_user_style(tone_emb, user_style)
            
            result['embedding'] = tone_emb
            result['logits'] = self.output_head(tone_emb)
            if self.intent_head is not None:
                result['intent_logits'] = self.intent_head(tone_emb)
        
        elif mode == 'hybrid':
            # Hybrid mode: use both encoders + fusion
            intent_emb = self.intent_encoder(embedded, attention_mask)
            tone_emb = self.tone_encoder(embedded, attention_mask)
            
            # Apply user style to tone embedding
            if user_style is not None:
                tone_emb = self._apply_user_style(tone_emb, user_style)
            
            # Fuse embeddings
            fused_emb, gate = self.fusion(intent_emb, tone_emb)
            
            result['embedding'] = fused_emb
            result['logits'] = self.output_head(fused_emb)
            result['gate_values'] = gate
            if self.intent_head is not None:
                result['intent_logits'] = self.intent_head(fused_emb)
        
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        return result
    
    def _apply_user_style(self, tone_embedding, user_style):
        """
        Apply user-specific style to tone embedding.
        
        Args:
            tone_embedding: (batch, 384)
            user_style: (batch, 64)
        
        Returns:
            styled_embedding: (batch, 384)
        """
        # Keep style tensors aligned with the encoder device, especially on CUDA.
        user_style = user_style.to(tone_embedding.device)
        style_signal = self.style_adapter(user_style)
        
        # Additive style injection (residual)
        styled = tone_embedding + style_signal * 0.2  # Scale factor for stability
        
        return styled
    
    def generate(self, input_ids, max_length=100, temperature=0.7, mode='hybrid', user_style=None, tokenizer=None, max_new_tokens=None, top_p=0.9, repetition_penalty=1.2, min_p=0.05, no_repeat_ngram_size=2, bad_words=None):
        """
        Autoregressive generation.
        
        Args:
            input_ids: (1, seq_len) starting tokens
            max_length: DEPRECATED - use max_new_tokens
            max_new_tokens: max NEW tokens to generate (not including input)
            temperature: sampling temperature
            top_p: nucleus sampling threshold
            min_p: minimum probability threshold (better for small models)
            repetition_penalty: penalty for repeating tokens
            no_repeat_ngram_size: block repeating n-grams
            bad_words: list of token IDs to ban
            mode: encoder mode
            user_style: user style embedding
            tokenizer: tokenizer instance for EOS detection
        
        Returns:
            generated_ids: (1, generated_len)
        """
        self.eval()
        
        generated = input_ids.clone()
        
        # Get EOS/PAD IDs from tokenizer if provided, else default
        eos_id = tokenizer.eos_id if tokenizer else 3
        pad_id = tokenizer.pad_id if tokenizer else 0
        
        # Use max_new_tokens if provided
        actual_iterations = max_new_tokens if max_new_tokens is not None else max_length
        
        # Build bad words set from token IDs
        bad_words_set = set(bad_words) if bad_words else set()
        
        # Track n-grams to prevent repetition
        def get_ngrams(token_list, n):
            ngrams = set()
            for i in range(len(token_list) - n + 1):
                ngrams.add(tuple(token_list[i:i+n]))
            return ngrams
        
        generated_ngrams = set()
        
        with torch.no_grad():
            for _ in range(actual_iterations):
                # Forward pass
                result = self.forward(generated, mode=mode, user_style=user_style)
                logits = result['logits']
                
                # Get next-token logits.
                # Hybrid/tone modes return (batch, vocab), while intent mode returns
                # (batch, seq_len, vocab). In intent mode we want the last position.
                next_token_logits = logits[0]
                if next_token_logits.dim() == 2:
                    next_token_logits = next_token_logits[-1]
                next_token_logits = next_token_logits.clone()
                
                # Ban bad words
                if bad_words_set:
                    for bad_id in bad_words_set:
                        if bad_id < len(next_token_logits):
                            next_token_logits[bad_id] = -float('inf')
                
                # Apply repetition penalty
                if repetition_penalty != 1.0:
                    for token_id in set(generated[0].tolist()):
                        if token_id < len(next_token_logits):
                            next_token_logits[token_id] /= repetition_penalty
                
                # Block n-gram repetition
                if no_repeat_ngram_size > 0 and generated.size(1) >= no_repeat_ngram_size:
                    gen_tokens = generated[0].tolist()
                    current_ngrams = get_ngrams(gen_tokens[-(no_repeat_ngram_size-1):], no_repeat_ngram_size - 1)
                    
                    # Check each possible next token
                    for next_token_id in range(len(next_token_logits)):
                        test_ngram = tuple(gen_tokens[-(no_repeat_ngram_size-1):] + [next_token_id])
                        if test_ngram in generated_ngrams:
                            next_token_logits[next_token_id] = -float('inf')
                
                # Apply temperature
                next_token_logits = next_token_logits / temperature
                probs = torch.softmax(next_token_logits, dim=-1)
                
                # Apply min_p filtering (better than top_p for small models)
                if min_p > 0.0:
                    min_p_threshold = min_p * probs.max()
                    probs[probs < min_p_threshold] = 0
                    prob_sum = probs.sum()
                    if torch.isfinite(prob_sum) and prob_sum > 0:
                        probs = probs / prob_sum  # Renormalize

                # Safety fallback: filtering can zero-out everything or create NaNs.
                if (not torch.isfinite(probs).all()) or probs.sum() <= 0:
                    probs = torch.softmax(next_token_logits, dim=-1)
                    if (not torch.isfinite(probs).all()) or probs.sum() <= 0:
                        next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
                        token_val = next_token.item()
                        if token_val == eos_id or token_val == pad_id:
                            break
                        if no_repeat_ngram_size > 0:
                            gen_tokens = generated[0].tolist()
                            if len(gen_tokens) >= no_repeat_ngram_size - 1:
                                new_ngram = tuple(gen_tokens[-(no_repeat_ngram_size-1):] + [token_val])
                                generated_ngrams.add(new_ngram)
                        generated = torch.cat([generated, next_token.unsqueeze(0)], dim=1)
                        continue
                
                # Sample
                next_token = torch.multinomial(probs, num_samples=1)
                
                # Stop if EOS or PAD
                token_val = next_token.item()
                if token_val == eos_id or token_val == pad_id:
                    break
                
                # Update n-gram tracking
                if no_repeat_ngram_size > 0:
                    gen_tokens = generated[0].tolist()
                    if len(gen_tokens) >= no_repeat_ngram_size - 1:
                        new_ngram = tuple(gen_tokens[-(no_repeat_ngram_size-1):] + [token_val])
                        generated_ngrams.add(new_ngram)
                
                # Append token
                generated = torch.cat([generated, next_token.unsqueeze(0)], dim=1)
        
        return generated

    def predict_intent(self, input_ids, mode='hybrid', user_style=None):
        """
        Predict intent label for an input batch.

        Returns:
            intent_logits: (batch, intent_count) or None
        """
        result = self.forward(input_ids, mode=mode, user_style=user_style)
        return result.get('intent_logits')
    
    def get_num_parameters(self):
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def save_checkpoint(self, path):
        """Save model checkpoint."""
        torch.save({
            'model_state_dict': self.state_dict(),
            'config': self.config,
            'vocab_size': self.vocab_size
        }, path)
    
    @classmethod
    def load_checkpoint(cls, path):
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location='cpu')
        model = cls(checkpoint['config'], checkpoint['vocab_size'])
        model.load_state_dict(checkpoint['model_state_dict'])
        return model
