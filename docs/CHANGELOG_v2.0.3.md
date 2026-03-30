# Shadow AI v2.0.3 - Release Notes

**Release Date**: TBD

## 🎯 Overview
Shadow AI v2.0.3 introduces a custom-trained lean base LLM, automatic model version detection across all 15 API providers, and a professional color palette system. This release emphasizes **privacy-first AI** with a lightweight foundation model that learns per-user after deployment.

---

## 🆕 Major Features

### 1. **Shadow Tiny LM - Lean Base Language Model**
- **Privacy-First Design**: Ships as a blank, lightweight foundation with NO user-specific data or personalization
- **Per-User Learning**: Model learns only from each user after deployment
- **Architecture**: Hybrid GRU + Transformer (96-dimensional, 2 layers, 4 attention heads)
- **Lightweight**: ~1.1 MB model size (43 tokens, character-level tokenizer)
- **Intent Classification**: Built-in 6-intent classifier for command detection
- **Integration**: Seamlessly integrated as `shadow_tiny` backend option
- **Path**: Automatically loads from `~/Downloads/Shadow training/shadow_tiny_lm.pt`

**Technical Specifications**:
- d_model: 96
- GRU Hidden Size: 96
- Layers: 2 (GRU) + Transformer attention heads
- Max Context: 192 tokens
- Intents: updatemodelrequirements, setstylerules, configurehybridpipeline, seterrortolerance, define_personality, cleanuprequest

### 2. **Automatic Model Version Detection**
- **Zero Manual Input**: No manual version selection required
- **Multi-Source Detection**:
  - HTTP response headers (X-Model-Version, X-API-Version, etc.)
  - API response metadata (model field, version field)
  - Capability signatures (token limits, vision support, thinking mode)
- **Provider Coverage**: All 15 API providers (OpenAI, Gemini, Claude, Grok, Mistral, Cohere, Together AI, Perplexity, Groq, DeepSeek, HuggingFace, OpenRouter, Anyscale, Fireworks)
- **Caching**: Detected versions cached per provider
- **Fallback**: Intelligent fallback to endpoint URL version detection

**Capability Signatures**:
- OpenAI: Detects GPT-4-Turbo (128K context + vision), GPT-4 (8K), GPT-3.5-Turbo (16K)
- Gemini: Detects 1.5-Pro (2M context + thinking), 1.5-Flash (1M + thinking), Gemini-Pro (32K)
- Claude: Detects Claude-3-Opus (200K + extended thinking), Claude-3-Sonnet (200K), Claude-2 (100K)

### 3. **Color Palette Module**
- **Paint-Program Style**: Classic grid layout familiar to creative professionals
- **Primary Colors**: Top row with 8 essential colors (Red, Orange, Yellow, Green, Blue, Purple, Black, White)
- **Extended Grid**: 216-color web-safe palette in scrollable grid (18 colors per row)
- **Custom Picker**: System color chooser integration for unlimited colors
- **Live Preview**: Real-time color preview with hex code display
- **UI Integration**: 3 customizable colors (Chat Text, Chat Background, Terminal Text)
- **Persistence**: Color choices saved to config and applied immediately

---

## 🔧 Technical Improvements

### Backend Architecture
1. **Unified LLM Module**:
   - Added `shadow_tiny` backend alongside ollama, gguf, api
   - Lazy loading for Shadow Tiny LM (loads on first use)
   - Auto-detection layer for API responses
   - Tuple returns `(response, headers)` from API calls for version detection

2. **Model Version Detector**:
   - Standalone module: `core/model_version_detector.py`
   - Header pattern matching with regex extraction
   - Metadata inspection (model, version, model_name, engine fields)
   - Capability fingerprinting (max_tokens, vision, thinking_mode, extended_thinking)
   - Provider-specific signature databases

3. **Shadow Tiny LM Backend**:
   - Standalone module: `core/shadow_tiny_lm.py`
   - ShadowTokenizer: Character-level with special tokens (<pad>, <unk>, <bos>, <eos>)
   - ShadowTinyLM: PyTorch nn.Module with GRU + attention
   - ShadowTinyLMBackend: High-level API for generation
   - Temperature-controlled sampling with EOS detection

### UI/UX Enhancements
1. **Color Palette Widget**:
   - Standalone module: `output/color_palette.py`
   - Tkinter Toplevel window (420x500px, modal)
   - Canvas-based color preview (60x30px with hex label)
   - Button grid with hover effects
   - Scrollable extended palette (200px height)
   - Callback architecture for parent widget updates

2. **Settings Integration**:
   - New "Appearance" tab in settings
   - Live color preview canvases (40x25px)
   - Immediate color application (no restart required)
   - Config persistence for all color choices

---

## 📦 Files Added/Modified

### New Files
- `core/shadow_tiny_lm.py` (218 lines)
- `core/model_version_detector.py` (246 lines)
- `output/color_palette.py` (362 lines)
- `docs/CHANGELOG_v2.0.3.md` (this file)

### Modified Files
- `core/unified_llm.py` (+50 lines)
  - Import Shadow Tiny LM and version detector
  - Default backend changed to `shadow_tiny`
  - API calls return tuple `(response, headers)`
  - Auto-detection call after API responses
  - New method: `get_detected_version(provider)`

- `output/gui.py` (+80 lines)
  - Import ColorPalette
  - New "Appearance" tab in settings
  - 3 color picker buttons (text, background, terminal)
  - Live color preview canvases
  - Immediate config updates on color change

---

## 🎨 User Guide

### Using Shadow Tiny LM
1. **Automatic**: Shadow Tiny LM is now the default backend
2. **Manual Switch**: Settings → Select backend
3. **Fallback**: If model not found, switch to Ollama/API backend
4. **Training**: Model learns from your usage (privacy-first, local only)

### Checking Detected Model Versions
1. When using API backends, Shadow automatically detects model versions
2. Version info printed to console: `Auto-detected openai model: gpt-4-turbo`
3. No manual version selection needed - Shadow figures it out automatically

### Customizing Colors
1. Open Settings (⚙ button)
2. Go to "Appearance" tab
3. Click "Change Color" next to any color option
4. Select from primary colors, extended grid, or custom picker
5. Click OK to apply immediately
6. Colors persist across sessions

---

## 📊 Statistics
- **Total Code**: 826 lines added across 6 files
- **Model Size**: 1.1 MB (Shadow Tiny LM)
- **Supported Providers**: 15 API providers with auto-detection
- **Color Palette**: 224 colors (8 primary + 216 web-safe)
- **Config Options**: 6 new settings (backend, text_color, bg_color, terminal_color, max_length, temperature)

---

## 📄 License
MIT License - Free for everyone, standalone and independent.

**Co-Authored-By: Warp <agent@warp.dev>**
