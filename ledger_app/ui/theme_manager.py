import os
import json
import customtkinter as ctk

class Theme:
    # Color Palette (Dark & Light Mode responsive colors)
    # Format: (Light Mode Hex, Dark Mode Hex)
    BG_PRIMARY = ("#F8FAFC", "#0B1220")       # App base background
    BG_SIDEBAR = ("#FFFFFF", "#111827")       # Sidebar background
    BG_SECONDARY = ("#FFFFFF", "#1E293B")     # Card / dialog background
    BG_TERTIARY = ("#F1F5F9", "#0F172A")      # Table headers / Input boxes / hover backgrounds
    
    ACCENT = ("#0EA5E9", "#14B8A6")           # Primary Accent
    ACCENT_HOVER = ("#0284C7", "#0D9488")     # Accent hover color
    
    # Text Colors
    TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
    TEXT_SECONDARY = ("#64748B", "#94A3B8")
    TEXT_WHITE = "#FFFFFF"
    
    # Financial indicators
    DEBIT_RED = ("#EF4444", "#EF4444")        # Customer owes us money (Danger/Debit)
    CREDIT_GREEN = ("#22C55E", "#22C55E")     # Customer paid / credit balance (Success/Credit)
    NEUTRAL_BLUE = ("#0EA5E9", "#14B8A6")     # Secondary Accent
    WARNING_ORANGE = ("#F59E0B", "#F59E0B")   # Warning Accent
    
    # Special button states / danger alerts
    DANGER_HOVER = ("#FADBD8", "#78281F")
    
    # Layout Sizing
    CORNER_RADIUS = 10
    BORDER_WIDTH = 1
    BORDER_COLOR = ("#E2E8F0", "#334155")
    
    # Fonts
    FONT_FAMILY = "Segoe UI"
    
    FONT_TITLE = (FONT_FAMILY, 24, "bold")
    FONT_SUBTITLE = (FONT_FAMILY, 16, "bold")
    FONT_HEADER = (FONT_FAMILY, 13, "bold")
    FONT_BODY = (FONT_FAMILY, 12, "normal")
    FONT_BODY_BOLD = (FONT_FAMILY, 12, "bold")
    FONT_CAPTION = (FONT_FAMILY, 10, "normal")
    
    # Large Stat numbers
    FONT_STAT = (FONT_FAMILY, 28, "bold")


class ThemeManager:
    _listeners = []
    _current_theme = "dark"  # Default theme
    
    @classmethod
    def register_listener(cls, listener):
        if listener not in cls._listeners:
            cls._listeners.append(listener)
            
    @classmethod
    def unregister_listener(cls, listener):
        if listener in cls._listeners:
            cls._listeners.remove(listener)
            
    @classmethod
    def get_color(cls, color_val) -> str:
        if isinstance(color_val, tuple):
            return color_val[0] if cls._current_theme == "light" else color_val[1]
        return color_val

    @classmethod
    def get_current_theme(cls) -> str:
        return cls._current_theme
        
    @classmethod
    def set_theme(cls, theme_name: str):
        if theme_name not in ("light", "dark"):
            raise ValueError("Theme must be 'light' or 'dark'")
        cls._current_theme = theme_name
        cls.save_theme()
        cls.apply_theme()
        # Notify observers/listeners of theme change
        for listener in list(cls._listeners):
            try:
                listener(theme_name)
            except Exception as e:
                print(f"Error notifying theme listener: {e}")
                
    @classmethod
    def load_theme(cls) -> str:
        if os.path.exists("settings.json"):
            try:
                with open("settings.json", "r") as f:
                    data = json.load(f)
                    cls._current_theme = data.get("theme", "dark")
            except Exception as e:
                print(f"Error loading theme: {e}")
                cls._current_theme = "dark"
        return cls._current_theme
        
    @classmethod
    def save_theme(cls):
        data = {}
        if os.path.exists("settings.json"):
            try:
                with open("settings.json", "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        data["theme"] = cls._current_theme
        try:
            with open("settings.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving theme: {e}")
            
    @classmethod
    def apply_theme(cls):
        ctk.set_appearance_mode(cls._current_theme)
