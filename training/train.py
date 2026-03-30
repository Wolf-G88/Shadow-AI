"""
Complete Training Script for SILS v1
Full training loop with checkpointing, logging, and evaluation
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import json
from pathlib import Path
from tqdm import tqdm
import logging
from typing import Optional

from model.dual_encoder import DualEncoder
from training.dataset import create_dataloader
from training.losses import SILSLoss, compute_perplexity
from training.optimizer import create_optimizer, create_scheduler, GradientClipper, OptimizerState
from training.tokenizer import ShadowTokenizer, build_tokenizer_from_dataset


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SILSTrainer:
    """
    Complete trainer for SILS v1 dual-encoder model.
    
    Features:
    - Full training loop with epochs/steps
    - Checkpoint save/load with optimizer state
    - Logging (loss, perplexity, learning rate)
    - Evaluation on validation set
    - Gradient clipping
    - Learning rate scheduling
    """
    
    def __init__(self, config_path: str, output_dir: str):
        # Load config
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        # Training params
        self.batch_size = None
        self.max_steps = None
        self.save_every = None
        self.eval_every = None
        self.gradient_clip = None
        self.early_stopping_patience = None
        self.early_stopping_min_delta = None
        self._refresh_training_params()
        
        # Initialize components
        self.tokenizer = None
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.criterion = None
        self.gradient_clipper = GradientClipper(self.gradient_clip)
        
        # Training state
        self.global_step = 0
        self.epoch = 0
        self.best_val_loss = float('inf')
        self.best_val_step = 0
        self.no_improve_evals = 0
        
        logger.info("Trainer initialized")

    def _refresh_training_params(self):
        """Refresh cached training params after config overrides."""
        training_cfg = self.config.get('training', {})
        self.batch_size = training_cfg.get('batch_size', 16)
        self.max_steps = training_cfg.get('max_steps', 50000)
        self.save_every = training_cfg.get('save_every', 500)
        self.eval_every = training_cfg.get('eval_every', 100)
        self.gradient_clip = training_cfg.get('gradient_clip', 1.0)
        self.early_stopping_patience = training_cfg.get('early_stopping_patience')
        self.early_stopping_min_delta = float(training_cfg.get('early_stopping_min_delta', 0.0))
        self.gradient_clipper = GradientClipper(self.gradient_clip)
    
    def setup_tokenizer(self, dataset_path: str, tokenizer_path: Optional[str] = None):
        """Setup or load tokenizer."""
        if tokenizer_path and Path(tokenizer_path).exists():
            logger.info(f"Loading tokenizer from {tokenizer_path}")
            self.tokenizer = ShadowTokenizer.load(tokenizer_path)
        else:
            logger.info("Building tokenizer from dataset")
            tokenizer_cfg = self.config.get('tokenizer', {})
            vocab_size = tokenizer_cfg.get('vocab_size')
            min_frequency = tokenizer_cfg.get('min_frequency', 2)
            extra_text_paths = tokenizer_cfg.get('extra_text_paths', [])
            seed_tokens_path = tokenizer_cfg.get('seed_tokens_path')
            save_path = self.output_dir / "tokenizer_metadata.json"
            self.tokenizer = build_tokenizer_from_dataset(
                dataset_path,
                vocab_size=vocab_size,
                min_frequency=min_frequency,
                extra_text_paths=extra_text_paths,
                seed_tokens_path=seed_tokens_path,
                save_path=str(save_path)
            )
    
    def setup_model(self):
        """Initialize model."""
        logger.info("Initializing dual-encoder model")
        
        vocab_size = self.tokenizer.get_vocab_size()
        self.model = DualEncoder(self.config, vocab_size)
        self.model.to(self.device)
        
        # Count parameters
        num_params = self.model.get_num_parameters()
        logger.info(f"Model parameters: {num_params:,}")
        
        # Initialize loss
        self.criterion = SILSLoss(self.config)
        self.criterion.to(self.device)
    
    def setup_optimizer(self, num_training_steps: int):
        """Initialize optimizer and scheduler."""
        logger.info("Setting up optimizer")
        
        self.optimizer = create_optimizer(self.model, self.config)
        self.scheduler = create_scheduler(self.optimizer, self.config, num_training_steps)
        
        logger.info(f"Learning rate: {self.config['training']['lr']}")
        logger.info(f"Weight decay: {self.config['training']['weight_decay']}")

    def _apply_dataset_metadata(self, dataset):
        """Carry dataset-derived metadata into config for dynamic training heads."""
        intent_names = dataset.get_intent_names()
        if intent_names:
            self.config['intents'] = intent_names
            self.config['intent_count'] = len(intent_names)
            logger.info(f"Detected intents ({len(intent_names)}): {', '.join(intent_names)}")
    
    def train(self, train_dataset_path: str, val_dataset_path: Optional[str] = None,
              resume_from: Optional[str] = None):
        """
        Main training loop.
        
        Args:
            train_dataset_path: Path to training JSONL
            val_dataset_path: Path to validation JSONL (optional)
            resume_from: Checkpoint path to resume from (optional)
        """
        self._refresh_training_params()

        # Setup tokenizer
        self.setup_tokenizer(train_dataset_path)
        
        # Create dataloaders
        train_loader, train_dataset = create_dataloader(
            train_dataset_path,
            self.tokenizer,
            batch_size=self.batch_size,
            shuffle=True,
            return_dataset=True,
            cleanup_boost=self.config.get('training', {}).get('cleanup_boost', 0),
            max_cleanup_repeats=self.config.get('training', {}).get('max_cleanup_repeats', 4)
        )
        self._apply_dataset_metadata(train_dataset)
        cleanup_summary = train_dataset.get_cleanup_repeat_summary()
        if cleanup_summary["cleanup_boost"] > 0:
            logger.info(
                "Cleanup boost enabled | boosted_examples=%s | avg_repeat=%.2f | max_repeat=%s",
                cleanup_summary["boosted_examples"],
                cleanup_summary["avg_repeat"],
                cleanup_summary["max_repeat"]
            )
        
        val_loader = None
        if val_dataset_path:
            val_loader, _ = create_dataloader(
                val_dataset_path,
                self.tokenizer,
                batch_size=self.batch_size,
                shuffle=False,
                return_dataset=True,
                intent_to_label=train_dataset.intent_to_label
            )

        # Setup model after dataset metadata is known.
        self.setup_model()
        
        # Calculate total training steps
        num_training_steps = min(
            self.max_steps,
            len(train_loader) * (self.max_steps // len(train_loader) + 1)
        )
        
        # Setup optimizer
        self.setup_optimizer(num_training_steps)
        
        # Resume from checkpoint if provided
        if resume_from:
            self.load_checkpoint(resume_from)
        
        logger.info("=" * 80)
        logger.info("Starting training")
        logger.info(f"Total steps: {num_training_steps}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Save every: {self.save_every} steps")
        logger.info(f"Eval every: {self.eval_every} steps")
        if val_loader:
            logger.info(f"Early stopping patience: {self.early_stopping_patience}")
            logger.info(f"Early stopping min delta: {self.early_stopping_min_delta:.6f}")
        logger.info("=" * 80)
        
        # Training loop
        self.model.train()
        
        progress_bar = tqdm(total=num_training_steps, desc="Training")
        
        stop_early = False
        while self.global_step < num_training_steps and not stop_early:
            self.epoch += 1
            
            for batch in train_loader:
                if self.global_step >= num_training_steps:
                    break
                
                # Move batch to device
                input_ids = batch['input_ids'].to(self.device)
                output_ids = batch['output_ids'].to(self.device)
                intent_labels = batch['intent_labels'].to(self.device)
                
                # Forward pass
                model_output = self.model(input_ids, mode='hybrid')
                
                # Compute loss
                loss, loss_dict = self.criterion(
                    model_output,
                    output_ids[:, -1],  # Last token prediction
                    intent_labels=intent_labels
                )
                
                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                
                # Gradient clipping
                grad_norm = self.gradient_clipper.clip(self.model)
                
                # Optimizer step
                self.optimizer.step()
                self.scheduler.step()
                
                # Logging
                if self.global_step % 10 == 0:
                    lr = self.scheduler.get_last_lr()[0]
                    perplexity = compute_perplexity(model_output['logits'], output_ids[:, -1])
                    
                    progress_bar.set_postfix({
                        'loss': f"{loss.item():.4f}",
                        'ppl': f"{perplexity.item():.2f}",
                        'lr': f"{lr:.2e}",
                        'grad': f"{grad_norm:.2f}"
                    })
                    
                    logger.info(
                        f"Step {self.global_step} | "
                        f"Loss: {loss.item():.4f} | "
                        f"CE: {loss_dict['ce_loss'].item():.4f} | "
                        f"Intent: {loss_dict['intent_loss'].item():.4f} | "
                        f"Style: {loss_dict['style_loss'].item():.4f} | "
                        f"PPL: {perplexity.item():.2f} | "
                        f"LR: {lr:.2e}"
                    )
                
                # Evaluation
                if (
                    val_loader and
                    self.eval_every and
                    self.eval_every > 0 and
                    self.global_step > 0 and
                    self.global_step % self.eval_every == 0
                ):
                    val_loss = self.evaluate(val_loader)
                    logger.info(f"Validation loss: {val_loss:.4f}")
                    
                    # Save best model
                    if val_loss < (self.best_val_loss - self.early_stopping_min_delta):
                        self.best_val_loss = val_loss
                        self.best_val_step = self.global_step
                        self.no_improve_evals = 0
                        self.save_checkpoint("best_model.pt")
                        logger.info("Saved best model")
                    else:
                        self.no_improve_evals += 1
                        logger.info(
                            "No validation improvement | count=%s | best=%.4f @ step %s",
                            self.no_improve_evals,
                            self.best_val_loss,
                            self.best_val_step
                        )
                        if (
                            self.early_stopping_patience is not None and
                            self.no_improve_evals >= self.early_stopping_patience
                        ):
                            logger.info(
                                "Early stopping triggered after %s non-improving evals",
                                self.no_improve_evals
                            )
                            stop_early = True
                    
                    self.model.train()
                    if stop_early:
                        break
                
                # Save checkpoint
                if self.save_every and self.global_step > 0 and self.global_step % self.save_every == 0:
                    self.save_checkpoint(f"checkpoint_step_{self.global_step}.pt")
                    logger.info(f"Saved checkpoint at step {self.global_step}")
                
                self.global_step += 1
                progress_bar.update(1)
        
        progress_bar.close()
        
        # Save final model
        self.save_checkpoint("final_model.pt")
        logger.info("Training complete!")
    
    def evaluate(self, val_loader: DataLoader) -> float:
        """Evaluate on validation set."""
        self.model.eval()
        
        total_loss = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch['input_ids'].to(self.device)
                output_ids = batch['output_ids'].to(self.device)
                intent_labels = batch['intent_labels'].to(self.device)
                
                model_output = self.model(input_ids, mode='hybrid')
                
                loss, _ = self.criterion(
                    model_output,
                    output_ids[:, -1],
                    intent_labels=intent_labels
                )
                
                total_loss += loss.item()
                num_batches += 1
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        
        return avg_loss
    
    def save_checkpoint(self, filename: str):
        """Save model and training state."""
        checkpoint_path = self.output_dir / filename
        
        checkpoint = {
            'global_step': self.global_step,
            'epoch': self.epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'config': self.config,
            'intent_names': self.config.get('intents', []),
            'best_val_loss': self.best_val_loss,
            'best_val_step': self.best_val_step,
            'no_improve_evals': self.no_improve_evals
        }
        
        torch.save(checkpoint, checkpoint_path)
        logger.info(f"Checkpoint saved to {checkpoint_path}")
    
    def load_checkpoint(self, checkpoint_path: str):
        """Load model and training state."""
        logger.info(f"Loading checkpoint from {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        
        self.global_step = checkpoint['global_step']
        self.epoch = checkpoint['epoch']
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))
        self.best_val_step = checkpoint.get('best_val_step', 0)
        self.no_improve_evals = checkpoint.get('no_improve_evals', 0)
        
        logger.info(
            f"Resumed from step {self.global_step}, epoch {self.epoch}, "
            f"best val loss {self.best_val_loss:.4f} @ step {self.best_val_step}"
        )


def main():
    """Main training entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train SILS v1 model")
    parser.add_argument("--config", type=str, required=True, help="Path to config.json")
    parser.add_argument("--train-data", type=str, required=True, help="Path to training JSONL")
    parser.add_argument("--val-data", type=str, default=None, help="Path to validation JSONL")
    parser.add_argument("--output-dir", type=str, default="./checkpoints", help="Output directory")
    parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = SILSTrainer(args.config, args.output_dir)
    
    # Start training
    trainer.train(
        train_dataset_path=args.train_data,
        val_dataset_path=args.val_data,
        resume_from=args.resume
    )


if __name__ == "__main__":
    main()
