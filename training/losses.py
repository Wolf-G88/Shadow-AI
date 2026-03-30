"""
Loss Functions for SILS v1 Training
- Cross-entropy loss
- Style-alignment loss
- Intent-classification loss
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SILSLoss(nn.Module):
    """
    Combined loss function for SILS training.
    
    Components:
    1. Cross-entropy loss (language modeling)
    2. Style-alignment loss (tone encoder alignment with user style)
    3. Intent-classification loss (intent encoder accuracy)
    """
    
    def __init__(self, config):
        super().__init__()
        
        self.config = config
        self.num_intents = len(config.get('intents', [])) or config.get('intent_count', 6)
        
        # Loss weights
        self.ce_weight = 1.0
        self.style_weight = 0.3
        self.intent_weight = 0.5
        
        # Loss functions
        self.ce_loss = nn.CrossEntropyLoss(ignore_index=0)  # Ignore padding
        self.intent_loss = nn.CrossEntropyLoss()
        self.style_loss = StyleAlignmentLoss()
    
    def forward(self, model_output, targets, intent_labels=None, user_style=None, tone_embedding=None):
        """
        Compute combined loss.
        
        Args:
            model_output: dict from DualEncoder.forward() containing logits
            targets: (batch, seq_len) target token IDs
            intent_labels: (batch,) intent class labels (0-5)
            user_style: (batch, 64) user style embeddings
            tone_embedding: (batch, 384) tone encoder output
        
        Returns:
            total_loss: scalar tensor
            loss_dict: dict with individual loss components
        """
        losses = {}
        
        # 1. Cross-entropy loss (language modeling)
        logits = model_output['logits']  # (batch, vocab_size)
        
        # For autoregressive, we'd compare shifted sequences
        # For simplicity, we'll compute loss on last token prediction
        ce_loss = self.ce_loss(logits, targets)
        losses['ce_loss'] = ce_loss
        
        # 2. Intent classification loss (if intent mode or hybrid)
        if intent_labels is not None and model_output.get('embedding') is not None:
            intent_logits = model_output.get('intent_logits')
            if intent_logits is not None:
                intent_loss = self.intent_loss(intent_logits, intent_labels)
                losses['intent_loss'] = intent_loss
            else:
                losses['intent_loss'] = torch.tensor(0.0, device=logits.device)
        else:
            losses['intent_loss'] = torch.tensor(0.0, device=logits.device)
        
        # 3. Style alignment loss (if tone mode or hybrid)
        if user_style is not None and tone_embedding is not None:
            style_loss = self.style_loss(tone_embedding, user_style)
            losses['style_loss'] = style_loss
        else:
            losses['style_loss'] = torch.tensor(0.0, device=logits.device)
        
        # Compute total loss
        total_loss = (
            self.ce_weight * losses['ce_loss'] +
            self.intent_weight * losses['intent_loss'] +
            self.style_weight * losses['style_loss']
        )
        
        losses['total_loss'] = total_loss
        
        return total_loss, losses


class StyleAlignmentLoss(nn.Module):
    """
    Style alignment loss to match tone encoder output with user style.
    
    Uses cosine similarity to ensure tone encoder learns to produce
    embeddings aligned with user's communication style.
    """
    
    def __init__(self):
        super().__init__()
    
    def forward(self, tone_embedding, user_style):
        """
        Compute style alignment loss.
        
        Args:
            tone_embedding: (batch, 384) from tone encoder
            user_style: (batch, 64) user style embedding
        
        Returns:
            loss: scalar tensor
        """
        # Project user style to tone dimension
        if not hasattr(self, 'style_proj'):
            self.style_proj = nn.Linear(64, 384).to(tone_embedding.device)
        
        projected_style = self.style_proj(user_style)
        
        # Cosine similarity loss (we want high similarity)
        # Loss = 1 - cosine_similarity (minimize distance)
        cos_sim = F.cosine_similarity(tone_embedding, projected_style, dim=-1)
        loss = (1.0 - cos_sim).mean()
        
        return loss


class ContrastiveLoss(nn.Module):
    """
    Contrastive loss for learning better embeddings.
    Pushes similar examples together, dissimilar examples apart.
    """
    
    def __init__(self, temperature=0.07):
        super().__init__()
        self.temperature = temperature
    
    def forward(self, embeddings, labels):
        """
        Compute contrastive loss.
        
        Args:
            embeddings: (batch, dim) embeddings
            labels: (batch,) class labels
        
        Returns:
            loss: scalar tensor
        """
        # Normalize embeddings
        embeddings = F.normalize(embeddings, p=2, dim=1)
        
        # Compute similarity matrix
        sim_matrix = torch.matmul(embeddings, embeddings.T) / self.temperature
        
        # Create positive/negative masks
        labels = labels.unsqueeze(1)
        pos_mask = (labels == labels.T).float()
        neg_mask = (labels != labels.T).float()
        
        # Remove diagonal (self-similarity)
        pos_mask.fill_diagonal_(0)
        
        # Compute loss
        # Positive pairs should have high similarity
        # Negative pairs should have low similarity
        exp_sim = torch.exp(sim_matrix)
        
        # For each anchor, sum over all positives and negatives
        pos_sim = (exp_sim * pos_mask).sum(dim=1)
        neg_sim = (exp_sim * neg_mask).sum(dim=1)
        
        # Contrastive loss
        loss = -torch.log(pos_sim / (pos_sim + neg_sim + 1e-8)).mean()
        
        return loss


class GateLoss(nn.Module):
    """
    Regularization loss for gated fusion.
    Encourages gate to make clear decisions (close to 0 or 1).
    """
    
    def __init__(self):
        super().__init__()
    
    def forward(self, gate_values):
        """
        Compute gate regularization loss.
        
        Args:
            gate_values: (batch, 384) gate values from fusion
        
        Returns:
            loss: scalar tensor
        """
        # Encourage gate values to be close to 0 or 1 (decisive)
        # Loss = mean((gate - 0.5)^2 - 0.25)
        # This pushes values away from 0.5 (indecisive)
        deviation = torch.abs(gate_values - 0.5)
        loss = -deviation.mean()  # Negative because we want high deviation
        
        return loss


def compute_perplexity(logits, targets, ignore_index=0):
    """
    Compute perplexity from logits and targets.
    
    Args:
        logits: (batch, vocab_size) or (batch, seq_len, vocab_size)
        targets: (batch,) or (batch, seq_len)
        ignore_index: padding index to ignore
    
    Returns:
        perplexity: scalar tensor
    """
    ce_loss = F.cross_entropy(
        logits.view(-1, logits.size(-1)),
        targets.view(-1),
        ignore_index=ignore_index,
        reduction='mean'
    )
    
    perplexity = torch.exp(ce_loss)
    
    return perplexity
