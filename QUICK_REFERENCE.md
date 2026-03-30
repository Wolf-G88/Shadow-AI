# Shadow AI v2.0.2 - Quick Reference

## 🚀 Launch
```bash
cd /home/wolfking/Downloads/shadow-ai-v2
./run.sh
```

## ✨ New Features

### Streaming Text
- **What**: AI responses appear word-by-word
- **How**: Just send any message normally
- **Why**: Provides real-time feedback like Warp terminal

### Shell Commands
- **Syntax**: `!command`
- **Example**: `!ls -la`, `!echo "hello"`, `!cat file.txt`
- **Output**: Live terminal output with colors
- **Status**: Shows ✅ SUCCESS or ❌ ERROR

### Status Bar
- **Location**: Bottom of window
- **States**: 
  - "Ready" (green) - Idle
  - "Shadow is thinking..." (green) - Processing

### Syntax Highlighting
- **Terminal output**: Green Courier New font
- **AI responses**: Black regular font
- **System messages**: Blue bold font

## 🔧 Settings

### Ollama Models (Tab 1)
- Use dropdown in top bar to select model
- Click "+ Pull" to download new models
- Examples: `llama3.2`, `mistral`, `llava`, `qwen2:0.5b`

### Custom GGUF (Tab 2)
- Load local .gguf model files
- Size limit: 8GB
- Models copied to `custom_models/` directory

### Remote API (Tab 3)
**15 Providers Available**:
1. Grok (X.AI) - `grok-beta`, `grok-3`, `grok-3-mini`
2. OpenAI - `gpt-4`, `gpt-3.5-turbo`, `o1-mini`
3. Claude (Anthropic) - `claude-3-5-sonnet-20241022`
4. Gemini (Google) - `gemini-pro`, `gemini-1.5-pro`, `gemini-1.5-flash`
5. Mistral AI - `mistral-large-latest`, `mistral-small-latest`
6. Cohere - `command-r-plus`
7. Together AI - Various open models
8. Perplexity AI - `llama-3.1-sonar-large-128k-online`
9. Groq - `llama-3.3-70b-versatile` (very fast!)
10. DeepSeek - `deepseek-chat`
11. Hugging Face - Any public model
12. OpenRouter - Aggregator of many models
13. Anyscale - Enterprise-grade endpoints
14. Fireworks AI - Fast inference

**To Use**:
1. Open Settings (⚙ button)
2. Go to "Remote API" tab
3. Select provider
4. Enter model name (e.g., `grok-3-mini`)
5. Enter your API key
6. Click "Save Settings"

## 🐛 Fixed Issues

| Issue | Status |
|-------|--------|
| Model selection crash | ✅ Fixed |
| First reply crash | ✅ Fixed |
| Config not saving | ✅ Fixed |
| Gemini 1.5 404 errors | ✅ Fixed |
| Missing API providers | ✅ Added 10 more |
| No visual feedback | ✅ Added streaming + status |

## 📊 Performance Tips

### For Faster Local Models
```bash
# Use tiny models on dual-core CPU
ollama pull qwen2:0.5b      # 352MB, fastest
ollama pull tinyllama       # 637MB
ollama pull gemma2:2b       # 1.6GB
```

### For Faster API
- **Groq**: Fastest (specialized chips)
- **Grok**: Good balance
- **Perplexity**: Fast with web search

## 🎯 Common Commands

### Shell Execution Examples
```bash
!ls                    # List files
!pwd                   # Current directory
!echo "test"          # Print text
!cat README.md        # Read file
!python3 --version    # Check Python
!git status           # Check git repo
```

### Model Management
```bash
# In terminal (not in Shadow AI)
ollama list           # See all models
ollama pull <model>   # Download model
ollama rm <model>     # Delete model
ollama ps             # See running models
```

## 🔍 Troubleshooting

### App Won't Start
```bash
# Check if Ollama is running
sudo systemctl status ollama

# Start Ollama if needed
sudo systemctl start ollama

# Check virtual environment
source venv/bin/activate
pip install ollama pillow gitpython requests
```

### Model Dropdown Empty
```bash
# Pull at least one model
ollama pull qwen2:0.5b

# Restart app
./run.sh
```

### API Not Working
1. Check API key is correct
2. Verify model name is valid for that provider
3. Check internet connection
4. Verify no rate limiting

### Settings Not Saving
```bash
# Check config file
cat ~/.shadow_ai_config.json

# Check permissions
ls -la ~/.shadow_ai_config.json

# Should be: -rw-r--r-- owned by you
```

## 📁 File Locations

| Item | Path |
|------|------|
| App directory | `/home/wolfking/Downloads/shadow-ai-v2` |
| Virtual env | `/home/wolfking/Downloads/shadow-ai-v2/venv` |
| Config file | `~/.shadow_ai_config.json` |
| Memory/history | `data/memory.json` |
| Custom GGUF models | `custom_models/` |
| Logs | Check terminal output |

## 🎨 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message |
| Esc | (none - add if needed) |
| Ctrl+C | Copy selected text |
| Ctrl+V | Paste into input |

## 💾 Config File Format

`~/.shadow_ai_config.json`:
```json
{
  "backend": "ollama",              // or "gguf" or "api"
  "ollama_model": "gemma2:2b",     
  "gguf_path": "",                  
  "api_provider": "grok",           // or "openai", "claude", etc.
  "api_key": "xai-...",            
  "api_model": "grok-3-mini",       
  "custom_models": []
}
```

## 🔐 API Key Format

| Provider | Key Format | Where to Get |
|----------|-----------|--------------|
| Grok | `xai-...` | console.x.ai |
| OpenAI | `sk-...` | platform.openai.com |
| Claude | `sk-ant-...` | console.anthropic.com |
| Gemini | `AIza...` | aistudio.google.com |
| Groq | `gsk_...` | console.groq.com |

## 📈 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | Dec 2025 | Initial release |
| 2.0.1 | Jan 2026 | Multi-backend support |
| 2.0.2 | Jan 2026 | **Bug fixes + streaming + 10 new APIs** |

## 🆘 Quick Help

**Model not responding?**
- Check status bar (bottom)
- Wait for "Ready" status
- Try smaller model if timeout

**API too slow?**
- Normal: 1-5 seconds
- Try Groq for faster response
- Check internet speed

**Shell command not working?**
- Prefix with `!`: `!ls` not `ls`
- Check command is valid
- Avoid dangerous commands

**Can't see streaming?**
- Should work automatically
- Check you're on v2.0.2
- Terminal output shows as green text

## 📞 Support

**Documentation**:
- `SUMMARY.md` - Overview
- `FIXES.md` - Technical details
- `README.md` - Original docs

**Testing**:
```bash
python3 test_fixes.py    # Verify all fixes
python3 -m py_compile output/gui.py  # Check syntax
```

**Community**:
- Check GitHub issues
- Review memory.json for errors
- Enable debug mode in code

---

**Quick Commands Summary**:
```bash
./run.sh                 # Launch app
!command                 # Execute shell command
Settings → Remote API    # Switch to cloud AI
+ Pull                   # Download model
⚙                        # Open settings
```

**Remember**: 
- Type `!` before shell commands
- API keys are stored locally
- Config persists between sessions
- Streaming works automatically
