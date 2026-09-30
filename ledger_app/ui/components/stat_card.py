import customtkinter as ctk
from ledger_app.ui.theme import Theme

class StatCard(ctk.CTkFrame):
    """Reusable card component to display business KPI stats (Total Credit, Debit, etc.)."""
    def __init__(self, parent, title: str, value: str, color: tuple = Theme.TEXT_PRIMARY, icon_char: str = ""):
        super().__init__(
            parent, 
            fg_color=Theme.BG_SECONDARY, 
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH,
            border_color=Theme.BORDER_COLOR
        )
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1), weight=1)
        
        # Inner padding frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Label/Title
        self.title_label = ctk.CTkLabel(
            self.content_frame, 
            text=title.upper(), 
            font=Theme.FONT_CAPTION, 
            text_color=Theme.TEXT_SECONDARY,
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        # Value Frame (to align value and optional icon)
        self.value_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.value_frame.grid(row=1, column=0, sticky="ew")
        self.value_frame.grid_columnconfigure(0, weight=1)
        
        self.value_label = ctk.CTkLabel(
            self.value_frame, 
            text=value, 
            font=Theme.FONT_STAT, 
            text_color=color,
            anchor="w"
        )
        self.value_label.grid(row=0, column=0, sticky="w")
        
        if icon_char:
            self.icon_label = ctk.CTkLabel(
                self.value_frame, 
                text=icon_char, 
                font=(Theme.FONT_FAMILY, 26, "normal"), 
                text_color=Theme.TEXT_SECONDARY,
                anchor="e"
            )
            self.icon_label.grid(row=0, column=1, sticky="e")
            
    def update_value(self, new_value: str, color: tuple = None):
        """Dynamically updates the displayed value."""
        self.value_label.configure(text=new_value)
        if color:
            self.value_label.configure(text_color=color)
