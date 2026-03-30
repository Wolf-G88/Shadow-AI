"""
Tone Encoder - Transformer-based tone/style/emotion understanding
SILS v1 - Shadow Intelligence Layer
"""

import warnings
import torch
import torch.nn as nn
import math


warnings.filterwarnings(
    "ignore",
    message="The PyTorch API of nested tensors is in prototype stage.*",
    category=UserWarning,
)


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding - dynamically adapts to input length."""
    
    def __init__(self, d_model, max_len=None):
        super().__init__()
        self.d_model = d_model
        # If no max_len specified, use 16384 as safe default (supports very long sequences)
        self.max_len = max_len if max_len is not None else 16384
        
        # Pre-compute positional encodings up to max_len
        pe = torch.zeros(self.max_len, d_model)
        position = torch.arange(0, self.max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        """Add positional encoding to input - dynamically extends if needed."""
        seq_len = x.size(1)
        
        # Dynamically extend positional encoding if input exceeds current max
        if seq_len > self.max_len:
            print(f"Extending positional encoding: {self.max_len} -> {seq_len}")
            self._extend_pe(seq_len)
        
        return x + self.pe[:, :seq_len, :]
    
    def _extend_pe(self, new_max_len):
        """Dynamically extend positional encoding buffer."""
        pe = torch.zeros(new_max_len, self.d_model)
        position = torch.arange(0, new_max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, self.d_model, 2).float() * (-math.log(10000.0) / self.d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        pe = pe.unsqueeze(0).to(self.pe.device)
        self.register_buffer('pe', pe)
        self.max_len = new_max_len


class ToneEncoder(nn.Module):
    """
    Transformer-based encoder for tone, warmth, style, and emotional cues.
    
    Architecture:
    - 4 layers
    - 8 attention heads
    - Hidden size: 384
    - Feedforward size: 1536
    - Output: Tone embedding (384-dim)
    """
    
    def __init__(self, config):
        super().__init__()
        
        self.embedding_dim = config.get("embedding_dim", 256)
        self.hidden_size = config["tone_encoder"]["hidden_size"]
        self.num_layers = config["tone_encoder"]["layers"]
        self.num_heads = config["tone_encoder"]["heads"]
        self.ff_size = config["tone_encoder"]["ff_size"]
        
        # Input projection (embedding_dim -> hidden_size)
        self.input_proj = nn.Linear(self.embedding_dim, self.hidden_size)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(self.hidden_size)
        
        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.hidden_size,
            nhead=self.num_heads,
            dim_feedforward=self.ff_size,
            dropout=0.1,
            activation='gelu',
            batch_first=True
        )
        
        try:
            self.transformer = nn.TransformerEncoder(
                encoder_layer,
                num_layers=self.num_layers,
                enable_nested_tensor=False
            )
        except TypeError:
            self.transformer = nn.TransformerEncoder(
                encoder_layer,
                num_layers=self.num_layers
            )
        
        # Output projection (hidden_size -> 384 for fusion)
        self.output_proj = nn.Linear(self.hidden_size, 384)
        
        self.dropout = nn.Dropout(0.1)
        self.layer_norm = nn.LayerNorm(384)
    
    def forward(self, embedded_input, attention_mask=None):
        """
        Forward pass.
        
        Args:
            embedded_input: (batch, seq_len, embedding_dim)
            attention_mask: (batch, seq_len) - optional, 1 for valid tokens, 0 for padding
        
        Returns:
            tone_embedding: (batch, 384)
        """
        # Project to hidden size
        x = self.input_proj(embedded_input)
        x = self.dropout(x)
        
        # Add positional encoding
        x = self.pos_encoder(x)
        
        # Create attention mask for transformer
        # PyTorch transformer expects: False for valid, True for masked
        if attention_mask is not None:
            src_key_padding_mask = (attention_mask == 0)
        else:
            src_key_padding_mask = None
        
        # Transformer encoding
        x = self.transformer(x, src_key_padding_mask=src_key_padding_mask)
        
        # Pool: use mean of all token representations
        if attention_mask is not None:
            # Masked mean pooling
            mask_expanded = attention_mask.unsqueeze(-1).expand(x.size())
            sum_embeddings = torch.sum(x * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            pooled = sum_embeddings / sum_mask
        else:
            # Simple mean pooling
            pooled = x.mean(dim=1)
        
        # Project to fusion dimension
        tone_embedding = self.output_proj(pooled)
        tone_embedding = self.layer_norm(tone_embedding)
        
        return tone_embedding
    
    def extract_style_features(self, tone_embedding):
        """
        Extract 64-dim style embedding for personalization.
        
        Args:
            tone_embedding: (batch, 384)
        
        Returns:
            style_embedding: (batch, 64)
        """
        if not hasattr(self, 'style_proj'):
            self.style_proj = nn.Linear(384, 64)
        
        return self.style_proj(tone_embedding)
