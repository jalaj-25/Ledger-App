import customtkinter as ctk
from ledger_app.ui.theme import Theme

class DataTable(ctk.CTkFrame):
    """
    Reusable grid/table component using CTkScrollableFrame.
    Handles zebra striping, custom column widths, and responsive grid layouts.
    """
    def __init__(self, parent, headers: list, col_weights: list = None):
        super().__init__(parent, fg_color="transparent")
        self.headers = headers
        self.num_cols = len(headers)
        self.col_weights = col_weights or [1] * self.num_cols
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. Table Header Row Frame
        self.header_frame = ctk.CTkFrame(
            self, 
            fg_color=Theme.BG_TERTIARY, 
            corner_radius=0, 
            height=35
        )
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        # Configure columns inside header
        for c in range(self.num_cols):
            self.header_frame.grid_columnconfigure(c, weight=self.col_weights[c])
            lbl = ctk.CTkLabel(
                self.header_frame, 
                text=headers[c].upper(), 
                font=Theme.FONT_HEADER, 
                text_color=Theme.TEXT_PRIMARY,
                pady=8
            )
            lbl.grid(row=0, column=c, sticky="nsew", padx=10)
            
        # 2. Scrollable Data Frame for rows
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent", 
            corner_radius=0
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        
        # Configure columns inside scroll frame
        for c in range(self.num_cols):
            self.scroll_frame.grid_columnconfigure(c, weight=self.col_weights[c])
            
        self.rows_list = []

    def clear(self):
        """Clears all rows from the table."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.rows_list = []

    def set_data(self, data_rows: list):
        """
        Populates the table with data rows.
        data_rows should be a list of lists/tuples representing cells.
        Each cell value can be a string, or a dict with formatting configurations
        like {'text': '...', 'color': '#HexColor'}.
        """
        self.clear()
        
        for r_idx, row_val in enumerate(data_rows):
            # Row container to structure line margins and zebra striping
            bg_color = Theme.BG_SECONDARY if r_idx % 2 == 0 else Theme.BG_PRIMARY
            
            for c_idx in range(self.num_cols):
                cell_data = row_val[c_idx] if c_idx < len(row_val) else ""
                
                # Check custom cell formats
                cell_text = ""
                cell_color = Theme.TEXT_PRIMARY
                
                if isinstance(cell_data, dict):
                    cell_text = cell_data.get('text', '')
                    cell_color = cell_data.get('color', Theme.TEXT_PRIMARY)
                else:
                    cell_text = str(cell_data)
                
                # Create parent widget cell background wrapper
                cell_bg = ctk.CTkFrame(
                    self.scroll_frame, 
                    fg_color=bg_color, 
                    corner_radius=0, 
                    border_width=0
                )
                cell_bg.grid(row=r_idx, column=c_idx, sticky="nsew", ipady=6)
                cell_bg.grid_columnconfigure(0, weight=1)
                
                lbl = ctk.CTkLabel(
                    cell_bg, 
                    text=cell_text, 
                    font=Theme.FONT_BODY, 
                    text_color=cell_color
                )
                lbl.grid(row=0, column=0, padx=10, pady=4)
                
            self.rows_list.append(row_val)
            
        # If no records exist, show empty message
        if not data_rows:
            empty_bg = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            empty_bg.grid(row=0, column=0, columnspan=self.num_cols, pady=40, sticky="nsew")
            empty_bg.grid_columnconfigure(0, weight=1)
            
            empty_lbl = ctk.CTkLabel(
                empty_bg, 
                text="No records found.", 
                font=Theme.FONT_BODY, 
                text_color=Theme.TEXT_SECONDARY
            )
            empty_lbl.grid(row=0, column=0)
