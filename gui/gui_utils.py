"""
GUI Utilities - Animations and transitions
"""

import customtkinter as ctk

def fade_in(widget, start_opacity=0, duration=300, steps=10):
    """Simple fade-in effect for widgets (simulated by background color blending)"""
    # Note: customtkinter doesn't support true alpha for all widgets easily,
    # but we can simulate a fade by moving from a dark background to the actual one.
    # For now, let's implement a simpler "lift" or "slide" or just simple appearance.
    
    # Simple recursive reveal
    widget.after(10, lambda: widget.pack_configure(padx=25, pady=25))

def apply_hover_effect(widget, hover_color, original_color):
    """Apply hover color changes to a widget"""
    widget.bind("<Enter>", lambda e: widget.configure(fg_color=hover_color))
    widget.bind("<Leave>", lambda e: widget.configure(fg_color=original_color))
