#!/usr/bin/env python3
"""
Shadow AI v2.0.3 - Final Shipping Training Script
Trains SILS with tone awareness on your custom corpus
Set it and forget it - handles everything automatically
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from tqdm import tqdm
import json
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from model.dual_encoder import DualEncoder
from training.tokenizer import ShadowTokenizer


# === CONFIGURATION ===
CHECKPOINT_PATH = Path.home() / "Downloads" / "Shadow training" / "shadow_tiny_lm.pt"
TOKENIZER_PATH = Path.home() / "Downloads" / "Shadow training" / "tokenizer_metadata.json"
DATA_PATH = Path.home() / "vocab"
OUTPUT_DIR = Path.home() / "Downloads" / "Shadow training" / "checkpoints"
FINAL_OUTPUT = Path.home() / "Downloads" / "Shadow training" / "shadow_v2_final.pt"

# Training params
EPOCHS = 3
BATCH_SIZE = 8
LR_EMBEDDINGS = 1e-3  # Fast learning for new vocab
LR_TRANSFORMER = 1e-5  # Slow learning to preserve existing knowledge
GRADIENT_CLIP = 1.0
SAVE_EVERY = 500  # Save checkpoint every N steps

# Tone tags
TONES = ["<SHADOW>", "<BRIGHT>", "<COLD>", "<NEUTRAL>"]


class ToneDataset(Dataset):
    """Dataset that loads tone-tagged training data."""
    
    def __init__(self, corpus_path, tokenizer, max_length=128):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.examples = []
        
        print(f"Loading corpus from {corpus_path}")
        
        # Read corpus file
        with open(corpus_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        # Filter out section headers
        texts = [line for line in lines if not line.startswith('Section')]
        
        print(f"Loaded {len(texts)} lines")
        print("Creating tone-tagged examples...")
        
        # Create tone-tagged examples (4 versions of each sentence)
        for text in texts:
            for tone in TONES:
                tagged = f"{tone} {text}"
                self.examples.append(tagged)
        
        print(f"Created {len(self.examples)} training examples")
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        text = self.examples[idx]
        
        # Encode
        input_ids = self.tokenizer.encode(text, max_length=self.max_length, pad=True)
        
        # For autoregressive training, labels = input_ids shifted by 1
        labels = input_ids[1:] + [self.tokenizer.pad_id]
        
        return {
            'input_ids': torch.tensor(input_ids, dtype=torch.long),
            'labels': torch.tensor(labels, dtype=torch.long)
        }


def load_model_and_tokenizer():
    """Load warm-started model and tokenizer."""
    
    print("\n" + "="*60)
    print("LOADING MODEL & TOKENIZER")
    print("="*60)
    
    # Load tokenizer
    print(f"\n1. Loading tokenizer from {TOKENIZER_PATH}")
    tokenizer = ShadowTokenizer.load(str(TOKENIZER_PATH))
    vocab_size = tokenizer.get_vocab_size()
    print(f"   Vocab size: {vocab_size:,}")
    
    # Load model checkpoint
    print(f"\n2. Loading model from {CHECKPOINT_PATH}")
    checkpoint = torch.load(CHECKPOINT_PATH, map_location='cpu')
    
    # Get config
    if isinstance(checkpoint, dict) and 'config' in checkpoint:
        config = checkpoint['config']
    else:
        # Load default config
        config_path = Path(__file__).parent / "config" / "sils_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    # Initialize model
    model = DualEncoder(config, vocab_size)
    
    # Load weights
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'], strict=False)
    else:
        model.load_state_dict(checkpoint, strict=False)
    
    params = model.get_num_parameters()
    print(f"   Model loaded: {params:,} parameters")
    print(f"   Embedding dim: {model.embedding_dim}")
    
    return model, tokenizer


def create_optimizer(model):
    """Create tiered optimizer - fast for embeddings, slow for transformer."""
    
    print("\n3. Setting up optimizer")
    print("   Embedding LR: 1e-3 (learning new vocabulary)")
    print("   Transformer LR: 1e-5 (preserving existing knowledge)")
    
    optimizer = torch.optim.AdamW([
        {'params': model.token_embedding.parameters(), 'lr': LR_EMBEDDINGS},
        {'params': model.intent_encoder.parameters(), 'lr': LR_TRANSFORMER},
        {'params': model.tone_encoder.parameters(), 'lr': LR_TRANSFORMER},
        {'params': model.fusion.parameters(), 'lr': LR_TRANSFORMER},
        {'params': model.output_head.parameters(), 'lr': LR_EMBEDDINGS}
    ], weight_decay=0.01)
    
    return optimizer


def train_one_epoch(model, train_loader, optimizer, epoch, device):
    """Train for one epoch with progress bar."""
    
    model.train()
    total_loss = 0
    step = 0
    
    loop = tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}")
    
    for batch in loop:
        input_ids = batch['input_ids'].to(device)
        labels = batch['labels'].to(device)
        
        # Forward pass - use intent mode for basic language modeling
        result = model(input_ids, mode='intent')
        logits = result['logits']
        
        # Calculate loss - flatten batch and seq dimensions
        # logits shape: [batch, vocab] or [batch, seq, vocab]
        # labels shape: [batch, seq]
        loss = nn.CrossEntropyLoss(ignore_index=0)(
            logits.view(-1, logits.size(-1)),
            labels.view(-1)
        )
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
        optimizer.step()
        
        # Update metrics
        total_loss += loss.item()
        step += 1
        loop.set_postfix(loss=loss.item(), avg_loss=total_loss/step)
        
        # Auto-save checkpoint
        if step % SAVE_EVERY == 0:
            checkpoint_path = OUTPUT_DIR / f"checkpoint_epoch{epoch+1}_step{step}.pt"
            save_checkpoint(model, checkpoint_path)
    
    return total_loss / len(train_loader)


def save_checkpoint(model, path):
    """Save model checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'config': model.config,
        'vocab_size': model.vocab_size
    }, path)


def validate_model(model, tokenizer, device):
    """Run final validation tests."""
    
    print("\n" + "="*60)
    print("FINAL VALIDATION")
    print("="*60)
    
    model.eval()
    model.to(device)
    
    test_cases = [
        ("<SHADOW>", "system status"),
        ("<BRIGHT>", "hello world"),
        ("<COLD>", "execute command"),
        ("<NEUTRAL>", "the sun rises")
    ]
    
    print("\nTesting tone-aware generation:\n")
    
    with torch.no_grad():
        for tone, prompt in test_cases:
            full_prompt = f"{tone} {prompt}"
            
            # Encode
            input_ids = tokenizer.encode(full_prompt, max_length=None, pad=False)
            input_tensor = torch.tensor([input_ids], dtype=torch.long).to(device)
            
            # Generate
            mode = 'hybrid' if tone == '<SHADOW>' else 'intent'
            generated = model.generate(
                input_tensor,
                max_length=15,
                temperature=0.7,
                mode=mode,
                tokenizer=tokenizer
            )
            
            # Decode (skip input echo)
            response = tokenizer.decode(generated[0, len(input_ids):].tolist())
            
            print(f"{tone:12} [{prompt}]")
            print(f"             -> {response}\n")
    
    print("✓ Validation complete")


def main():
    """Main training pipeline."""
    
    print("\n" + "="*60)
    print("SHADOW AI v2.0.3 - FINAL TRAINING RUN")
    print("="*60)
    
    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}")
    
    # Load model and tokenizer
    model, tokenizer = load_model_and_tokenizer()
    model.to(device)
    
    # Create dataset
    print("\n" + "="*60)
    print("PREPARING TRAINING DATA")
    print("="*60 + "\n")
    
    dataset = ToneDataset(DATA_PATH, tokenizer, max_length=128)
    train_loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=2
    )
    
    print(f"\nBatch size: {BATCH_SIZE}")
    print(f"Total batches per epoch: {len(train_loader)}")
    
    # Create optimizer
    optimizer = create_optimizer(model)
    
    # Training loop
    print("\n" + "="*60)
    print("TRAINING")
    print("="*60 + "\n")
    
    for epoch in range(EPOCHS):
        avg_loss = train_one_epoch(model, train_loader, optimizer, epoch, device)
        print(f"\nEpoch {epoch+1}/{EPOCHS} complete - Average loss: {avg_loss:.4f}")
        
        # Save epoch checkpoint
        epoch_checkpoint = OUTPUT_DIR / f"checkpoint_epoch{epoch+1}.pt"
        save_checkpoint(model, epoch_checkpoint)
        print(f"✓ Saved checkpoint: {epoch_checkpoint}")
    
    # Save final model
    print("\n" + "="*60)
    print("SAVING FINAL MODEL")
    print("="*60)
    
    save_checkpoint(model, FINAL_OUTPUT)
    print(f"\n✓ Final model saved: {FINAL_OUTPUT}")
    
    # Validate
    validate_model(model, tokenizer, device)
    
    print("\n" + "="*60)
    print("🚀 TRAINING COMPLETE - READY TO SHIP")
    print("="*60)
    print(f"\nFinal checkpoint: {FINAL_OUTPUT}")
    print("Replace shadow_tiny_lm.pt with shadow_v2_final.pt to use trained model")
    print("\nNext steps:")
    print("1. Test in Shadow AI GUI")
    print("2. Update version to 2.0.3-RELEASE")
    print("3. Clear logs/ directory")
    print("4. Ship it! 🎯")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        print("Latest checkpoint saved in checkpoints/ directory")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
