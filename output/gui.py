import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from PIL import Image, ImageTk
import os
import glob
import ctypes
import subprocess
import threading
import queue
import psutil
import pynvml
import re
import zipfile
import xml.etree.ElementTree as ET
import base64
import io
from datetime import datetime
from input.file import select_files
from core.agent_formatting import format_agent_reply
from core.agent_recipes import detect_agent_recipe, format_task_recipe_notice, format_task_recipe_status
from core.app_paths import get_models_dir
from core.resource_paths import get_resource_root
from core.engine import ShadowCore
from core.memory import MemoryBank
from core.shell_safety import assess_command_risk, build_exec_plan, summarize_command_policies
from output.color_palette import ColorPalette

class GUI:
    WINDOWS_APP_ID = "WolfClan.ShadowAI"
    TEXT_ATTACHMENT_EXTENSIONS = {
        '.txt', '.md', '.log', '.text', '.csv', '.json', '.xml', '.yaml', '.yml',
        '.ini', '.conf', '.cfg', '.toml', '.sh', '.bash', '.py', '.js', '.ts',
        '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php',
        '.html', '.css', '.jsx', '.tsx', '.vue', '.sql', '.r', '.pl', '.lua',
        '.swift', '.kt', '.dart', '.scala', '.ex', '.exs', '.clj', '.hs', '.ml',
        '.tex', '.rst', '.adoc', '.org', '.rtf'
    }
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    def __init__(self):
        self.memory = MemoryBank()
        self.memory.load()
        self.core = ShadowCore(self.memory)
        self.last_file_path = None
        self.last_file_type = None
        self.window_icon = None

        self._configure_windows_app_id()
        self.root = tk.Tk()
        self._configure_window_icon()
        self.root.title("Shadow AI")
        self.root.geometry("1400x800")
        self.root.configure(bg="#1a1a1a")
        
        # Message queue for streaming
        self.msg_queue = queue.Queue()
        self.command_history = []
        self.history_index = -1
        self.active_ai_block = False
        self.active_ai_close = None
        self.rect_select_active = False
        self.rect_sel_ranges = []

        # Top bar: Model selector (full width, large font)
        top_frame = tk.Frame(self.root, bg="#2a2a2a", height=60)
        top_frame.pack(fill=tk.X, padx=0, pady=0)
        top_frame.pack_propagate(False)
        
        tk.Label(top_frame, text="Model:", bg="#2a2a2a", fg="white", 
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=15)
        
        self.model_var = tk.StringVar(value="gemma2:2b")
        self.model_menu = ttk.Combobox(top_frame, textvariable=self.model_var, 
                                 font=("Arial", 14), width=40, state="readonly")
        self.model_menu['values'] = self.core.llm.list_models()
        if self.model_menu['values']:
            self.model_menu.set(self.model_menu['values'][0])
        self.model_menu.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
        self.model_menu.bind('<<ComboboxSelected>>', self.change_model)
        
        # Pull Model button
        pull_btn = tk.Button(top_frame, text="+ Pull", 
                            command=self.pull_model,
                            bg="#4a4a4a", fg="white",
                            font=("Arial", 10, "bold"),
                            relief=tk.FLAT,
                            activebackground="#5a5a5a")
        pull_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Agent Mode toggle
        self.agent_mode = tk.BooleanVar(value=False)
        agent_btn = tk.Checkbutton(top_frame, text="Agent", variable=self.agent_mode,
                                   bg="#2a2a2a", fg="white", selectcolor="#2a2a2a",
                                   font=("Arial", 10, "bold"), relief=tk.FLAT,
                                   activebackground="#2a2a2a", activeforeground="white",
                                   command=self._toggle_agent_mode)
        agent_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Agent backend selector (used only when Agent Mode is ON)
        agent_backend_options = ["Use current", "Ollama", "GGUF", "API"]
        saved_agent_backend = self.core.config.get("agent_backend", "Use current")
        if saved_agent_backend not in agent_backend_options:
            saved_agent_backend = "Use current"
        self.agent_backend_var = tk.StringVar(value=saved_agent_backend)
        self.agent_backend_menu = ttk.Combobox(
            top_frame, textvariable=self.agent_backend_var,
            values=agent_backend_options, state="readonly",
            font=("Arial", 10), width=12
        )
        self.agent_backend_menu.pack(side=tk.RIGHT, padx=10, pady=10)
        tk.Label(top_frame, text="Agent:", bg="#2a2a2a", fg="white",
                 font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=(0, 5))
        self.agent_backend_menu.bind('<<ComboboxSelected>>', self._on_agent_backend_change)

        # Settings gear button
        settings_btn = tk.Button(top_frame, text="⚙", 
                                command=self.open_settings,
                                bg="#4a4a4a", fg="white",
                                font=("Arial", 14),
                                width=3, relief=tk.FLAT,
                                activebackground="#5a5a5a")
        settings_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        # Main container for left (chat) and right (preview) panels
        main_container = tk.Frame(self.root, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel (70%): Chat log
        left_panel = tk.Frame(main_container, bg="#ffffff")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(left_panel, text="Chat Log", bg="#ffffff", fg="#333333",
                font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(5, 0))
        
        self.chat_log = scrolledtext.ScrolledText(left_panel, wrap=tk.WORD, 
                                                   bg="#ffffff", fg="#1a1a1a",
                                                   font=("Arial", 11),
                                                   state=tk.DISABLED,
                                                   relief=tk.FLAT)
        self.chat_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Right panel (30%): Preview area
        right_panel = tk.Frame(main_container, bg="#f5f5f5", width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_panel.pack_propagate(False)
        
        tk.Label(right_panel, text="Preview", bg="#f5f5f5", fg="#333333",
                font=("Arial", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(5, 0))
        
        self.preview_frame = tk.Frame(right_panel, bg="#f5f5f5")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # System monitoring overlay (always on)
        self.nvml_available = False
        try:
            pynvml.nvmlInit()
            self.nvml_available = True
        except:
            self.nvml_available = False
        self.cpu_label = tk.Label(self.preview_frame, text="Cpu", 
                                 bg="#f5f5f5", fg="#333333",
                                 font=("Arial", 12, "bold"), anchor=tk.W)
        self.cpu_label.pack(fill=tk.X, pady=(0, 5))
        self.cpu_canvas = tk.Canvas(self.preview_frame, height=20, bg="#f5f5f5", 
                                   highlightthickness=0)
        self.cpu_canvas.pack(fill=tk.X, pady=(0, 10))
        
        self.ram_label = tk.Label(self.preview_frame, text="Ram", 
                                 bg="#f5f5f5", fg="#333333",
                                 font=("Arial", 12, "bold"), anchor=tk.W)
        self.ram_label.pack(fill=tk.X, pady=(0, 5))
        self.ram_canvas = tk.Canvas(self.preview_frame, height=20, bg="#f5f5f5", 
                                   highlightthickness=0)
        self.ram_canvas.pack(fill=tk.X, pady=(0, 10))
        
        self.disk_label = tk.Label(self.preview_frame, text="HD", 
                                  bg="#f5f5f5", fg="#333333",
                                  font=("Arial", 12, "bold"), anchor=tk.W)
        self.disk_label.pack(fill=tk.X, pady=(0, 5))
        self.disk_canvas = tk.Canvas(self.preview_frame, height=20, bg="#f5f5f5", 
                                    highlightthickness=0)
        self.disk_canvas.pack(fill=tk.X, pady=(0, 10))
        
        # GPU section (all GPUs)
        self.gpu_bars = []
        self.gpus = self._detect_gpus()
        for idx, gpu in enumerate(self.gpus):
            label = tk.Label(self.preview_frame, text=f"Gpu {idx}: {gpu['name']}", 
                             bg="#f5f5f5", fg="#333333",
                             font=("Arial", 12, "bold"), anchor=tk.W)
            label.pack(fill=tk.X, pady=(0, 5))
            canvas = tk.Canvas(self.preview_frame, height=20, bg="#f5f5f5", 
                               highlightthickness=0)
            canvas.pack(fill=tk.X, pady=(0, 10 if idx < len(self.gpus) - 1 else 0))
            self.gpu_bars.append(canvas)
        
        # Preview info label (kept minimal so overlay stays visible)
        self.preview_info = tk.Label(self.preview_frame, 
                                     text="Drop file or click + to analyze",
                                     bg="#f5f5f5", fg="#888888",
                                     font=("Arial", 9, "italic"),
                                     wraplength=350, justify=tk.CENTER)
        self.preview_info.pack(pady=(10, 0))
        
        # Start monitoring thread
        self.monitoring_active = True
        threading.Thread(target=self._update_system_stats, daemon=True).start()

        # Bottom bar: Input field with buttons
        bottom_frame = tk.Frame(self.root, bg="#2a2a2a", height=60)
        bottom_frame.pack(fill=tk.X, padx=0, pady=0)
        bottom_frame.pack_propagate(False)
        
        # + button for file upload
        self.file_btn = tk.Button(bottom_frame, text="+", 
                                  command=self.send_file,
                                  bg="#4a4a4a", fg="white",
                                  font=("Arial", 16, "bold"),
                                  width=3, relief=tk.FLAT,
                                  activebackground="#5a5a5a")
        self.file_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Repo button for Git URL
        self.repo_btn = tk.Button(bottom_frame, text="📦", 
                                  command=self.clone_repo,
                                  bg="#4a4a4a", fg="white",
                                  font=("Arial", 14),
                                  width=3, relief=tk.FLAT,
                                  activebackground="#5a5a5a")
        self.repo_btn.pack(side=tk.LEFT, padx=(0, 10), pady=10)
        
        # Multiline input field (terminal editor)
        self.entry = tk.Text(bottom_frame, bg="#3a3a3a", fg="white",
                             font=("Arial", 12), relief=tk.FLAT, height=3,
                             wrap=tk.WORD, insertbackground="white")
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=10)
        self.entry.bind("<Return>", self.send_text)
        self.entry.bind("<Shift-Return>", self._insert_newline)
        self.entry.bind("<Up>", self._history_up)
        self.entry.bind("<Down>", self._history_down)
        self.entry.bind("<Alt-Button-1>", self._rect_sel_start)
        self.entry.bind("<Alt-B1-Motion>", self._rect_sel_drag)
        self.entry.bind("<Alt-ButtonRelease-1>", self._rect_sel_end)
        self.entry.bind("<Control-c>", self._copy_selection)
        
        # Send button
        self.send_btn = tk.Button(bottom_frame, text="Send", 
                                 command=self.send_text,
                                 bg="#0066cc", fg="white",
                                 font=("Arial", 11, "bold"),
                                 width=8, relief=tk.FLAT,
                                 activebackground="#0052a3")
        self.send_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Status bar at the bottom for visual feedback
        self.status_bar = tk.Label(self.root, text="Ready", 
                                   bg="#1a1a1a", fg="#00ff41",
                                   font=("Courier New", 9),
                                   anchor=tk.W, padx=10)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Configure chat log tags for styling
        self.chat_log.tag_config("terminal", foreground="#00FF41", font=("Courier New", 10))
        self.chat_log.tag_config("ai", foreground="#1a1a1a")
        self.chat_log.tag_config("system", foreground="#0066cc", font=("Arial", 10, "bold"))
        self.chat_log.tag_config("block_user", background="#f7f7f7")
        self.chat_log.tag_config("block_ai", background="#f1f5ff")
        self.chat_log.tag_config("block_header", foreground="#555555", font=("Arial", 9, "bold"))
        self.chat_log.tag_config("rectsel", background="#555555", foreground="#ffffff")

    def change_model(self, event=None):
        selected = self.model_var.get()
        
        # Detect if TinyLM (SILS) is selected
        if "TinyLM" in selected and "SILS" in selected:
            self.core.config.set("backend", "sils")
            self.append_chat(f"[System: Switched to {selected}]")
        else:
            # Assume it's an Ollama model
            self.core.config.set("backend", "ollama")
            self.core.config.set("ollama_model", selected)
            self.append_chat(f"[System: Switched to {selected}]")
    
    def pull_model(self):
        # Dialog to enter model name
        pull_window = tk.Toplevel(self.root)
        pull_window.title("Pull Ollama Model")
        pull_window.geometry("500x200")
        pull_window.configure(bg="#2a2a2a")
        
        tk.Label(pull_window, text="Enter model name (e.g., llama3.2, mistral, llava):",
                bg="#2a2a2a", fg="white", font=("Arial", 11)).pack(pady=15)
        
        name_entry = tk.Entry(pull_window, width=40, font=("Arial", 12))
        name_entry.pack(pady=5, padx=20)
        name_entry.focus()
        
        status_label = tk.Label(pull_window, text="", bg="#2a2a2a", fg="#ffaa00",
                               font=("Arial", 10), wraplength=450)
        status_label.pack(pady=10)
        
        def do_pull():
            model_name = name_entry.get().strip()
            if not model_name:
                return
            
            status_label.config(text=f"Pulling {model_name}... This may take several minutes.")
            pull_window.update()
            
            def pull_in_thread():
                try:
                    result = subprocess.run(['ollama', 'pull', model_name],
                                          capture_output=True, text=True, timeout=600)
                    
                    if result.returncode == 0:
                        # Refresh model list
                        self.root.after(0, lambda: self._refresh_models(model_name, pull_window))
                    else:
                        self.root.after(0, lambda: status_label.config(
                            text=f"Error: {result.stderr or 'Failed to pull model'}"))
                except subprocess.TimeoutExpired:
                    self.root.after(0, lambda: status_label.config(text="Error: Pull timed out"))
                except Exception as e:
                    self.root.after(0, lambda: status_label.config(text=f"Error: {str(e)}"))
            
            threading.Thread(target=pull_in_thread, daemon=True).start()
        
        tk.Button(pull_window, text="Pull Model", command=do_pull,
                 bg="#0066cc", fg="white", font=("Arial", 11, "bold")).pack(pady=10)
    
    def _refresh_models(self, new_model, window):
        # Refresh the dropdown with new model list
        models = self.core.llm.list_models()
        self.model_menu['values'] = models
        self.model_var.set(new_model)
        # Update config instead of nonexistent model attribute
        self.core.config.set("ollama_model", new_model)
        self.append_chat(f"[System: Pulled and switched to {new_model}]")
        window.destroy()
    
    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Shadow AI Settings")
        settings_window.geometry("600x400")
        settings_window.configure(bg="#2a2a2a")
        
        # Create notebook for tabs
        from tkinter import ttk
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Local Ollama Models
        ollama_tab = tk.Frame(notebook, bg="#2a2a2a")
        notebook.add(ollama_tab, text="Ollama Models")
        
        tk.Label(ollama_tab, text="Current Ollama models", bg="#2a2a2a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=15)
        tk.Label(ollama_tab, text="Use the '+ Pull' button to download more models from Ollama library.",
                bg="#2a2a2a", fg="#aaaaaa", font=("Arial", 10)).pack(pady=5)
        
        # Tab 2: Appearance
        appearance_tab = tk.Frame(notebook, bg="#2a2a2a")
        notebook.add(appearance_tab, text="Appearance")
        
        tk.Label(appearance_tab, text="Customize Shadow AI Appearance", bg="#2a2a2a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=15)
        
        # Text color button
        text_color_frame = tk.Frame(appearance_tab, bg="#2a2a2a")
        text_color_frame.pack(pady=10)
        
        tk.Label(text_color_frame, text="Chat Text Color:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        text_color_var = tk.StringVar(value=self.core.config.get("text_color", "#1a1a1a"))
        self.text_color_display = tk.Canvas(text_color_frame, width=40, height=25, 
                                           bg=text_color_var.get(), highlightthickness=1)
        self.text_color_display.pack(side=tk.LEFT, padx=5)
        
        def change_text_color():
            def on_color_selected(color):
                text_color_var.set(color)
                self.text_color_display.config(bg=color)
                self.core.config.set("text_color", color)
                self.chat_log.tag_config("ai", foreground=color)
                self.append_chat(f"[System: Text color changed to {color}]")
            
            ColorPalette.show_palette(settings_window, on_color_selected, text_color_var.get())
        
        tk.Button(text_color_frame, text="Change Color", command=change_text_color,
                 bg="#4a4a4a", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # Background color button
        bg_color_frame = tk.Frame(appearance_tab, bg="#2a2a2a")
        bg_color_frame.pack(pady=10)
        
        tk.Label(bg_color_frame, text="Chat Background:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        bg_color_var = tk.StringVar(value=self.core.config.get("bg_color", "#ffffff"))
        self.bg_color_display = tk.Canvas(bg_color_frame, width=40, height=25,
                                         bg=bg_color_var.get(), highlightthickness=1)
        self.bg_color_display.pack(side=tk.LEFT, padx=5)
        
        def change_bg_color():
            def on_color_selected(color):
                bg_color_var.set(color)
                self.bg_color_display.config(bg=color)
                self.core.config.set("bg_color", color)
                self.chat_log.config(bg=color)
                self.append_chat(f"[System: Background changed to {color}]")
            
            ColorPalette.show_palette(settings_window, on_color_selected, bg_color_var.get())
        
        tk.Button(bg_color_frame, text="Change Color", command=change_bg_color,
                 bg="#4a4a4a", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # Terminal color button
        term_color_frame = tk.Frame(appearance_tab, bg="#2a2a2a")
        term_color_frame.pack(pady=10)
        
        tk.Label(term_color_frame, text="Terminal Text:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        term_color_var = tk.StringVar(value=self.core.config.get("terminal_color", "#00FF41"))
        self.term_color_display = tk.Canvas(term_color_frame, width=40, height=25,
                                           bg=term_color_var.get(), highlightthickness=1)
        self.term_color_display.pack(side=tk.LEFT, padx=5)
        
        def change_term_color():
            def on_color_selected(color):
                term_color_var.set(color)
                self.term_color_display.config(bg=color)
                self.core.config.set("terminal_color", color)
                self.chat_log.tag_config("terminal", foreground=color)
                self.append_chat(f"[System: Terminal color changed to {color}]")
            
            ColorPalette.show_palette(settings_window, on_color_selected, term_color_var.get())
        
        tk.Button(term_color_frame, text="Change Color", command=change_term_color,
                 bg="#4a4a4a", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # Tab 3: Custom GGUF Models
        gguf_tab = tk.Frame(notebook, bg="#2a2a2a")
        notebook.add(gguf_tab, text="Custom GGUF")
        
        tk.Label(gguf_tab, text="Load your own GGUF model", bg="#2a2a2a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=15)
        tk.Label(gguf_tab, text="Select a .gguf file from your computer. Recommended: < 8GB",
                bg="#2a2a2a", fg="#aaaaaa", font=("Arial", 10)).pack(pady=5)
        
        gguf_path_var = tk.StringVar(value="No GGUF model loaded")
        tk.Label(gguf_tab, textvariable=gguf_path_var, bg="#2a2a2a", fg="#ffaa00",
                font=("Arial", 9), wraplength=500).pack(pady=10)
        
        def load_gguf():
            file_path = filedialog.askopenfilename(
                title="Select GGUF Model",
                filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
            )
            if file_path:
                # Check file size
                size_gb = os.path.getsize(file_path) / (1024**3)
                if size_gb > 8:
                    gguf_path_var.set(f"Error: File too large ({size_gb:.1f} GB). Max 8 GB.")
                    return
                
                # Copy to custom_models directory
                custom_dir = str(get_models_dir())
                os.makedirs(custom_dir, exist_ok=True)
                
                import shutil
                model_name = os.path.basename(file_path)
                dest_path = os.path.join(custom_dir, model_name)
                
                gguf_path_var.set(f"Copying {model_name}...")
                settings_window.update()
                
                shutil.copy2(file_path, dest_path)
                gguf_path_var.set(f"Loaded: {model_name} ({size_gb:.1f} GB)")
                
                # Wire GGUF backend to config
                self.core.config.set("backend", "gguf")
                self.core.config.set("gguf_path", dest_path)
                
                # Refresh model selector and show confirmation
                self.model_var.set(f"GGUF: {model_name}")
                self.append_chat(f"[System: Switched to GGUF backend: {model_name}]")
        
        tk.Button(gguf_tab, text="Select GGUF File", command=load_gguf,
                 bg="#0066cc", fg="white", font=("Arial", 11, "bold")).pack(pady=15)
        
        # Tab 3: Remote API
        api_tab = tk.Frame(notebook, bg="#2a2a2a")
        notebook.add(api_tab, text="Remote API")
        
        tk.Label(api_tab, text="Use cloud API for unlimited power", bg="#2a2a2a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=15)
        
        tk.Label(api_tab, text="Provider:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(pady=(10,5))
        
        # Load saved settings
        saved_backend = self.core.config.get("backend", "ollama")
        saved_provider = self.core.config.get("api_provider", "local")
        saved_key = self.core.config.get("api_key", "")
        
        # Map internal provider codes to display names
        provider_display = {
            "local": "Local Only",
            "grok": "Grok (X.AI)",
            "openai": "OpenAI (GPT-4/ChatGPT)",
            "claude": "Claude (Anthropic)",
            "gemini": "Gemini (Google)"
        }
        
        initial_provider = "Local Only"
        if saved_backend == "api" and saved_key:
            initial_provider = provider_display.get(saved_provider, "Local Only")
        
        provider_var = tk.StringVar(value=initial_provider)
        provider_menu = ttk.Combobox(api_tab, textvariable=provider_var,
                                    values=[
                                        "Local Only",
                                        "Grok (X.AI)",
                                        "OpenAI (GPT-4/ChatGPT)",
                                        "Claude (Anthropic)",
                                        "Gemini (Google)",
                                        "Mistral AI",
                                        "Cohere",
                                        "Together AI",
                                        "Perplexity AI",
                                        "Groq",
                                        "DeepSeek",
                                        "Hugging Face",
                                        "OpenRouter",
                                        "Anyscale",
                                        "Fireworks AI"
                                    ],
                                    state="readonly", font=("Arial", 11), width=35)
        provider_menu.pack(pady=5)
        
        tk.Label(api_tab, text="Model Name (e.g., grok-3, grok-3-mini, gpt-4):", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(pady=(15,5))
        
        saved_model = self.core.config.get("api_model", "grok-beta")
        api_model_entry = tk.Entry(api_tab, width=50, font=("Arial", 10))
        api_model_entry.insert(0, saved_model)
        api_model_entry.pack(pady=5)
        
        tk.Label(api_tab, text="API Key:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(pady=(15,5))
        
        api_key_entry = tk.Entry(api_tab, width=50, font=("Arial", 10), show="*")
        if saved_key:
            api_key_entry.insert(0, saved_key)
        api_key_entry.pack(pady=5)
        
        status_label = tk.Label(api_tab, text="", bg="#2a2a2a", fg="#00ff00",
                               font=("Arial", 9))
        status_label.pack(pady=10)
        
        def save_api_settings():
            provider = provider_var.get()
            api_key = api_key_entry.get().strip()
            api_model = api_model_entry.get().strip()
            
            if provider == "Local Only" or not api_key:
                self.core.config.set("backend", "ollama")
                self.core.config.set("api_key", "")
                status_label.config(text="Using local models only")
                self.append_chat(f"[System: Switched to local Ollama]")
            else:
                # Map provider names to API provider codes
                provider_map = {
                    "Grok (X.AI)": "grok",
                    "OpenAI (GPT-4/ChatGPT)": "openai",
                    "Claude (Anthropic)": "claude",
                    "Gemini (Google)": "gemini",
                    "Mistral AI": "mistral",
                    "Cohere": "cohere",
                    "Together AI": "together",
                    "Perplexity AI": "perplexity",
                    "Groq": "groq",
                    "DeepSeek": "deepseek",
                    "Hugging Face": "huggingface",
                    "OpenRouter": "openrouter",
                    "Anyscale": "anyscale",
                    "Fireworks AI": "fireworks"
                }
                
                api_provider = provider_map.get(provider, "grok")
                self.core.config.set("backend", "api")
                self.core.config.set("api_provider", api_provider)
                self.core.config.set("api_key", api_key)
                self.core.config.set("api_model", api_model)
                status_label.config(text=f"Saved: Using {provider} ({api_model})")
                self.append_chat(f"[System: Switched to {provider} with {api_model}]")
        
        tk.Button(api_tab, text="Save Settings", command=save_api_settings,
                 bg="#0066cc", fg="white", font=("Arial", 11, "bold")).pack(pady=15)
        
        tk.Label(api_tab, text="Clear API key to return to local models",
                bg="#2a2a2a", fg="#888888", font=("Arial", 9)).pack(pady=5)
    def _on_agent_backend_change(self, event=None):
        selected = self.agent_backend_var.get()
        self.core.config.set("agent_backend", selected)
        self.append_chat(f"[System: Agent backend set to {selected}]")

    def _get_agent_override(self):
        selection = self.agent_backend_var.get()
        if selection == "Use current":
            return None
        if selection == "Ollama":
            model = self.model_var.get()
            if not model:
                self.append_chat("[System: No Ollama model selected for Agent]")
                return None
            return {"backend": "ollama", "ollama_model": model}
        if selection == "GGUF":
            gguf_path = self.core.config.get("gguf_path", "")
            if not gguf_path or not os.path.exists(gguf_path):
                self.append_chat("[System: No GGUF model loaded. Use Settings > Custom GGUF.]")
                return None
            return {"backend": "gguf", "gguf_path": gguf_path}
        if selection == "API":
            api_key = self.core.config.get("api_key", "")
            api_provider = self.core.config.get("api_provider", "")
            api_model = self.core.config.get("api_model", "")
            if not api_key or not api_provider:
                self.append_chat("[System: API not configured. Use Settings > Remote API.]")
                return None
            return {
                "backend": "api",
                "api_provider": api_provider,
                "api_key": api_key,
                "api_model": api_model
            }
        return None

    def _toggle_agent_mode(self):
        if self.agent_mode.get():
            self.status_bar.config(text="Agent Mode: ON")
        else:
            self.status_bar.config(text="Ready")

    def _get_input_text(self):
        return self.entry.get("1.0", tk.END).rstrip()

    def _set_input_text(self, text):
        self.entry.delete("1.0", tk.END)
        self.entry.insert("1.0", text)

    def _insert_newline(self, event=None):
        self.entry.insert(tk.INSERT, "\n")
        return "break"

    def _history_up(self, event=None):
        text = self._get_input_text()
        if "\n" in text:
            return None
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self._set_input_text(self.command_history[-(self.history_index + 1)])
        return "break"

    def _history_down(self, event=None):
        text = self._get_input_text()
        if "\n" in text:
            return None
        if self.history_index > 0:
            self.history_index -= 1
            self._set_input_text(self.command_history[-(self.history_index + 1)])
        elif self.history_index == 0:
            self.history_index = -1
            self._set_input_text("")
        return "break"

    def _rect_sel_start(self, event):
        self.rect_select_active = True
        self.rect_sel_ranges = []
        self.entry.tag_remove("rectsel", "1.0", tk.END)
        self._rect_start = self.entry.index(f"@{event.x},{event.y}")
        return "break"

    def _rect_sel_drag(self, event):
        if not self.rect_select_active:
            return "break"
        self.entry.tag_remove("rectsel", "1.0", tk.END)
        end = self.entry.index(f"@{event.x},{event.y}")
        s_line, s_col = map(int, self._rect_start.split("."))
        e_line, e_col = map(int, end.split("."))
        min_line, max_line = min(s_line, e_line), max(s_line, e_line)
        min_col, max_col = min(s_col, e_col), max(s_col, e_col)
        self.rect_sel_ranges = []
        for line in range(min_line, max_line + 1):
            start = f"{line}.{min_col}"
            endi = f"{line}.{max_col}"
            self.entry.tag_add("rectsel", start, endi)
            self.rect_sel_ranges.append((start, endi))
        return "break"

    def _rect_sel_end(self, event):
        self.rect_select_active = True
        return "break"

    def _copy_selection(self, event=None):
        if self.rect_select_active and self.rect_sel_ranges:
            parts = []
            for start, end in self.rect_sel_ranges:
                parts.append(self.entry.get(start, end))
            text = "\n".join(parts)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            return "break"
        return None

    def _insert_block(self, role, text, tag):
        ts = datetime.now().strftime("%H:%M:%S")
        header = f"┌─ {role} {ts}\n"
        footer = "└────────────────────────\n"
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, header, ("block_header", tag))
        self.chat_log.insert(tk.END, text + "\n", (tag,))
        self.chat_log.insert(tk.END, footer + "\n", ("block_header", tag))
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def _start_ai_block(self):
        ts = datetime.now().strftime("%H:%M:%S")
        header = f"┌─ Shadow {ts}\n"
        footer = "└────────────────────────\n"
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, header, ("block_header", "block_ai"))
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.see(tk.END)
        self.active_ai_block = True
        self.active_ai_close = footer

    def _append_system_message(self, text):
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, text + "\n", "system")
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def _extract_docx_text(self, path):
        """Extract basic text from a .docx using the document XML."""
        try:
            with zipfile.ZipFile(path) as docx:
                with docx.open("word/document.xml") as xml_file:
                    root = ET.parse(xml_file).getroot()

            text_chunks = []
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    text_chunks.append(node.text)
                elif node.tag.endswith("}p"):
                    text_chunks.append("\n")

            text = "".join(text_chunks)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
        except Exception:
            return None

    def _describe_image_attachment(self, path):
        """Provide a lightweight local summary when no vision backend is active."""
        try:
            with Image.open(path) as img:
                width, height = img.size
                image_format = img.format or "unknown"

            size_kb = os.path.getsize(path) / 1024
            return (
                f"[Image attachment: {os.path.basename(path)}]\n"
                f"Format: {image_format}\n"
                f"Dimensions: {width}x{height}\n"
                f"Size: {size_kb:.1f} KB\n"
                "Note: Use a vision-capable model for full visual analysis."
            )
        except Exception:
            return f"[Image attachment: {os.path.basename(path)}]\n[Metadata unavailable]"

    def _encode_image_attachment(self, path):
        """Convert an image file to the base64 payload expected by vision backends."""
        try:
            with Image.open(path) as img:
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception:
            return None

    def _extract_attachment_text(self, path):
        """Read supported attachment types into prompt-friendly text."""
        ext = os.path.splitext(path)[1].lower()

        if ext in self.IMAGE_EXTENSIONS:
            return self._describe_image_attachment(path)

        if ext == ".docx":
            text = self._extract_docx_text(path)
            return text[:200000] if text else "[Unreadable .docx document]"

        if ext in self.TEXT_ATTACHMENT_EXTENSIONS:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(200000)
            except Exception:
                return "[Unreadable text file]"

        return f"[Binary attachment: {os.path.basename(path)}]"

    def _parse_attachments(self, text):
        files = []
        content_blocks = []
        cleaned = text
        for match in re.findall(r'@(\"[^\"]+\"|\\S+)', text):
            path = match.strip('"')
            path = os.path.expanduser(path)
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            if os.path.exists(path) and os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in self.IMAGE_EXTENSIONS:
                    image_payload = self._encode_image_attachment(path)
                    if image_payload:
                        files.append(image_payload)
                data = self._extract_attachment_text(path)
                content_blocks.append(f"[{os.path.basename(path)}]\\n{data}")
            cleaned = cleaned.replace(f"@{match}", "").strip()
        return cleaned, files, "\\n\\n".join(content_blocks)

    def send_text(self, event=None):
        msg = self._get_input_text()
        if not msg:
            return "break"

        self.command_history.append(msg)
        self.history_index = -1
        self._set_input_text("")

        clean_msg, attached_files, attached_text = self._parse_attachments(msg)
        if attached_files:
            self.append_chat(f"[Attached: {', '.join([os.path.basename(f) for f in attached_files])}]")

        # User block
        self._insert_block("You", clean_msg, "block_user")

        # Update status
        # Check if it's a shell command (starts with !)
        if clean_msg.startswith("!"):
            self.status_bar.config(text="Shadow is running command...")
            threading.Thread(target=self._execute_shell_command, args=(clean_msg[1:],), daemon=True).start()
        else:
            # Start streaming AI response
            self._start_ai_block()
            prompt = clean_msg
            has_attachment_context = bool(attached_text or attached_files)
            if attached_text:
                prompt += f"\\n\\n[ATTACHED FILES]\\n{attached_text}"
            task_recipe = detect_agent_recipe(clean_msg, has_attachments=has_attachment_context)
            self.status_bar.config(text=format_task_recipe_status(task_recipe, agent_mode=self.agent_mode.get()))
            recipe_notice = format_task_recipe_notice(task_recipe, agent_mode=self.agent_mode.get())
            if recipe_notice:
                self._append_system_message(recipe_notice)
            agent_override = self._get_agent_override() if self.agent_mode.get() else None
            threading.Thread(
                target=self._stream_ai_response,
                args=(prompt, agent_override, attached_files, task_recipe, self.agent_mode.get()),
                daemon=True
            ).start()

        # Start queue processor
        self.root.after(50, self._process_queue)
        return "break"

    def _configure_windows_app_id(self):
        if os.name != "nt":
            return

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.WINDOWS_APP_ID)
        except Exception:
            pass

    def _configure_window_icon(self):
        icon_path = os.path.join(get_resource_root(), "ShadowAI.ico")
        if not os.path.exists(icon_path):
            return

        try:
            self.root.iconbitmap(default=icon_path)
        except Exception:
            pass

        try:
            icon_image = Image.open(icon_path)
            self.window_icon = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(True, self.window_icon)
        except Exception:
            self.window_icon = None
    
    def _stream_ai_response(self, user_input, agent_override=None, files=None, task_recipe=None, agent_mode_enabled=False):
        """Stream AI response word by word for Warp-like feedback."""
        import sys
        import traceback
        
        try:
            restore_config = None
            if agent_override:
                restore_config = {k: self.core.config.get(k) for k in agent_override.keys()}
                for k, v in agent_override.items():
                    self.core.config.set(k, v)
            print(f"[DEBUG] Starting generation for: {user_input}", flush=True)
            reply = self.core.process(
                user_input,
                files=files,
                task_recipe=task_recipe,
                agent_mode=agent_mode_enabled
            )
            if reply and agent_mode_enabled:
                reply = format_agent_reply(reply)
                action_review = summarize_command_policies(reply)
                if action_review:
                    reply = f"{reply}\n\n{action_review}"
            elif reply and task_recipe:
                action_review = summarize_command_policies(reply)
                if action_review:
                    reply = f"{reply}\n\n{action_review}"
            print(f"[DEBUG] Got reply: {reply}", flush=True)
            
            # Stream response word by word
            if reply:
                words = reply.split()
                for word in words:
                    self.msg_queue.put(("ai", word + " "))
            else:
                self.msg_queue.put(("ai", "[No response]"))
                
        except Exception as e:
            print(f"[DEBUG] Exception: {str(e)}", flush=True)
            traceback.print_exc()
            self.msg_queue.put(("system", f"\n[Error: {str(e)}]"))
        finally:
            if agent_override and restore_config:
                for k, v in restore_config.items():
                    self.core.config.set(k, v)
            self.msg_queue.put(("done", None))
    
    def _execute_shell_command(self, command):
        """Execute shell command with live output streaming and safety gates."""
        # Deadman lock: hard block extreme commands
        if self._deadman_enabled() and self._deadman_blocked_command(command):
            msg = self.core.config.get("deadman_message", "ACCESS DENIED STOP WHILE YOU ARE AHEAD!")
            self.msg_queue.put(("system", f"❌ {msg}\n"))
            self.msg_queue.put(("done", None))
            return
        # Safety gate: Check for destructive commands
        risk = self._assess_command_risk(command)
        risk_level = risk["level"]
        self._announce_command_policy(command, risk)
        
        if risk_level == "critical":
            self.msg_queue.put(("system", f"❌ CRITICAL OPERATION BLOCKED: {command}\n"))
            self.msg_queue.put(("system", f"This command is extremely dangerous and has been blocked for safety ({risk['reason']}).\n"))
            self.msg_queue.put(("done", None))
            return
        elif risk.get("confirm"):
            # Show confirmation dialog in main thread
            self.root.after(0, lambda: self._confirm_risky_command(command, risk))
            return
        elif risk_level == "medium":
            self.msg_queue.put(("system", f"⚠️ Warning: Potentially risky command\n"))
        
        self.msg_queue.put(("terminal", f"🚀 Executing: {command}\n"))
        
        try:
            process = self._spawn_command_process(command)
            
            # Stream output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.msg_queue.put(("terminal", f"  [LOG] {line}"))
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code == 0:
                self.msg_queue.put(("terminal", "✅ SUCCESS: Operation completed.\n"))
            else:
                self.msg_queue.put(("terminal", f"❌ ERROR: Failed with code {return_code}\n"))
                
        except Exception as e:
            self.msg_queue.put(("system", f"[Error executing command: {str(e)}]\n"))
        finally:
            self.msg_queue.put(("done", None))
    
    def _assess_command_risk(self, command):
        """Assess risk level of shell command based on cognitive architecture."""
        return assess_command_risk(command)

    def _announce_command_policy(self, command, risk):
        """Emit a short command-policy summary into the chat log."""
        profile = risk.get("profile", "unknown")
        level = risk.get("level", "unknown")
        reason = risk.get("reason", "unknown")
        action = "blocked" if level == "critical" else ("confirm" if risk.get("confirm") else "run")
        self.msg_queue.put((
            "system",
            f"[Command Policy] profile={profile} level={level} action={action} reason={reason}\n"
        ))

    def _spawn_command_process(self, command, allow_shell_fallback=False):
        """Spawn subprocess with shell=False when possible."""
        plan = build_exec_plan(command)
        if plan["mode"] == "direct":
            return subprocess.Popen(
                plan["argv"],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

        if not allow_shell_fallback:
            raise ValueError("Shell metacharacters detected; confirmation required.")

        return subprocess.Popen(
            plan["command"],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    
    def _deadman_enabled(self):
        return bool(self.core.config.get("deadman_lock", True))
    
    def _deadman_blocked_command(self, command):
        """Block extreme destructive or world-hack shell commands."""
        cmd = command.lower()
        patterns = [
            r"rm\\s+-rf\\s+/",
            r"mkfs\\b",
            r"\\bformat\\b",
            r"dd\\s+if=/dev/zero",
            r"\\bwipefs\\b",
            r"\\bfsck\\b.*-y",
            r"\\bparted\\b|\\bfdisk\\b|\\bsgdisk\\b",
            r"\\blvremove\\b|\\bvgremove\\b|\\bpvremove\\b",
            r"\\bshutdown\\b|\\breboot\\b|\\bpoweroff\\b|\\bhalt\\b",
            r"systemctl\\s+(poweroff|reboot)",
            r"kill\\s+-9\\s+1",
            r":\\(\\)\\s*\\{\\s*:\\s*\\|\\s*:\\s*&\\s*\\}\\s*;\\s*:",
            r"\\bnmap\\b|\\bmasscan\\b|\\bmsfconsole\\b|\\bmsfvenom\\b",
            r"\\bhydra\\b|\\bsqlmap\\b|\\baircrack\\b|\\bettercap\\b|\\bbettercap\\b",
            r"\\bnetcat\\b\\s+.*\\s+-e\\b|\\bnc\\b\\s+.*\\s+-e\\b"
        ]
        return any(re.search(p, cmd) for p in patterns)
    
    def _confirm_risky_command(self, command, risk=None):
        """Show confirmation dialog for risky commands."""
        confirm_window = tk.Toplevel(self.root)
        confirm_window.title("⚠️ Risky Operation")
        confirm_window.geometry("500x200")
        confirm_window.configure(bg="#2a2a2a")
        
        tk.Label(confirm_window, 
                text="⚠️ WARNING: POTENTIALLY DESTRUCTIVE COMMAND",
                bg="#2a2a2a", fg="#ff4444", 
                font=("Arial", 12, "bold")).pack(pady=15)
        
        tk.Label(confirm_window, 
                text=f"Command: {command}",
                bg="#2a2a2a", fg="white", 
                font=("Courier New", 10)).pack(pady=5)
        
        risk_reason = risk["reason"] if risk else "may modify files or system state"
        risk_profile = risk["profile"] if risk else "mutating"
        tk.Label(confirm_window, 
                text=f"Profile: {risk_profile} | Reason: {risk_reason}",
                bg="#2a2a2a", fg="#ffaa00", 
                font=("Arial", 10), wraplength=460).pack(pady=5)
        
        button_frame = tk.Frame(confirm_window, bg="#2a2a2a")
        button_frame.pack(pady=20)
        
        def allow():
            confirm_window.destroy()
            # Execute the command
            self.msg_queue.put(("terminal", f"🚀 Executing (user confirmed): {command}\n"))
            threading.Thread(target=self._execute_command_unsafe, args=(command,), daemon=True).start()
            self.root.after(50, self._process_queue)
        
        def deny():
            confirm_window.destroy()
            self.msg_queue.put(("system", f"❌ Command cancelled by user: {command}\n"))
            self.msg_queue.put(("done", None))
        
        tk.Button(button_frame, text="❌ Deny", command=deny,
                 bg="#666666", fg="white", font=("Arial", 10, "bold"),
                 width=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="✅ Allow", command=allow,
                 bg="#ff4444", fg="white", font=("Arial", 10, "bold"),
                 width=10).pack(side=tk.LEFT, padx=10)
    
    def _execute_command_unsafe(self, command):
        """Execute command without safety checks (user already confirmed)."""
        if self._deadman_enabled() and self._deadman_blocked_command(command):
            msg = self.core.config.get("deadman_message", "ACCESS DENIED STOP WHILE YOU ARE AHEAD!")
            self.msg_queue.put(("system", f"❌ {msg}\n"))
            self.msg_queue.put(("done", None))
            return
        try:
            process = self._spawn_command_process(command, allow_shell_fallback=True)
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.msg_queue.put(("terminal", f"  [LOG] {line}"))
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code == 0:
                self.msg_queue.put(("terminal", "✅ SUCCESS: Operation completed.\n"))
            else:
                self.msg_queue.put(("terminal", f"❌ ERROR: Failed with code {return_code}\n"))
        except Exception as e:
            self.msg_queue.put(("system", f"[Error: {str(e)}]\n"))
        finally:
            self.msg_queue.put(("done", None))
    
    def _process_queue(self):
        """Process streaming messages from the queue."""
        try:
            while True:
                msg_type, content = self.msg_queue.get_nowait()
                
                if msg_type == "done":
                    if self.active_ai_block and self.active_ai_close:
                        self.chat_log.config(state=tk.NORMAL)
                        self.chat_log.insert(tk.END, self.active_ai_close + "\n", ("block_header", "block_ai"))
                        self.chat_log.config(state=tk.DISABLED)
                        self.active_ai_block = False
                        self.active_ai_close = None
                    self.status_bar.config(text="Ready")
                    return
                
                # Insert content with appropriate styling
                self.chat_log.config(state=tk.NORMAL)
                if msg_type == "terminal":
                    self.chat_log.insert(tk.END, content, "terminal")
                elif msg_type == "system":
                    self.chat_log.insert(tk.END, content, "system")
                else:  # ai
                    if self.active_ai_block:
                        self.chat_log.insert(tk.END, content, "block_ai")
                    else:
                        self.chat_log.insert(tk.END, content, "ai")
                
                self.chat_log.see(tk.END)
                self.chat_log.config(state=tk.DISABLED)
                
        except queue.Empty:
            # Queue is empty, check again in 50ms
            self.root.after(50, self._process_queue)

    def send_file(self):
        from tkinter import messagebox
        files = filedialog.askopenfilenames(
            title="Select files to analyze",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("Videos", "*.mp4 *.avi *.mov *.mkv"),
                ("Audio", "*.mp3 *.wav *.ogg *.m4a"),
                ("Documents", "*.txt *.pdf *.doc *.docx"),
                ("Code", "*.py *.js *.java *.cpp *.c *.go *.rs"),
                ("All files", "*.*")
            ]
        )
        
        if files:
            # Check if any text files - offer batch learning
            text_extensions = ['txt', 'md', 'log', 'text', 'csv', 'json', 'xml', 'yaml', 'yml', 
                             'ini', 'conf', 'cfg', 'toml', 'sh', 'bash', 'py', 'js', 'ts', 
                             'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'go', 'rs', 'rb', 'php', 
                             'html', 'css', 'jsx', 'tsx', 'vue', 'sql', 'r', 'pl', 'lua', 
                             'swift', 'kt', 'dart', 'scala', 'ex', 'exs', 'clj', 'hs', 'ml', 
                             'tex', 'rst', 'adoc', 'org', 'rtf']
            text_files = [f for f in files if f.split('.')[-1].lower() in text_extensions]
            
            if text_files:
                result = messagebox.askyesnocancel(
                    "Batch Learning",
                    f"Found {len(text_files)} text file(s).\n\nYes = Learn from them\nNo = Analyze normally\nCancel = Cancel"
                )
                
                if result is None:  # Cancel
                    return
                elif result:  # Yes - learn
                    for file_path in text_files:
                        self.append_chat(f"[Learning from: {os.path.basename(file_path)}]")
                        stats = self.core.process_file_learning(file_path)
                        self.append_chat(f"Shadow: {stats}")
                    return
            
            # Normal analysis
            for file_path in files:
                self.last_file_path = file_path
                self.update_preview(file_path)
                self.append_chat(f"[Uploaded: {os.path.basename(file_path)}]")
                
                # Analyze file immediately in thread
                threading.Thread(target=self._analyze_file, args=(file_path,), daemon=True).start()

    def _analyze_file(self, file_path):
        # Determine file type and create appropriate prompt
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                img_str = self._encode_image_attachment(file_path)
                prompt = "Describe this image in detail. What do you see?"
                if img_str:
                    reply = self.core.llm.generate(prompt, images=[img_str])
                    if isinstance(reply, str) and "error" in reply.lower():
                        reply = self._describe_image_attachment(file_path)
                else:
                    reply = self._describe_image_attachment(file_path)
                
            elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                prompt = f"Analyze this video file: {os.path.basename(file_path)}"
                reply = self.core.process(prompt)
                
            elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                prompt = f"This is an audio file: {os.path.basename(file_path)}. Transcribe or analyze it."
                reply = self.core.process(prompt)
                
            else:
                # Text-based files
                try:
                    content = self._extract_attachment_text(file_path)
                    if not content or content.startswith("[Binary attachment:"):
                        raise ValueError("Unsupported file type")
                    content = content[:5000]
                    prompt = f"Analyze this file ({os.path.basename(file_path)}):\n\n{content}"
                    reply = self.core.process(prompt)
                except:
                    reply = "Could not read file."
            
            if reply:
                self.append_chat(f"Shadow: {reply}\n")
            else:
                self.append_chat(f"Shadow: [No response from model]\n")
                
        except Exception as e:
            self.append_chat(f"[Error analyzing file: {str(e)}]\n")

    def clone_repo(self):
        # Simple dialog for Git URL
        repo_window = tk.Toplevel(self.root)
        repo_window.title("Clone Repository")
        repo_window.geometry("500x150")
        repo_window.configure(bg="#2a2a2a")
        
        tk.Label(repo_window, text="Enter Git repository URL:", 
                bg="#2a2a2a", fg="white", font=("Arial", 11)).pack(pady=10)
        
        url_entry = tk.Entry(repo_window, width=60, font=("Arial", 10))
        url_entry.pack(pady=5, padx=20)
        
        def do_clone():
            url = url_entry.get().strip()
            if url:
                repo_window.destroy()
                self.append_chat(f"[Cloning: {url}]")
                threading.Thread(target=self._clone_and_analyze, args=(url,), daemon=True).start()
        
        tk.Button(repo_window, text="Clone & Analyze", command=do_clone,
                 bg="#0066cc", fg="white", font=("Arial", 10, "bold")).pack(pady=10)

    def _clone_and_analyze(self, url):
        try:
            repo_name = url.split('/')[-1].replace('.git', '')
            clone_path = os.path.join(os.path.expanduser('~'), 'shadow_repos', repo_name)
            os.makedirs(os.path.dirname(clone_path), exist_ok=True)
            
            # Clone repo
            result = subprocess.run(['git', 'clone', url, clone_path], 
                                   capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                self.append_chat(f"[Cloned to: {clone_path}]")
                
                # Generate file tree
                tree = self._generate_tree(clone_path)
                self.update_preview_text(f"Repository: {repo_name}\n\n{tree}")
                
                # Analyze repo structure
                prompt = f"Analyze this repository structure:\n\n{tree}"
                reply = self.core.process(prompt)
                self.append_chat(f"Shadow: {reply}\n")
            else:
                self.append_chat(f"[Error cloning: {result.stderr}]")
        except Exception as e:
            self.append_chat(f"[Error: {str(e)}]")

    def _generate_tree(self, path, prefix="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return ""
        
        tree = ""
        try:
            items = sorted(os.listdir(path))
            items = [i for i in items if not i.startswith('.')]
            
            for i, item in enumerate(items[:20]):  # Limit to 20 items
                item_path = os.path.join(path, item)
                is_last = i == len(items) - 1
                
                tree += prefix + ("└── " if is_last else "├── ") + item + "\n"
                
                if os.path.isdir(item_path) and current_depth < max_depth - 1:
                    extension = "    " if is_last else "│   "
                    tree += self._generate_tree(item_path, prefix + extension, 
                                               max_depth, current_depth + 1)
        except:
            pass

    def _detect_gpus(self):
        """Detect all GPUs (NVIDIA + AMD/Intel via sysfs)."""
        gpus = []
        # NVIDIA GPUs via NVML
        if self.nvml_available:
            try:
                count = pynvml.nvmlDeviceGetCount()
                for i in range(count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode("utf-8", errors="ignore")
                    gpus.append({"name": name, "type": "nvidia", "index": i})
            except:
                pass
        
        # AMD/Intel GPUs via sysfs
        for card in sorted(glob.glob("/sys/class/drm/card[0-9]*")):
            vendor_path = os.path.join(card, "device", "vendor")
            if not os.path.exists(vendor_path):
                continue
            try:
                with open(vendor_path, "r") as f:
                    vendor = f.read().strip().lower()
            except:
                continue
            if vendor == "0x10de":
                # NVIDIA already handled
                continue
            if vendor == "0x1002":
                name = f"AMD GPU ({os.path.basename(card)})"
            elif vendor == "0x8086":
                name = f"Intel GPU ({os.path.basename(card)})"
            else:
                name = f"GPU {vendor} ({os.path.basename(card)})"
            gpus.append({"name": name, "type": "sysfs", "card": card})
        
        if not gpus:
            gpus = [{"name": "GPU", "type": "none"}]
        return gpus

    def _read_gpu_busy(self, card_path):
        """Read GPU utilization from sysfs if available."""
        candidates = [
            os.path.join(card_path, "device", "gpu_busy_percent"),
            os.path.join(card_path, "device", "gt_busy_percent"),
            os.path.join(card_path, "device", "amd_gpu_busy_percent"),
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        return float(f.read().strip())
                except:
                    continue
        return 0.0
        
        return tree

    def update_preview(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            # Show image thumbnail
            self.update_preview_text(f"Image: {os.path.basename(file_path)}")
        
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            self.update_preview_text(f"🎬 Video: {os.path.basename(file_path)}")
        
        elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
            self.update_preview_text(f"🎵 Audio: {os.path.basename(file_path)}")
        
        else:
            # Show file info
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB"
            self.update_preview_text(f"📄 File: {os.path.basename(file_path)} ({size_str})")

    def update_preview_text(self, text):
        if self.preview_info:
            self.preview_info.config(text=text)

    def _update_system_stats(self):
        """Update system monitoring stats in real-time."""
        while self.monitoring_active:
            try:
                # Get CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                # Get RAM usage
                ram = psutil.virtual_memory()
                ram_percent = ram.percent
                # Get disk usage
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                # Get GPU usage for all GPUs
                gpu_percents = []
                for gpu in self.gpus:
                    if gpu["type"] == "nvidia" and self.nvml_available:
                        try:
                            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu["index"])
                            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                            gpu_percents.append(util.gpu)
                        except:
                            gpu_percents.append(0)
                    elif gpu["type"] == "sysfs":
                        gpu_percents.append(self._read_gpu_busy(gpu["card"]))
                    else:
                        gpu_percents.append(0)
                
                # Update canvases in main thread
                self.root.after(0, self._draw_stat_bars, cpu_percent, ram_percent, disk_percent, gpu_percents)
                threading.Event().wait(1)  # Update every 1 second
            except:
                break
    
    def _draw_stat_bars(self, cpu, ram, disk, gpus):
        """Draw system stat bars on canvases."""
        try:
            # CPU bar
            self.cpu_canvas.delete("all")
            bar_width = max(self.cpu_canvas.winfo_width(), 200)
            cpu_x = int(cpu * bar_width / 100)
            self.cpu_canvas.create_rectangle(0, 0, cpu_x, 20, fill="#4CAF50", outline="#333333")
            self.cpu_canvas.create_text(bar_width + 10, 10, text=f"{cpu:.1f}%", 
                                       fill="#333333", font=("Arial", 9), anchor=tk.W)
            
            # RAM bar
            self.ram_canvas.delete("all")
            ram_x = int(ram * bar_width / 100)
            self.ram_canvas.create_rectangle(0, 0, ram_x, 20, fill="#2196F3", outline="#333333")
            self.ram_canvas.create_text(bar_width + 10, 10, text=f"{ram:.1f}%", 
                                       fill="#333333", font=("Arial", 9), anchor=tk.W)
            
            # Disk bar
            self.disk_canvas.delete("all")
            disk_x = int(disk * bar_width / 100)
            self.disk_canvas.create_rectangle(0, 0, disk_x, 20, fill="#FF9800", outline="#333333")
            self.disk_canvas.create_text(bar_width + 10, 10, text=f"{disk:.1f}%", 
                                        fill="#333333", font=("Arial", 9), anchor=tk.W)
            
            # GPU bars (all GPUs)
            for i, canvas in enumerate(self.gpu_bars):
                canvas.delete("all")
                gpu_val = gpus[i] if i < len(gpus) else 0
                gpu_x = int(gpu_val * bar_width / 100)
                canvas.create_rectangle(0, 0, gpu_x, 20, fill="#9C27B0", outline="#333333")
                canvas.create_text(bar_width + 10, 10, text=f"{gpu_val:.1f}%", 
                                  fill="#333333", font=("Arial", 9), anchor=tk.W)
        except:
            pass

    def append_chat(self, msg):
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, msg + "\n")
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def run(self):
        self.root.mainloop()
        self.monitoring_active = False
        self.memory.save()
