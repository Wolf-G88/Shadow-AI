# Shadow AI v2.0.3 - Advanced Features Roadmap

## Overview
This roadmap outlines the next-generation enhancements for Shadow AI, implementing the cognitive architecture principles and Warp-like advanced features.

---

## Priority 1: Critical Safety & Reliability

### 1.1 Safety Gates ✅ IMPLEMENTED
**Status**: Complete in v2.0.2

- ✅ Command risk assessment (`_assess_command_risk`)
- ✅ Three-tier safety system (Critical/High/Medium)
- ✅ Confirmation dialogs for risky operations
- ✅ Critical command blocking (rm -rf, format, etc.)

**Test**:
```bash
# Should be blocked
!rm -rf /

# Should require confirmation
!rm test.txt

# Should show warning
!sudo apt remove python3
```

### 1.2 RAM Monitoring for GGUF Models
**Status**: Not implemented  
**Priority**: HIGH  
**Estimated effort**: 2-3 hours

**Implementation**:
```python
# In output/gui.py, load_gguf function
import psutil

def load_gguf():
    file_path = filedialog.askopenfilename(...)
    if file_path:
        size_gb = os.path.getsize(file_path) / (1024**3)
        
        # NEW: Check available RAM
        available_ram = psutil.virtual_memory().available / (1024**3)
        required_ram = size_gb * 1.5  # 50% margin for safe operation
        
        if required_ram > available_ram:
            gguf_path_var.set(
                f"Error: Insufficient RAM. Need {required_ram:.1f}GB, "
                f"have {available_ram:.1f}GB free."
            )
            return
        
        # Proceed with copy...
```

**Dependencies**:
```bash
pip install psutil
```

---

## Priority 2: User Experience Enhancements

### 2.1 Command History (Up/Down Arrows)
**Status**: Not implemented  
**Priority**: MEDIUM  
**Estimated effort**: 3-4 hours

**Implementation**:
```python
# In output/gui.py, __init__
self.command_history = []
self.history_index = -1

# Bind arrow keys
self.entry.bind("<Up>", self.history_up)
self.entry.bind("<Down>", self.history_down)

def history_up(self, event):
    if self.command_history and self.history_index < len(self.command_history) - 1:
        self.history_index += 1
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.command_history[-(self.history_index + 1)])
    return "break"  # Prevent default behavior

def history_down(self, event):
    if self.history_index > 0:
        self.history_index -= 1
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.command_history[-(self.history_index + 1)])
    elif self.history_index == 0:
        self.history_index = -1
        self.entry.delete(0, tk.END)
    return "break"

# In send_text, add to history
def send_text(self, event=None):
    msg = self.entry.get().strip()
    if msg:
        self.command_history.append(msg)
        self.history_index = -1
        # ... rest of code
```

### 2.2 Clickable File Paths in Output
**Status**: Not implemented  
**Priority**: MEDIUM  
**Estimated effort**: 4-5 hours

**Implementation**:
```python
import re
import webbrowser

# In __init__, add tag config
self.chat_log.tag_config("clickable", foreground="#58a6ff", underline=True)
self.chat_log.tag_bind("clickable", "<Button-1>", self.open_path)
self.chat_log.tag_bind("clickable", "<Enter>", 
                       lambda e: self.chat_log.config(cursor="hand2"))
self.chat_log.tag_bind("clickable", "<Leave>", 
                       lambda e: self.chat_log.config(cursor=""))

# In _process_queue, detect paths
def _process_queue(self):
    # ... existing code
    
    # If terminal output, check for file paths
    if msg_type == "terminal":
        self._insert_with_clickable_paths(content)
    else:
        self.chat_log.insert(tk.END, content, msg_type)

def _insert_with_clickable_paths(self, text):
    # Regex for file paths
    path_pattern = r'(/[^\s]+|\.{0,2}/[^\s]+|\w+\.(py|js|txt|md|json|sh|c|cpp|go|rs))'
    
    last_end = 0
    for match in re.finditer(path_pattern, text):
        # Insert text before match
        if match.start() > last_end:
            self.chat_log.insert(tk.END, text[last_end:match.start()], "terminal")
        
        # Insert clickable path
        path = match.group()
        self.chat_log.insert(tk.END, path, ("terminal", "clickable"))
        self.chat_log.tag_add(f"path_{match.start()}", 
                              f"end-{len(path)}c", "end")
        self.chat_log.tag_bind(f"path_{match.start()}", "<Button-1>",
                              lambda e, p=path: self.open_path(p))
        
        last_end = match.end()
    
    # Insert remaining text
    if last_end < len(text):
        self.chat_log.insert(tk.END, text[last_end:], "terminal")

def open_path(self, path):
    """Open file path in default editor."""
    if os.path.exists(path):
        if os.path.isfile(path):
            # Open file
            webbrowser.open(f"file://{os.path.abspath(path)}")
        elif os.path.isdir(path):
            # Open directory
            webbrowser.open(f"file://{os.path.abspath(path)}")
```

### 2.3 Improved Status Bar with Activity Indicator
**Status**: Partial  
**Priority**: LOW  
**Estimated effort**: 1-2 hours

**Enhancement**:
```python
# Add animated "thinking" indicator
def _animate_status(self):
    if self.status_bar.cget("text").startswith("Shadow is thinking"):
        dots = self.status_bar.cget("text").count(".")
        new_dots = "." * ((dots % 3) + 1)
        self.status_bar.config(text=f"Shadow is thinking{new_dots}")
        self.root.after(500, self._animate_status)

# Call in send_text
def send_text(self, event=None):
    # ... existing code
    self.status_bar.config(text="Shadow is thinking")
    self._animate_status()
```

---

## Priority 3: Advanced Cognitive Features

### 3.1 Memory Compression & Staleness Detection
**Status**: Not implemented  
**Priority**: MEDIUM  
**Estimated effort**: 5-6 hours

**Implementation** in `core/memory.py`:
```python
import hashlib
from datetime import datetime

class MemoryBank:
    def __init__(self, path="data/memory.json"):
        self.path = path
        self.history = []
        self.stale = False
        self.last_command_time = None
    
    def mark_stale(self):
        """Mark memory as stale after shell command execution."""
        self.stale = True
        self.last_command_time = datetime.now().isoformat()
    
    def compress(self):
        """Compress memory every 10 blocks."""
        if len(self.history) > 50:
            # Summarize old exchanges
            summary = {
                "user": "[Compressed history]",
                "assistant": f"Previous {len(self.history) - 50} exchanges summarized.",
                "timestamp": datetime.now().isoformat()
            }
            self.history = [summary] + self.history[-50:]
    
    def deduplicate(self):
        """Remove duplicate context based on content hash."""
        seen_hashes = set()
        unique_history = []
        
        for entry in self.history:
            content = f"{entry['user']} {entry['assistant']}"
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_history.append(entry)
        
        self.history = unique_history
```

### 3.2 Quantum-Like Multi-Backend Selection
**Status**: Partial (manual selection only)  
**Priority**: MEDIUM  
**Estimated effort**: 6-8 hours

**Concept**: Automatically choose optimal backend based on query characteristics.

**Implementation** in `core/engine.py`:
```python
class ShadowCore:
    def process(self, text, files=None):
        # Quantum folding: Evaluate all backends simultaneously
        optimal_backend = self._select_optimal_backend(text, files)
        
        # Temporarily switch to optimal backend
        original_backend = self.config.get("backend")
        self.config.set("backend", optimal_backend)
        
        try:
            reply = self._generate_with_backend(text, files, optimal_backend)
        finally:
            # Restore original backend
            self.config.set("backend", original_backend)
        
        return reply
    
    def _select_optimal_backend(self, text, files):
        """Quantum-like folding: Choose optimal path."""
        # Vision task → requires llava or API
        if files and any(f.endswith(('.png', '.jpg')) for f in files):
            if self._has_vision_model():
                return "ollama"
            else:
                return "api"  # Fallback to API with vision
        
        # Long complex query → API for best quality
        if len(text) > 500:
            if self.config.get("api_key"):
                return "api"
        
        # Quick question → local for speed
        if len(text) < 100:
            return "ollama"
        
        # Default to current backend
        return self.config.get("backend", "ollama")
    
    def _has_vision_model(self):
        models = self.llm.list_models()
        return any("llava" in m.lower() for m in models)
```

### 3.3 Progressive Validation System
**Status**: Not implemented  
**Priority**: HIGH for kernel dev  
**Estimated effort**: 8-10 hours

**Concept**: Small-scale test → validate → scale to full.

**Implementation**:
```python
class ProgressiveValidator:
    """Implements prove-through-action validation."""
    
    def __init__(self):
        self.validation_log = []
    
    def validate_compilation(self, project_path):
        """Progressive scaling: single file → module → full project."""
        stages = [
            ("single_file", self.compile_single_file),
            ("module", self.compile_module),
            ("full_project", self.compile_full_project)
        ]
        
        for stage_name, stage_func in stages:
            success, output = stage_func(project_path)
            
            self.validation_log.append({
                "stage": stage_name,
                "success": success,
                "output": output,
                "timestamp": datetime.now().isoformat()
            })
            
            if not success:
                return False, f"Failed at {stage_name}: {output}"
        
        return True, "All stages validated successfully"
    
    def compile_single_file(self, project_path):
        # Find simplest .c or .zig file
        # Compile in isolation
        pass
    
    def compile_module(self, project_path):
        # Compile related files as module
        pass
    
    def compile_full_project(self, project_path):
        # Full build
        pass
```

---

## Priority 4: Security Hardening

### 4.1 CORS Policy Restriction
**Status**: Not implemented (if FastAPI backend exists)  
**Priority**: HIGH  
**File**: `backend/main.py` (if exists)

**Fix**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],  # Changed from ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.2 Config File Permissions
**Status**: Needs verification  
**Priority**: MEDIUM

**Check**:
```bash
ls -la ~/.shadow_ai_config.json
# Should be: -rw------- (0600)
```

**Fix**:
```python
# In core/config.py, save method
def save(self):
    try:
        with open(self.config_path, 'w') as f:
            json.dump(self.data, f, indent=2)
        
        # Set secure permissions (owner read/write only)
        os.chmod(self.config_path, 0o600)
    except Exception as e:
        print(f"Could not save config: {e}")
```

---

## Priority 5: Provider-Specific Tool Calling

### 5.1 Specialized Tool Formats
**Status**: Not implemented  
**Priority**: MEDIUM  
**Affected**: DeepSeek, Mistral, Cohere

**Implementation** in `core/unified_llm.py`:
```python
def _call_deepseek(self, prompt, api_key):
    """DeepSeek-specific implementation with tool calling."""
    model = self.config.get("api_model", "deepseek-chat")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # DeepSeek supports function calling
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "execute_shell",
                    "description": "Execute shell command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"}
                        }
                    }
                }
            }
        ],
        "max_tokens": 2048
    }
    
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers=headers, json=data, timeout=60
    )
    response.raise_for_status()
    
    result = response.json()
    
    # Handle tool calls
    if "tool_calls" in result['choices'][0]['message']:
        # Process tool calls
        pass
    
    return result['choices'][0]['message']['content']
```

---

## Testing Checklist for v2.0.3

### Safety Features
- [ ] Critical commands blocked (rm -rf, format)
- [ ] High-risk commands show confirmation dialog
- [ ] Medium-risk commands show warning
- [ ] Safe commands execute without prompts

### UX Enhancements
- [ ] Up arrow recalls previous commands
- [ ] Down arrow navigates forward in history
- [ ] File paths in terminal output are clickable
- [ ] Clicking path opens file in default editor
- [ ] Status bar shows animated thinking indicator

### Memory & Performance
- [ ] GGUF models check RAM before loading
- [ ] Memory compresses after 50 exchanges
- [ ] Duplicate context is deduplicated
- [ ] Memory marked stale after !command

### Security
- [ ] Config file has 0600 permissions
- [ ] CORS restricted to localhost
- [ ] API keys never logged in plain text

---

## Implementation Timeline

**Week 1**: Priority 1 (Safety & Reliability)
- Days 1-2: RAM monitoring for GGUF
- Days 3-5: Test and validate safety gates

**Week 2**: Priority 2 (UX Enhancements)
- Days 1-2: Command history
- Days 3-4: Clickable paths
- Day 5: Status bar animations

**Week 3**: Priority 3 (Cognitive Features)
- Days 1-2: Memory compression
- Days 3-5: Quantum backend selection

**Week 4**: Priority 4-5 (Security & Tools)
- Days 1-2: Security hardening
- Days 3-5: Provider-specific tool calling

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| RAM check coverage | 100% GGUF loads | 0% |
| Command history recall | Works reliably | Not implemented |
| Clickable path detection | >90% accuracy | Not implemented |
| Memory compression | Auto at 50 msgs | Manual only |
| Safety gate coverage | 100% dangerous cmds | 80% |

---

## Long-Term Vision (v3.0+)

1. **Full Warp Terminal Integration**: Native Warp block support
2. **Multi-Agent Collaboration**: Shadow instances share knowledge
3. **Voice Interface**: Speech-to-text for hands-free coding
4. **Custom Plugin System**: User-defined tool extensions
5. **Distributed Inference**: Load balance across multiple backends
6. **Real-Time Collaboration**: Multiple users in same Shadow session

---

**Current Version**: 2.0.2  
**Next Release**: 2.0.3 (ETA: 2-4 weeks)  
**Status**: In planning phase
