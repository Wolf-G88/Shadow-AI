# Shadow AI v2.0.35 - SILS v1 Release
## "Wolfy Recognition & Cognitive Engagement"

**Release Date:** January 10, 2026  
**Package:** `shadow-ai-2.0.35.deb` (448 KB)

---

## 🎯 Major Features

### SILS v1 (Shadow Intelligence Layer System)
- **Dual-Encoder Architecture**: Intent encoder (GRU) + Tone encoder (Transformer)
- **Intelligent Routing**: Automatic mode selection (intent/tone/hybrid)
- **Personalization Loop**: Per-user style adaptation with EMA embeddings
- **TinyLM**: 12.24M parameter model with 5,382 token vocabulary
- **Dynamic Limits**: No hardcoded vocab/sequence constraints - fully adaptive

### Wolfy-Style Recognition Engine
**3-Tier Cognitive Engagement System:**

1. **TIER 1: Knowledge Base** (Instant, 0ms)
   - Pattern matching with 70%+ confidence
   - Grounded responses from curated knowledge
   - Zero CPU overhead

2. **TIER 2: Search Mesh** (Fast, 0.5s)
   - Parallel racing: Wikipedia + DuckDuckGo
   - First-responder-wins architecture
   - Query optimization for better results
   - Transparent source attribution

3. **TIER 3: Honest Decline** (Responsible)
   - "I don't know" instead of hallucinations
   - Cognitive engagement messages
   - Encourages user verification

### Anti-Spoonfeeding Philosophy
- Distinguishes between administrative vs historical data
- Prompts users to verify complex/temporal queries
- Respects user intelligence - augments rather than replaces
- Anti-cheating by design (educators rejoice!)

---

## 🎨 Enhanced Color Palette

- **Theme Presets**: Dark, Light, Terminal, Accent categories
- **Hover Tooltips**: Shows color name + hex value
- **Recent Colors**: Remembers last 16 colors used
- **Named Colors**: "Matrix Green", "GitHub Dark", "Pure Black", etc.
- **Better UX**: 500x600 window, organized by purpose

---

## 🔧 Technical Improvements

### Architecture
- Removed all hardcoded limits (vocab size, sequence length)
- Dynamic positional encoding (extends on demand)
- Warm-start transfer from character-level to BPE tokenizer
- Max-new-tokens parameter (not total length)

### Generation Quality
- Repetition penalty: 1.3
- Min-P sampling: 0.05 (better for small models)
- No-repeat-ngram: blocks 2-gram repetition
- Bad words filtering: prevents "crawl explore" loops
- Top-P nucleus sampling: 0.9

### Performance
- Recognition responses: instant (0.00s)
- External search: sub-second (0.5s average)
- Generation: ~0.05s per token on CPU
- Memory efficient: 12M params fits in RAM

---

## 📦 Installation

```bash
# Install package
sudo dpkg -i shadow-ai-2.0.35.deb

# Install dependencies
sudo apt-get install -f

# Run Shadow AI
cd /opt/shadow-ai
./run.sh
```

---

## 🚀 Usage

### Recognition Examples
```
You: hello
Shadow: [TIER 1] Hello! I'm Shadow AI. What do you need?

You: what is your iq?
Shadow: [TIER 1] I'm a 12M parameter model running on Wolfy-style recognition. 
        My 'intelligence' is pattern matching, not general intelligence.

You: when was rome built?
Shadow: [TIER 2] Rome is the capital and largest city of Italy...
        
        Note: I found modern administrative data. For detailed historical 
        origins, consider cross-referencing with primary sources.
        
        (Source: DuckDuckGo)
```

### Model Selection
- **TinyLM (SILS)**: 12M params, instant recognition, honest about limits
- **Ollama Models**: Larger generative models (llama3, gemma2, etc.)
- **API Providers**: 15+ cloud options (Grok, OpenAI, Claude, etc.)

---

## 🔬 What's New in Detail

### 1. SILS v1 Implementation (~3,115 lines)
- `model/intent_encoder.py`: GRU-based intent extraction
- `model/tone_encoder.py`: Transformer-based style analysis
- `model/fusion.py`: Gated fusion mechanism
- `router/router.py`: Mode detection (intent/tone/hybrid)
- `personalization/loop.py`: EMA-based user adaptation
- `core/sils_backend.py`: Complete integration layer

### 2. Recognition Engine
- `core/recognition.py`: Pattern matching with confidence scores
- `data/knowledge_base.json`: Curated response database
- Categories: greetings, identity, capabilities, status, etc.
- Dynamic placeholders (time, date)

### 3. External Bridge
- `core/external_bridge.py`: Multi-source search mesh
- Parallel execution with ThreadPoolExecutor
- DNS-based internet check (fast, no browser)
- Query optimization (extracts main subject)
- Wikipedia API + DuckDuckGo instant answers

### 4. Cognitive Engagement
- Historical query detection
- Administrative vs historical distinction
- Encourages cross-referencing
- Multi-part question handling

---

## 📊 Model Specs

### TinyLM
- **Parameters**: 12,240,582
- **Vocabulary**: 5,382 tokens (WordPiece with BPE merges)
- **Architecture**: Dual-encoder (intent + tone)
- **Intent Encoder**: GRU, 2 layers, 256 hidden, bidirectional
- **Tone Encoder**: Transformer, 4 layers, 8 heads, 384 hidden
- **Embedding Dim**: 96
- **Max Sequence**: 16,384 tokens (dynamic)

### Training
- **Dataset**: 67,612 tone-tagged examples
- **Corpus**: 16,903 lines (~3k unique words)
- **Epochs**: 3
- **Warm Start**: Transfer from 43-token character model
- **Checkpoints**: Auto-saved every 500 steps

---

## 🛡️ Privacy & Security

- **100% Local**: No telemetry, no cloud connections by default
- **Offline-First**: Full functionality without internet
- **Transparent Fallback**: Clear indication when reaching external sources
- **No Data Collection**: Everything stays on your machine
- **Open Source**: Full code available for audit

---

## 🐛 Bug Fixes

- Fixed tensor shape bugs in generation pipeline
- Fixed vocab size mismatches between checkpoints
- Fixed positional encoding shape conflicts
- Removed input truncation (now accepts any length)
- Fixed stdout blocking in GUI thread
- Improved error handling in search mesh

---

## 🔮 Future Roadmap

- Additional search sources (Brave Search API)
- Voice input/output
- Multi-language support
- Plugin system for custom knowledge bases
- RAG (Retrieval Augmented Generation)
- Fine-tuning UI

---

## 📝 Credits

**Architecture**: WolfKing  
**Philosophy**: Wolfy AI bottom-up recognition principles  
**SILS v1**: Complete dual-encoder implementation  
**Package**: Shadow AI v2.0.35

---

## 🔗 Links

- **Documentation**: `/opt/shadow-ai/docs/`
- **SILS Spec**: `/opt/shadow-ai/docs/SILS_v1_COMPLETE.md`
- **Knowledge Base**: `/opt/shadow-ai/data/knowledge_base.json`
- **GitHub**: (Add your repo URL)

---

**Installation Size**: 448 KB  
**Installed Size**: ~7.5 MB  
**License**: (Your license)

Enjoy responsible AI with Shadow AI v2.0.35! 🐺🤖
