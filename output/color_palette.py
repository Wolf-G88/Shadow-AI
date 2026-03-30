"""
Color Palette Module for Shadow AI
Classic paint-program grid layout with primary colors, extended grid, and custom selection.
"""

import tkinter as tk
from tkinter import colorchooser
from typing import Callable, Optional


class ColorPalette(tk.Toplevel):
    """
    Color palette widget with paint-program style grid layout.
    Includes primary colors, extended palette, and custom color picker.
    """
    
    # Theme presets
    THEMES = {
        "Dark Themes": [
            ("#1a1a1a", "Pure Black"),
            ("#2b2b2b", "Charcoal"),
            ("#1e1e2e", "Midnight"),
            ("#0d1117", "GitHub Dark"),
        ],
        "Light Themes": [
            ("#ffffff", "Pure White"),
            ("#f5f5f5", "Off White"),
            ("#e8e8e8", "Light Gray"),
            ("#fafafa", "Snow"),
        ],
        "Terminal Colors": [
            ("#00ff41", "Matrix Green"),
            ("#0066cc", "Link Blue"),
            ("#ff6b35", "Warning Orange"),
            ("#ffaa00", "Alert Yellow"),
        ],
        "Accent Colors": [
            ("#bb86fc", "Purple Accent"),
            ("#03dac6", "Teal Accent"),
            ("#cf6679", "Rose Accent"),
            ("#018786", "Dark Teal"),
        ]
    }
    
    # Primary colors (top row)
    PRIMARY_COLORS = [
        "#FF0000",  # Red
        "#FF7F00",  # Orange
        "#FFFF00",  # Yellow
        "#00FF00",  # Green
        "#0000FF",  # Blue
        "#8B00FF",  # Purple
        "#000000",  # Black
        "#FFFFFF",  # White
    ]
    
    # Recent colors storage
    recent_colors = []
    
    # Extended color grid (web-safe 216 colors)
    @staticmethod
    def _generate_extended_colors():
        """Generate 216-color web-safe palette."""
        colors = []
        values = [0x00, 0x33, 0x66, 0x99, 0xCC, 0xFF]
        
        for r in values:
            for g in values:
                for b in values:
                    color = f"#{r:02X}{g:02X}{b:02X}"
                    colors.append(color)
        
        return colors
    
    def __init__(
        self, 
        parent, 
        callback: Optional[Callable[[str], None]] = None,
        current_color: str = "#FFFFFF"
    ):
        """
        Initialize color palette.
        
        Args:
            parent: Parent widget
            callback: Function to call when color is selected (receives color hex string)
            current_color: Currently selected color
        """
        super().__init__(parent)
        
        self.callback = callback
        self.current_color = current_color
        self.selected_color = current_color
        
        self.title("Shadow AI - Color Palette")
        self.geometry("500x600")
        self.resizable(False, False)
        self.configure(bg="#2b2b2b")
        
        # Make window stay on top
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create palette widgets."""
        main_frame = tk.Frame(self, bg="#2b2b2b", padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Select Color",
            font=("Arial", 14, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        title_label.pack(pady=(0, 10))
        
        # Current color display
        self._create_current_color_display(main_frame)
        
        # Theme presets
        self._create_theme_presets(main_frame)
        
        # Recent colors
        if ColorPalette.recent_colors:
            self._create_recent_colors(main_frame)
        
        # Primary colors row
        self._create_primary_colors(main_frame)
        
        # Extended color grid
        self._create_extended_grid(main_frame)
        
        # Custom color picker button
        self._create_custom_picker(main_frame)
        
        # Action buttons
        self._create_action_buttons(main_frame)
    
    def _create_current_color_display(self, parent):
        """Create current color display."""
        frame = tk.Frame(parent, bg="#2b2b2b")
        frame.pack(pady=(0, 10))
        
        tk.Label(
            frame,
            text="Current:",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="#888888"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.current_color_canvas = tk.Canvas(
            frame,
            width=60,
            height=30,
            bg=self.current_color,
            highlightthickness=2,
            highlightbackground="#555555"
        )
        self.current_color_canvas.pack(side=tk.LEFT)
        
        self.color_label = tk.Label(
            frame,
            text=self.current_color,
            font=("Courier", 10),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        self.color_label.pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_theme_presets(self, parent):
        """Create theme preset buttons."""
        frame = tk.Frame(parent, bg="#2b2b2b")
        frame.pack(pady=(0, 10), fill=tk.X)
        
        tk.Label(
            frame,
            text="Theme Presets",
            font=("Arial", 10, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        ).pack(anchor=tk.W)
        
        for theme_name, colors in self.THEMES.items():
            theme_frame = tk.Frame(frame, bg="#2b2b2b")
            theme_frame.pack(anchor=tk.W, pady=2)
            
            tk.Label(
                theme_frame,
                text=f"{theme_name}:",
                font=("Arial", 9),
                bg="#2b2b2b",
                fg="#888888",
                width=15,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            
            colors_frame = tk.Frame(theme_frame, bg="#2b2b2b")
            colors_frame.pack(side=tk.LEFT)
            
            for color, name in colors:
                self._create_labeled_color_button(colors_frame, color, name)
    
    def _create_labeled_color_button(self, parent, color: str, label: str):
        """Create color button with tooltip label."""
        btn = tk.Button(
            parent,
            bg=color,
            width=3,
            height=1,
            relief=tk.RAISED,
            borderwidth=1,
            command=lambda: self._select_color(color),
            cursor="hand2"
        )
        btn.pack(side=tk.LEFT, padx=2)
        
        # Create tooltip
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label_widget = tk.Label(
                tooltip,
                text=f"{label}\n{color}",
                bg="#1a1a1a",
                fg="#ffffff",
                font=("Arial", 8),
                padx=5,
                pady=3
            )
            label_widget.pack()
            btn.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(btn, 'tooltip'):
                btn.tooltip.destroy()
        
        btn.bind("<Enter>", show_tooltip)
        btn.bind("<Leave>", hide_tooltip)
    
    def _create_recent_colors(self, parent):
        """Create recent colors row."""
        frame = tk.Frame(parent, bg="#2b2b2b")
        frame.pack(pady=(0, 10))
        
        tk.Label(
            frame,
            text="Recent Colors",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="#888888"
        ).pack()
        
        color_frame = tk.Frame(frame, bg="#2b2b2b")
        color_frame.pack()
        
        for color in ColorPalette.recent_colors[-8:]:  # Last 8 colors
            self._create_color_button(color_frame, color, size=25)
    
    def _create_primary_colors(self, parent):
        """Create primary colors row."""
        frame = tk.Frame(parent, bg="#2b2b2b")
        frame.pack(pady=(0, 10))
        
        tk.Label(
            frame,
            text="Primary Colors",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="#888888"
        ).pack()
        
        color_frame = tk.Frame(frame, bg="#2b2b2b")
        color_frame.pack()
        
        for color in self.PRIMARY_COLORS:
            self._create_color_button(color_frame, color, size=35)
    
    def _create_extended_grid(self, parent):
        """Create extended color grid."""
        frame = tk.Frame(parent, bg="#2b2b2b")
        frame.pack(pady=(0, 10))
        
        tk.Label(
            frame,
            text="Extended Colors",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="#888888"
        ).pack()
        
        # Create scrollable canvas for grid
        canvas_frame = tk.Frame(frame, bg="#2b2b2b")
        canvas_frame.pack()
        
        canvas = tk.Canvas(
            canvas_frame,
            width=380,
            height=200,
            bg="#1a1a1a",
            highlightthickness=1,
            highlightbackground="#555555"
        )
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        grid_frame = tk.Frame(canvas, bg="#1a1a1a")
        
        canvas.create_window((0, 0), window=grid_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        # Generate and display colors in grid (18 colors per row)
        extended_colors = self._generate_extended_colors()
        colors_per_row = 18
        
        for i, color in enumerate(extended_colors):
            row = i // colors_per_row
            col = i % colors_per_row
            
            btn = tk.Button(
                grid_frame,
                bg=color,
                width=2,
                height=1,
                relief=tk.RAISED,
                borderwidth=1,
                command=lambda c=color: self._select_color(c)
            )
            btn.grid(row=row, column=col, padx=1, pady=1)
        
        grid_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def _create_custom_picker(self, parent):
        """Create custom color picker button."""
        btn = tk.Button(
            parent,
            text="Custom Color...",
            font=("Arial", 10),
            bg="#444444",
            fg="#ffffff",
            activebackground="#555555",
            activeforeground="#ffffff",
            relief=tk.RAISED,
            borderwidth=2,
            command=self._open_custom_picker,
            cursor="hand2"
        )
        btn.pack(pady=(0, 10))
    
    def _create_action_buttons(self, parent):
        """Create OK/Cancel buttons."""
        frame = tk.Frame(parent, bg="#2b2b2b")
        frame.pack()
        
        ok_btn = tk.Button(
            frame,
            text="OK",
            font=("Arial", 10, "bold"),
            bg="#00aa00",
            fg="#ffffff",
            activebackground="#00cc00",
            activeforeground="#ffffff",
            width=10,
            relief=tk.RAISED,
            borderwidth=2,
            command=self._on_ok,
            cursor="hand2"
        )
        ok_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(
            frame,
            text="Cancel",
            font=("Arial", 10),
            bg="#aa0000",
            fg="#ffffff",
            activebackground="#cc0000",
            activeforeground="#ffffff",
            width=10,
            relief=tk.RAISED,
            borderwidth=2,
            command=self._on_cancel,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def _create_color_button(self, parent, color: str, size: int = 25):
        """Create individual color button."""
        btn = tk.Button(
            parent,
            bg=color,
            width=size // 8,
            height=size // 16,
            relief=tk.RAISED,
            borderwidth=2,
            command=lambda: self._select_color(color)
        )
        btn.pack(side=tk.LEFT, padx=2, pady=2)
    
    def _select_color(self, color: str):
        """Handle color selection."""
        self.selected_color = color
        self.current_color_canvas.configure(bg=color)
        self.color_label.configure(text=color)
    
    def _open_custom_picker(self):
        """Open system color picker."""
        color = colorchooser.askcolor(
            initialcolor=self.selected_color,
            title="Choose Custom Color",
            parent=self
        )
        
        if color and color[1]:  # color[1] is hex string
            self._select_color(color[1])
    
    def _on_ok(self):
        """Handle OK button."""
        # Add to recent colors
        if self.selected_color not in ColorPalette.recent_colors:
            ColorPalette.recent_colors.append(self.selected_color)
            if len(ColorPalette.recent_colors) > 16:  # Keep max 16
                ColorPalette.recent_colors.pop(0)
        
        if self.callback:
            self.callback(self.selected_color)
        self.destroy()
    
    def _on_cancel(self):
        """Handle Cancel button."""
        self.destroy()
    
    @staticmethod
    def show_palette(
        parent, 
        callback: Optional[Callable[[str], None]] = None,
        current_color: str = "#FFFFFF"
    ) -> str:
        """
        Convenience method to show color palette.
        
        Args:
            parent: Parent widget
            callback: Function to call when color is selected
            current_color: Currently selected color
        
        Returns:
            Selected color hex string
        """
        palette = ColorPalette(parent, callback, current_color)
        parent.wait_window(palette)
        return palette.selected_color


# Quick test function
def test_color_palette():
    """Test the color palette widget."""
    root = tk.Tk()
    root.title("Color Palette Test")
    root.geometry("300x200")
    
    selected_color = tk.StringVar(value="#FFFFFF")
    
    def on_color_selected(color):
        selected_color.set(color)
        display_label.configure(bg=color, text=color)
    
    display_label = tk.Label(
        root,
        text=selected_color.get(),
        font=("Arial", 14),
        bg=selected_color.get(),
        width=20,
        height=5
    )
    display_label.pack(pady=20)
    
    open_btn = tk.Button(
        root,
        text="Open Color Palette",
        command=lambda: ColorPalette.show_palette(root, on_color_selected, selected_color.get())
    )
    open_btn.pack()
    
    root.mainloop()


if __name__ == "__main__":
    test_color_palette()
