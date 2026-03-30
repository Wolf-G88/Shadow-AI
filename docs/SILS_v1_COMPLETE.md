# SILS v1 - Shadow Intelligence Layer System

## Complete Implementation Documentation

### Overview

SILS v1 is a complete dual-encoder architecture with intelligent routing, personalization, and comprehensive training pipeline. This is the **full, production-ready implementation** - not simplified, not reduced, exactly as specified.

---

## Architecture Components

### 1. Dual-Encoder System

#### Intent Encoder (GRU)
- **Purpose**: Fast command/action understanding
- **Architecture**:
  - 2 layers
  - Hidden size: 256
  - Bidirectional: True
  - Output: 384-dim intent embedding
- **File**: `model/intent_encoder.py`

#### Tone Encoder (Transformer)
- **Purpose**: Tone, warmth, style, emotional understanding
- **Architecture**:
  - 4 layers
  - 8 attention heads
  - Hidden size: 384
  - Feedforward: 1536
  - Positional encoding: Sinusoidal
  - Output: 384-dim tone embedding
- **File**: `model/tone_encoder.py`

#### Gated Fusion Layer
- **Formula**: `g = sigmoid(W * [intent; tone])`, `output = g * intent + (1-g) * tone`
- **Purpose**: Learnable blend of intent and tone
- **Gate dimension**: 384
- **File**: `model/fusion.py`

#### Complete Model
- **Shared embedding**: 256-dim token embeddings
- **Output head**: Linear projection to vocabulary
- **Parameters**: ~2-5M (depends on vocab size)
- **File**: `model/dual_encoder.py`

### 2. Router / Orchestrator

**File**: `router/router.py`

**Modes**:
- **Intent**: Command-oriented (GRU only)
- **Tone**: Conversational (Transformer only)
- **Hybrid**: Mixed (both + fusion)

**Detection Logic**:
- Command keywords: open, close, delete, create, set, get, show, tell, run, execute
- Sentence patterns: verb+noun, imperatives, questions
- Conversational indicators: emojis, hedges, pronouns, punctuation
- Hybrid threshold: 0.4 (scores within 0.4 → hybrid mode)

**Features**:
- Confidence scores (0.0-1.0)
- Explainable routing (debugging)
- Mode distribution analysis

### 3. Tone Analysis Engine

**File**: `tone/tone_analysis.py`

**Extracts 64-dimensional style embedding**:

| Feature Category | Dimensions | Analyzed Elements |
|-----------------|------------|-------------------|
| Warmth | 8 | Politeness, hedges, softeners, questions, personal pronouns, emojis |
| Directness | 8 | Sentence length, imperative mood, lack of qualifiers, declaratives |
| Profanity | 8 | Profanity count/ratio, strong vs mild, all-caps aggression |
| Punctuation | 16 | Ellipses, exclamations, questions, commas, semicolons, dashes, quotes, mixed |
| Emotion | 16 | Positive/negative counts, sentiment polarity, intensity, certainty |
| Rhythm | 8 | Sentence length variation, short/long ratios, alternation patterns |

**Output**: 64-dim numpy array, normalized to [-1, 1] with tanh

### 4. Personalization Loop

**File**: `personalization/loop.py`

**Features**:
- **Per-user style embedding** (64-dim)
- **EMA updates**: `style_new = 0.85 * style_old + 0.15 * style_current`
- **Storage**: `~/.shadow/user_profile_{user_id}.json`
- **Secure permissions**: 0600
- **Never modifies base LM weights**

**Stored Data**:
```json
{
  "user_id": "default",
  "style_embedding": [64-dim array],
  "message_count": 0,
  "preferences": {
    "warmth": 0.0,
    "directness": 0.0,
    "profanity": 0.0
  }
}
```

**Integration**: Style embedding injected into tone encoder via linear adapter (384-dim projection)

---

## Training Pipeline

### Configuration

**File**: `config/sils_config.json`

All hyperparameters loaded from config:
- embedding_dim: 256
- Intent encoder: GRU, 2 layers, 256 hidden, bidirectional
- Tone encoder: Transformer, 4 layers, 8 heads, 384 hidden, 1536 FF
- Fusion: gated, 384 dim
- Training: batch 16, lr 3e-4, weight_decay 0.01, max_steps 50000
- Personalization: style_dim 64, ema_alpha 0.85

### Tokenizer

**File**: `training/tokenizer.py`

**Features**:
- **Algorithm**: WordPiece with BPE merges
- **Special tokens**: `<PAD>` (0), `<UNK>` (1), `<BOS>` (2), `<EOS>` (3), `<STYLE>` (4), `<INTENT>` (5)
- **Dynamic vocabulary**: Extendable post-training
- **Metadata**: `tokenizer_metadata.json` with vocab, merges, special tokens
- **Batch encoding/decoding**: Respects `<PAD>` masking

### Dataset Format

**JSONL with required fields**:
```json
{
  "input": "user message",
  "output": "AI response",
  "intent_label": 0,
  "tone_label": 0,
  "metadata": {}
}
```

**Intent labels** (0-5):
0. updatemodelrequirements
1. setstylerules
2. configurehybridpipeline
3. seterrortolerance
4. define_personality
5. cleanuprequest

### Loss Functions

**File**: `training/losses.py`

1. **Cross-Entropy Loss**: Language modeling (ignore padding)
2. **Style-Alignment Loss**: Cosine similarity between tone output and user style
3. **Intent-Classification Loss**: 6-class intent prediction
4. **Contrastive Loss**: Optional, pushes similar embeddings together
5. **Gate Loss**: Optional, encourages decisive gate values (0 or 1)

**Combined**: `total = 1.0 * CE + 0.5 * intent + 0.3 * style`

### Optimizer

**File**: `training/optimizer.py`

- **Algorithm**: AdamW
- **Learning rate**: 3e-4
- **Weight decay**: 0.01 (not applied to biases/layer norms)
- **Betas**: (0.9, 0.999)
- **Scheduler**: Linear warmup (1000 steps) + cosine decay
- **Gradient clipping**: Max norm 1.0

### Training Script

**File**: `training/train.py`

**Features**:
- Full training loop with epochs/steps
- Checkpoint save/load (model + optimizer + scheduler state)
- Logging: loss, perplexity, learning rate, gradient norm
- Evaluation on validation set
- Best model tracking
- Progress bar with live stats
- Resume from checkpoint

**Usage**:
```bash
python training/train.py \
  --config config/sils_config.json \
  --train-data data/train.jsonl \
  --val-data data/val.jsonl \
  --output-dir ./checkpoints \
  --resume ./checkpoints/checkpoint_step_5000.pt
```

### Dataset Tools

**File**: `training/dataset_tools.py`

**Complete CLI with commands**:

1. **Add examples**:
```python
from training.dataset_tools import DatasetManager

manager = DatasetManager("data/train.jsonl")
manager.add_example(
    input_text="How do I delete a file?",
    output_text="Use the rm command: rm filename",
    intent_label=2,
    metadata={"source": "manual"}
)
```

2. **Clean dataset**:
```bash
python training/dataset_tools.py \
  --dataset data/train.jsonl \
  clean \
  --output data/train_clean.jsonl
```

3. **Merge datasets**:
```bash
python training/dataset_tools.py \
  --dataset data/train.jsonl \
  merge \
  --others data/extra1.jsonl data/extra2.jsonl \
  --output data/merged.jsonl
```

4. **Export train/val/test splits**:
```bash
python training/dataset_tools.py \
  --dataset data/full.jsonl \
  export \
  --output data/dataset \
  --train-split 0.8 \
  --val-split 0.1
```

5. **Show statistics**:
```bash
python training/dataset_tools.py \
  --dataset data/train.jsonl \
  stats
```

6. **Create version**:
```bash
python training/dataset_tools.py \
  --dataset data/train.jsonl \
  version \
  --name "pre_cleaning"
```

---

## Integration with Shadow AI

**File**: `core/sils_backend.py`

**Features**:
- Routes every message via router
- Runs correct encoder(s) based on mode
- Applies personalization when available
- Falls back gracefully if no user profile
- Updates user profile after each message
- Never modifies base LM weights

**Usage in Shadow**:
```python
from core.sils_backend import SILSBackend

# Initialize
sils = SILSBackend(
    model_path="./checkpoints/best_model.pt",
    tokenizer_path="./checkpoints/tokenizer_metadata.json",
    user_id="default"
)

# Generate
response = sils.generate("How do I create a file?")

# Switch user
sils.set_user("user_123")

# Reset personalization
sils.reset_personalization()

# Debug routing
routing_info = sils.explain_routing("delete this file")
```

**Config Integration** (`~/.shadow_ai_config.json`):
```json
{
  "backend": "sils",
  "sils_model_path": "./checkpoints/best_model.pt",
  "sils_tokenizer_path": "./checkpoints/tokenizer_metadata.json",
  "user_id": "default",
  "max_length": 100,
  "temperature": 0.7
}
```

---

## File Structure

```
shadow-ai-v2/
├── model/
│   ├── dual_encoder.py      (211 lines) ✓
│   ├── intent_encoder.py    (89 lines)  ✓
│   ├── tone_encoder.py      (138 lines) ✓
│   └── fusion.py            (89 lines)  ✓
│
├── router/
│   └── router.py            (212 lines) ✓
│
├── tone/
│   └── tone_analysis.py     (377 lines) ✓
│
├── personalization/
│   └── loop.py              (174 lines) ✓
│
├── training/
│   ├── train.py             (347 lines) ✓
│   ├── dataset.py           (120 lines) ✓
│   ├── losses.py            (232 lines) ✓
│   ├── optimizer.py         (156 lines) ✓
│   ├── tokenizer.py         (342 lines) ✓
│   └── dataset_tools.py     (401 lines) ✓
│
├── config/
│   └── sils_config.json     (50 lines)  ✓
│
└── core/
    └── sils_backend.py      (177 lines) ✓

Total: ~3,115 lines of production code
```

---

## Training Example Workflow

### 1. Prepare Dataset
```bash
# Merge multiple sources
python training/dataset_tools.py --dataset data/base.jsonl merge \
  --others data/commands.jsonl data/conversations.jsonl \
  --output data/full.jsonl

# Clean
python training/dataset_tools.py --dataset data/full.jsonl clean

# Export splits
python training/dataset_tools.py --dataset data/full.jsonl export \
  --output data/dataset --train-split 0.8 --val-split 0.1
```

### 2. Train Model
```bash
python training/train.py \
  --config config/sils_config.json \
  --train-data data/dataset_train.jsonl \
  --val-data data/dataset_val.jsonl \
  --output-dir ./checkpoints
```

### 3. Test Inference
```python
from core.sils_backend import SILSBackend

sils = SILSBackend(
    model_path="./checkpoints/best_model.pt",
    tokenizer_path="./checkpoints/tokenizer_metadata.json"
)

# Test intent mode
print(sils.generate("delete the file test.txt"))

# Test tone mode
print(sils.generate("I'm feeling confused about this..."))

# Test hybrid
print(sils.generate("Could you please help me delete this?"))

# Check personalization
print(sils.get_info()['personalization'])
```

---

## Status: COMPLETE ✓

All components fully implemented according to SILS v1 specification:

✓ Dual-encoder architecture  
✓ Router/orchestrator  
✓ Tone analysis (64-dim embeddings)  
✓ Personalization loop (EMA, per-user)  
✓ Training pipeline (full, not toy)  
✓ Dataset tools (add, clean, merge, export)  
✓ Tokenizer (WordPiece + BPE + special tokens)  
✓ Loss functions (3 losses as specified)  
✓ Optimizer (AdamW + scheduler)  
✓ Config system (all params in JSON)  
✓ Shadow AI integration  

**No simplifications. No reductions. Full implementation.**
