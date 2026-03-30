"""
Intent Encoder - GRU-based fast command understanding
SILS v1 - Shadow Intelligence Layer
"""

import torch
import torch.nn as nn


class IntentEncoder(nn.Module):
    """
    Fast GRU-based encoder for command/intent understanding.
    
    Architecture:
    - 2 layers
    - Hidden size: 256
    - Bidirectional: True
    - Output: Intent embedding (512-dim due to bidirectional)
    """
    
    def __init__(self, config):
        super().__init__()
        
        self.embedding_dim = config.get("embedding_dim", 256)
        self.hidden_size = config["intent_encoder"]["hidden_size"]
        self.num_layers = config["intent_encoder"]["layers"]
        self.bidirectional = config["intent_encoder"]["bidirectional"]
        
        # GRU layers
        self.gru = nn.GRU(
            input_size=self.embedding_dim,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            bidirectional=self.bidirectional,
            batch_first=True,
            dropout=0.1 if self.num_layers > 1 else 0
        )
        
        # Output projection
        output_dim = self.hidden_size * 2 if self.bidirectional else self.hidden_size
        self.output_proj = nn.Linear(output_dim, 384)  # Match fusion dim
        
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, embedded_input, attention_mask=None):
        """
        Forward pass.
        
        Args:
            embedded_input: (batch, seq_len, embedding_dim)
            attention_mask: (batch, seq_len) - optional
        
        Returns:
            intent_embedding: (batch, 384)
        """
        # GRU forward
        gru_output, hidden = self.gru(embedded_input)
        
        # Use last hidden state
        # hidden shape: (num_layers * num_directions, batch, hidden_size)
        if self.bidirectional:
            # Concatenate forward and backward final hidden states
            hidden_fwd = hidden[-2]  # Last layer forward
            hidden_bwd = hidden[-1]  # Last layer backward
            final_hidden = torch.cat([hidden_fwd, hidden_bwd], dim=-1)
        else:
            final_hidden = hidden[-1]
        
        # Project to fusion dimension
        intent_embedding = self.output_proj(final_hidden)
        intent_embedding = self.dropout(intent_embedding)
        
        return intent_embedding
    
    def get_intent_logits(self, intent_embedding, num_intents=6):
        """
        Project intent embedding to intent classification logits.
        
        Args:
            intent_embedding: (batch, 384)
            num_intents: Number of intent classes
        
        Returns:
            logits: (batch, num_intents)
        """
        if not hasattr(self, 'intent_classifier'):
            self.intent_classifier = nn.Linear(384, num_intents)
        
        return self.intent_classifier(intent_embedding)
