"""
Optimizer configuration for SILS v1
AdamW with warmup and cosine decay
"""

import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
import math


def create_optimizer(model, config):
    """
    Create AdamW optimizer with weight decay.
    
    Args:
        model: DualEncoder model
        config: training config dict
    
    Returns:
        optimizer: AdamW optimizer
    """
    lr = config['training']['lr']
    weight_decay = config['training']['weight_decay']
    
    # Separate parameters: no weight decay for biases and layer norms
    no_decay = ['bias', 'LayerNorm.weight', 'layer_norm.weight']
    
    optimizer_grouped_parameters = [
        {
            'params': [p for n, p in model.named_parameters() 
                      if not any(nd in n for nd in no_decay) and p.requires_grad],
            'weight_decay': weight_decay
        },
        {
            'params': [p for n, p in model.named_parameters() 
                      if any(nd in n for nd in no_decay) and p.requires_grad],
            'weight_decay': 0.0
        }
    ]
    
    optimizer = AdamW(
        optimizer_grouped_parameters,
        lr=lr,
        betas=(0.9, 0.999),
        eps=1e-8
    )
    
    return optimizer


def create_scheduler(optimizer, config, num_training_steps):
    """
    Create learning rate scheduler with warmup and cosine decay.
    
    Args:
        optimizer: optimizer instance
        config: training config dict
        num_training_steps: total training steps
    
    Returns:
        scheduler: LambdaLR scheduler
    """
    warmup_steps = config['training']['warmup_steps']
    
    def lr_lambda(current_step):
        """Compute learning rate multiplier."""
        if current_step < warmup_steps:
            # Linear warmup
            return float(current_step) / float(max(1, warmup_steps))
        
        # Cosine decay after warmup
        progress = float(current_step - warmup_steps) / float(max(1, num_training_steps - warmup_steps))
        return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))
    
    scheduler = LambdaLR(optimizer, lr_lambda)
    
    return scheduler


class GradientClipper:
    """
    Gradient clipping utility.
    """
    
    def __init__(self, max_norm=1.0):
        self.max_norm = max_norm
    
    def clip(self, model):
        """
        Clip gradients by global norm.
        
        Args:
            model: model with gradients
        
        Returns:
            total_norm: gradient norm before clipping
        """
        total_norm = torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            self.max_norm
        )
        
        return total_norm.item()


class OptimizerState:
    """
    Utility to save/load optimizer state.
    """
    
    @staticmethod
    def save(optimizer, scheduler, path):
        """Save optimizer and scheduler state."""
        state = {
            'optimizer': optimizer.state_dict(),
            'scheduler': scheduler.state_dict() if scheduler else None
        }
        torch.save(state, path)
    
    @staticmethod
    def load(optimizer, scheduler, path):
        """Load optimizer and scheduler state."""
        state = torch.load(path, map_location='cpu')
        optimizer.load_state_dict(state['optimizer'])
        if scheduler and state['scheduler']:
            scheduler.load_state_dict(state['scheduler'])


def get_optimizer_stats(optimizer):
    """
    Get optimizer statistics for logging.
    
    Args:
        optimizer: optimizer instance
    
    Returns:
        dict with stats
    """
    stats = {
        'lr': optimizer.param_groups[0]['lr'],
        'weight_decay': optimizer.param_groups[0]['weight_decay']
    }
    
    # Add gradient statistics if available
    total_norm = 0.0
    for group in optimizer.param_groups:
        for p in group['params']:
            if p.grad is not None:
                param_norm = p.grad.data.norm(2)
                total_norm += param_norm.item() ** 2
    
    total_norm = total_norm ** 0.5
    stats['grad_norm'] = total_norm
    
    return stats
