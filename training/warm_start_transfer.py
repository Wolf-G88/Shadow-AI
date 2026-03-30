"""
Warm Start Transfer for TinyLM
Transfers character-level weights from 43-token model to 5.4k subword model
Preserves learned character relationships while enabling word-level generation
"""

import torch
import torch.nn as nn
from pathlib import Path
import json


def warm_start_embeddings(old_checkpoint_path, new_vocab_path, embed_dim=None):
    """
    Transfer character weights from old model to new expanded vocab.
    
    Args:
        old_checkpoint_path: Path to 43-token TinyLM checkpoint
        new_vocab_path: Path to new 5.4k tokenizer metadata
        embed_dim: Embedding dimension (256 for TinyLM)
    
    Returns:
        new_embeddings: Expanded embedding matrix with transferred weights
        old_model_dict: Full old model state dict for other layers
    """
    
    print("=" * 60)
    print("WARM START TRANSFER")
    print("=" * 60)
    
    # Load old model (43 tokens)
    print(f"\n1. Loading old model from {old_checkpoint_path}")
    old_checkpoint = torch.load(old_checkpoint_path, map_location='cpu')
    
    # Extract old embedding weights
    old_state = old_checkpoint if isinstance(old_checkpoint, dict) else old_checkpoint.state_dict()
    old_embed_key = None
    for key in old_state.keys():
        if 'embedding' in key.lower() and 'weight' in key:
            old_embed_key = key
            break
    
    if old_embed_key is None:
        print("⚠️  Could not find embedding weights in old model")
        print("Available keys:", list(old_state.keys())[:10])
        return None, old_checkpoint
    
    old_embeddings = old_state[old_embed_key]
    old_vocab_size, old_embed_dim = old_embeddings.shape
    print(f"   Old vocab: {old_vocab_size} tokens, dim={old_embed_dim}")
    
    # Use old embedding dim to preserve model architecture
    if embed_dim is None:
        embed_dim = old_embed_dim
        print(f"   Using old embedding dimension: {embed_dim}")
    
    # Load new tokenizer vocab (5.4k tokens)
    print(f"\n2. Loading new tokenizer from {new_vocab_path}")
    with open(new_vocab_path, 'r') as f:
        tokenizer_meta = json.load(f)
    
    new_vocab = tokenizer_meta.get('vocab', tokenizer_meta.get('token_to_id', {}))
    new_vocab_size = len(new_vocab)
    print(f"   New vocab: {new_vocab_size} tokens")
    
    # Create new embedding matrix
    print(f"\n3. Initializing new embedding matrix ({new_vocab_size} x {embed_dim})")
    new_embeddings = nn.Embedding(new_vocab_size, embed_dim)
    nn.init.xavier_uniform_(new_embeddings.weight)
    
    # Build old vocab mapping (lowercase tokens from old model)
    old_token_map = {
        '<pad>': 0, '<unk>': 1, '<bos>': 2, '<eos>': 3,
        ' ': 4, '\n': 5, '.': 6, ',': 7, '-': 8, "'": 9, ':': 10, '"': 11,
        ')': 12, 'F': 13, 'I': 14, 'L': 15, 'M': 16, 'T': 17,
        'a': 18, 'b': 19, 'c': 20, 'd': 21, 'e': 22, 'f': 23,
        'g': 24, 'h': 25, 'i': 26, 'k': 27, 'l': 28, 'm': 29,
        'n': 30, 'o': 31, 'p': 32, 'q': 33, 'r': 34, 's': 35,
        't': 36, 'u': 37, 'v': 38, 'w': 39, 'x': 40, 'y': 41, '\u2019': 42
    }
    
    # Transfer character weights
    print("\n4. Transferring character weights...")
    matched_count = 0
    special_count = 0
    
    with torch.no_grad():
        for new_token, new_idx in new_vocab.items():
            # Direct character match
            if new_token in old_token_map:
                old_idx = old_token_map[new_token]
                if old_idx < old_vocab_size:
                    # Handle dimension mismatch - copy what we can, pad the rest
                    old_vec = old_embeddings[old_idx]
                    if old_vec.shape[0] != embed_dim:
                        # Pad or truncate to match new embedding dim
                        new_vec = torch.zeros(embed_dim)
                        copy_dim = min(old_vec.shape[0], embed_dim)
                        new_vec[:copy_dim] = old_vec[:copy_dim]
                        new_embeddings.weight[new_idx] = new_vec
                    else:
                        new_embeddings.weight[new_idx] = old_vec
                    
                    matched_count += 1
                    
                    if new_token in ['<pad>', '<unk>', '<bos>', '<eos>', '<STYLE>', '<INTENT>']:
                        special_count += 1
    
    print(f"   ✓ Transferred {matched_count} character weights")
    print(f"   ✓ Special tokens: {special_count}")
    print(f"   ✓ New subwords: {new_vocab_size - matched_count} (Xavier init)")
    
    # Calculate coverage
    coverage = (matched_count / new_vocab_size) * 100
    print(f"\n5. Transfer complete")
    print(f"   Coverage: {coverage:.1f}% of new vocab has pretrained weights")
    print(f"   Status: {'✓ Good' if coverage > 5 else '⚠️  Low coverage - mostly new tokens'}")
    
    return new_embeddings, old_checkpoint


def apply_warm_start(model, new_embeddings):
    """
    Apply transferred embeddings to model.
    
    Args:
        model: DualEncoder model instance
        new_embeddings: Transferred embedding layer
    """
    with torch.no_grad():
        # DualEncoder uses 'token_embedding' attribute
        model.token_embedding.weight.data = new_embeddings.weight.data
        model.token_embedding.num_embeddings = new_embeddings.num_embeddings
    print(f"\n✓ Warm start embeddings applied ({new_embeddings.num_embeddings} tokens, {new_embeddings.embedding_dim} dim)")


def save_warm_started_model(model, tokenizer_meta, output_path):
    """
    Save model with warm-started embeddings.
    
    Args:
        model: Model with transferred embeddings
        tokenizer_meta: Tokenizer metadata dict
        output_path: Where to save checkpoint
    """
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'config': model.config,
        'vocab_size': model.vocab_size,
        'tokenizer_meta': tokenizer_meta,
        'warm_started': True
    }
    
    torch.save(checkpoint, output_path)
    print(f"\n✓ Warm-started model saved to {output_path}")


if __name__ == "__main__":
    # Paths
    old_model_path = Path.home() / "Downloads" / "Shadow training" / "shadow_tiny_lm.pt"
    new_tokenizer_path = Path.home() / "Downloads" / "Shadow training" / "tokenizer_metadata.json"
    output_path = Path.home() / "Downloads" / "Shadow training" / "shadow_tiny_lm_warmstart.pt"
    
    print("\nWarm Start Transfer Script")
    print(f"Old model: {old_model_path}")
    print(f"New tokenizer: {new_tokenizer_path}")
    print(f"Output: {output_path}\n")
    
    # Perform transfer (use old model's embedding dim to preserve architecture)
    new_embeddings, old_checkpoint = warm_start_embeddings(
        str(old_model_path),
        str(new_tokenizer_path),
        embed_dim=None  # Auto-detect from old model
    )
    
    if new_embeddings is not None:
        # Load model and apply
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from model.dual_encoder import DualEncoder
        import json
        
        with open(new_tokenizer_path, 'r') as f:
            tokenizer_meta = json.load(f)
        
        vocab_size = len(tokenizer_meta.get('vocab', tokenizer_meta.get('token_to_id', {})))
        
        # Load SILS config
        config_path = Path(__file__).parent.parent / "config" / "sils_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Override embedding_dim to match old model dimension
        old_embed_dim = new_embeddings.weight.shape[1]
        config['embedding_dim'] = old_embed_dim
        print(f"\n✓ Using embedding_dim={old_embed_dim} (from old model)")
        
        model = DualEncoder(config, vocab_size)
        apply_warm_start(model, new_embeddings)
        save_warm_started_model(model, tokenizer_meta, str(output_path))
        
        print("\n" + "=" * 60)
        print("READY FOR TRAINING")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Prepare tone-tagged training data (<SHADOW>, <BRIGHT>, etc.)")
        print("2. Run training with frozen transformer (first 1000 steps)")
        print("3. Unfreeze and continue training")
        print(f"\nUse checkpoint: {output_path}")
