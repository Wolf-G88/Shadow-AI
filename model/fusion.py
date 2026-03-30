"""
Gated Fusion Layer - Blends intent and tone embeddings
SILS v1 - Shadow Intelligence Layer
"""

import torch
import torch.nn as nn


class GatedFusion(nn.Module):
    """
    Gated fusion layer that combines intent and tone embeddings.
    
    Formula:
        g = sigmoid(W * [intent; tone] + b)
        output = g * intent + (1 - g) * tone
    
    Where g is a learnable gate that decides the blend ratio.
    """
    
    def __init__(self, config):
        super().__init__()
        
        self.gate_dim = config["fusion"]["gate_dim"]  # 384
        
        # Gate network
        # Input: concatenated intent + tone (384 * 2 = 768)
        # Output: gate values (384)
        self.gate_network = nn.Sequential(
            nn.Linear(self.gate_dim * 2, self.gate_dim),
            nn.LayerNorm(self.gate_dim),
            nn.GELU(),
            nn.Linear(self.gate_dim, self.gate_dim),
            nn.Sigmoid()
        )
        
        self.layer_norm = nn.LayerNorm(self.gate_dim)
    
    def forward(self, intent_embedding, tone_embedding):
        """
        Fuse intent and tone embeddings.
        
        Args:
            intent_embedding: (batch, 384)
            tone_embedding: (batch, 384)
        
        Returns:
            fused_embedding: (batch, 384)
            gate_values: (batch, 384) - for interpretability
        """
        # Concatenate embeddings
        concatenated = torch.cat([intent_embedding, tone_embedding], dim=-1)
        
        # Compute gate
        gate = self.gate_network(concatenated)
        
        # Gated fusion
        fused = gate * intent_embedding + (1 - gate) * tone_embedding
        
        # Normalize
        fused = self.layer_norm(fused)
        
        return fused, gate
    
    def get_gate_stats(self, gate_values):
        """
        Get statistics about gate behavior for debugging.
        
        Args:
            gate_values: (batch, 384)
        
        Returns:
            dict with mean, std, intent_bias, tone_bias
        """
        mean_gate = gate_values.mean().item()
        std_gate = gate_values.std().item()
        
        # Intent bias: how much the gate prefers intent encoder
        intent_bias = (gate_values > 0.5).float().mean().item()
        
        # Tone bias: how much the gate prefers tone encoder
        tone_bias = (gate_values <= 0.5).float().mean().item()
        
        return {
            "mean_gate": mean_gate,
            "std_gate": std_gate,
            "intent_bias": intent_bias,
            "tone_bias": tone_bias
        }
