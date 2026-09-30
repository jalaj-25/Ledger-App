import customtkinter as ctk
# pyrefly: ignore [missing-import]
import matplotlib
# pyrefly: ignore [missing-import]
matplotlib.use("TkAgg")
# pyrefly: ignore [missing-import]
from matplotlib.figure import Figure
# pyrefly: ignore [missing-import]
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ledger_app.ui.theme import Theme
from ledger_app.ui.theme_manager import ThemeManager
from typing import List, Dict, Any

class ThemedChartCanvas:
    """Helper to configure Matplotlib figures with dynamic theme aesthetics."""
    
    @staticmethod
    def get_color(color_val):
        return ThemeManager.get_color(color_val)
    
    @staticmethod
    def create_figure(width: float, height: float) -> Figure:
        bg_color = ThemedChartCanvas.get_color(Theme.BG_SECONDARY)
        fig = Figure(figsize=(width, height), dpi=100, facecolor=bg_color)
        return fig

    @staticmethod
    def style_axes(ax, title: str):
        bg_color = ThemedChartCanvas.get_color(Theme.BG_SECONDARY)
        text_color = ThemedChartCanvas.get_color(Theme.TEXT_PRIMARY)
        sec_text = ThemedChartCanvas.get_color(Theme.TEXT_SECONDARY)
        border_color = ThemedChartCanvas.get_color(Theme.BORDER_COLOR)

        ax.set_facecolor(bg_color)
        ax.set_title(title, color=text_color, fontsize=12, fontweight='bold', pad=10)
        
        # Grid settings
        ax.grid(True, color=border_color, linestyle='--', alpha=0.5)
        
        # Tick and label styling
        ax.tick_params(colors=sec_text, labelsize=9)
        ax.xaxis.label.set_color(sec_text)
        ax.yaxis.label.set_color(sec_text)
        
        # Spines (borders) styling
        for spine in ax.spines.values():
            spine.set_color(border_color)
            spine.set_linewidth(1)


class DashboardAnalyticsPanel(ctk.CTkFrame):
    """
    Renders 4 system-wide analytics charts:
    1. Monthly Credit vs Debit (Line Chart)
    2. Top Customers by Outstanding Balance (Horizontal Bar Chart)
    3. Receivable vs Payable (Pie Chart)
    4. Monthly Transaction Count (Bar Chart)
    """
    def __init__(self, parent, analytics_service):
        super().__init__(parent, fg_color="transparent")
        self.service = analytics_service

        # Configure 2x3 responsive grid layout (2 cols, 3 rows)
        self.grid_columnconfigure((0, 1), weight=1, uniform="equal")
        self.grid_rowconfigure((0, 1, 2), weight=1, uniform="equal")

        # Keep references to active canvases to avoid GC
        self.canvases = []
        self._selected_tag = "All"

    def clear_charts(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.canvases.clear()

    def update_dashboard_data(self):
        self.clear_charts()

        try:
            monthly_data = self.service.get_monthly_credit_vs_debit()
            top_cust_data = self.service.get_top_customers_by_balance()
            rec_pay_data = self.service.get_receivable_vs_payable()
            txn_count_data = self.service.get_monthly_transaction_count()
        except Exception as e:
            print(f"Error gathering dashboard analytics: {e}")
            return

        # Read layout colors
        bg_sec = ThemedChartCanvas.get_color(Theme.BG_SECONDARY)
        border_col = ThemedChartCanvas.get_color(Theme.BORDER_COLOR)
        text_prim = ThemedChartCanvas.get_color(Theme.TEXT_PRIMARY)
        text_sec = ThemedChartCanvas.get_color(Theme.TEXT_SECONDARY)
        debit_color = ThemedChartCanvas.get_color(Theme.DEBIT_RED)
        credit_color = ThemedChartCanvas.get_color(Theme.CREDIT_GREEN)
        accent_color = ThemedChartCanvas.get_color(Theme.ACCENT)

        # -------------------------------------------------------------
        # Chart 1: Monthly Credit vs Debit (Line Chart)
        # -------------------------------------------------------------
        frame_chart1 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        fig1 = ThemedChartCanvas.create_figure(4, 2.5)
        ax1 = fig1.add_subplot(111)
        ThemedChartCanvas.style_axes(ax1, "Monthly Credit vs Debit")

        if monthly_data:
            months = [x["label"] for x in monthly_data]
            debits = [x["debit"] for x in monthly_data]
            credits = [x["credit"] for x in monthly_data]

            ax1.plot(months, debits, color=debit_color, marker='o', linewidth=2, label="Debit (Owed)")
            ax1.plot(months, credits, color=credit_color, marker='s', linewidth=2, label="Credit (Paid)")
            ax1.legend(facecolor=bg_sec, edgecolor=border_col, labelcolor=text_prim, fontsize=8)
            ax1.tick_params(axis='x', rotation=35)
        else:
            ax1.text(0.5, 0.5, "No Data Available", color=text_sec, ha='center', va='center')

        canvas1 = FigureCanvasTkAgg(fig1, master=frame_chart1)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas1)

        # -------------------------------------------------------------
        # Chart 2: Top Customers by Balance (Horizontal Bar Chart)
        # -------------------------------------------------------------
        frame_chart2 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        fig2 = ThemedChartCanvas.create_figure(4, 2.5)
        ax2 = fig2.add_subplot(111)
        ThemedChartCanvas.style_axes(ax2, "Top 10 Customers Outstanding")

        if top_cust_data:
            # Sort ascending for horizontal bar chart to show highest at the top
            sorted_custs = sorted(top_cust_data, key=lambda x: x["balance"])
            names = [x["name"] for x in sorted_custs]
            balances = [x["balance"] for x in sorted_custs]
            
            # Map colors: Green if credit balance (< 0), Red if outstanding debit (> 0)
            colors = [credit_color if b < 0 else debit_color for b in balances]
            ax2.barh(names, balances, color=colors, height=0.6)
            ax2.axvline(0, color=text_prim, linewidth=0.8, linestyle="--")
        else:
            ax2.text(0.5, 0.5, "No Data Available", color=text_sec, ha='center', va='center')

        canvas2 = FigureCanvasTkAgg(fig2, master=frame_chart2)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas2)

        # -------------------------------------------------------------
        # Chart 3: Receivable vs Payable (Pie Chart)
        # -------------------------------------------------------------
        frame_chart3 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart3.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        fig3 = ThemedChartCanvas.create_figure(4, 2.5)
        ax3 = fig3.add_subplot(111)
        ThemedChartCanvas.style_axes(ax3, "Receivables vs Payables")

        rec = rec_pay_data.get("receivable", 0.0)
        pay = rec_pay_data.get("payable", 0.0)

        if rec > 0 or pay > 0:
            labels = ["Receivables (Dr)", "Payables (Cr)"]
            sizes = [rec, pay]
            colors = [debit_color, credit_color]
            bg_prim = ThemedChartCanvas.get_color(Theme.BG_PRIMARY)
            
            wedges, texts, autotexts = ax3.pie(
                sizes, 
                labels=labels, 
                autopct=lambda pct: f"${pct*sum(sizes)/100:,.0f}\n({pct:.1f}%)",
                colors=colors,
                startangle=140,
                textprops=dict(color=text_prim, fontsize=8)
            )
            for autotext in autotexts:
                autotext.set_color(bg_prim)
                autotext.set_weight('bold')
        else:
            ax3.text(0.5, 0.5, "No Outstanding Balances", color=text_sec, ha='center', va='center')

        canvas3 = FigureCanvasTkAgg(fig3, master=frame_chart3)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas3)

        # -------------------------------------------------------------
        # Chart 4: Monthly Transaction Count (Bar Chart)
        # -------------------------------------------------------------
        frame_chart4 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart4.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        fig4 = ThemedChartCanvas.create_figure(4, 2.5)
        ax4 = fig4.add_subplot(111)
        ThemedChartCanvas.style_axes(ax4, "Monthly Transaction Count")

        if txn_count_data:
            months = [x["label"] for x in txn_count_data]
            counts = [x["count"] for x in txn_count_data]

            ax4.bar(months, counts, color=accent_color, width=0.5, edgecolor=border_col, align='center')
            ax4.tick_params(axis='x', rotation=35)
            # Force integer ticks on y-axis
            # pyrefly: ignore [missing-import]
            from matplotlib.ticker import MaxNLocator
            ax4.yaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            ax4.text(0.5, 0.5, "No Data Available", color=text_sec, ha='center', va='center')

        canvas4 = FigureCanvasTkAgg(fig4, master=frame_chart4)
        canvas4.draw()
        canvas4.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas4)

        # -------------------------------------------------------------
        # Chart 5: Customer Count by Category (Horizontal Bar)
        # -------------------------------------------------------------
        frame_chart5 = ctk.CTkFrame(
            self, fg_color=Theme.BG_SECONDARY,
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR
        )
        frame_chart5.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        try:
            tag_dist = self.service.get_customer_tag_distribution()
        except Exception:
            tag_dist = []

        fig5 = ThemedChartCanvas.create_figure(4, 2.5)
        ax5 = fig5.add_subplot(111)
        ThemedChartCanvas.style_axes(ax5, "Customers by Category")

        # Tag-specific palette (dark-mode accents)
        _TAG_COLORS_CHART = {
            "General":   "#94A3B8",
            "Retail":    "#38BDF8",
            "Wholesale": "#A78BFA",
            "VIP":       "#FCD34D",
            "Supplier":  "#4ADE80",
            "Family":    "#F472B6",
        }

        if tag_dist:
            tags   = [d["tag"]   for d in tag_dist]
            counts = [d["count"] for d in tag_dist]
            colors_bar = [_TAG_COLORS_CHART.get(t, accent_color) for t in tags]
            bars = ax5.barh(tags, counts, color=colors_bar, height=0.55, edgecolor="none")
            ax5.bar_label(bars, labels=[str(c) for c in counts], padding=4,
                         color=text_prim, fontsize=9, fontweight='bold')
            ax5.set_xlabel("Number of Customers", color=text_sec, fontsize=9)
        else:
            ax5.text(0.5, 0.5, "No Customers Added Yet", color=text_sec, ha='center', va='center')

        canvas5 = FigureCanvasTkAgg(fig5, master=frame_chart5)
        canvas5.draw()
        canvas5.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas5)

        # -------------------------------------------------------------
        # Chart 6: Top Customers by Selected Tag (Horizontal Bar)
        # -------------------------------------------------------------
        frame_chart6 = ctk.CTkFrame(
            self, fg_color=Theme.BG_SECONDARY,
            corner_radius=Theme.CORNER_RADIUS,
            border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR
        )
        frame_chart6.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        frame_chart6.grid_columnconfigure(0, weight=1)
        frame_chart6.grid_rowconfigure(1, weight=1)

        # Tag selector header
        from ledger_app.models.customer import BUILTIN_TAGS
        ctrl_row = ctk.CTkFrame(frame_chart6, fg_color="transparent")
        ctrl_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))

        ctk.CTkLabel(
            ctrl_row, text="Top Customers –",
            font=Theme.FONT_BODY_BOLD, text_color=text_prim
        ).pack(side="left")

        self._tag_selector_var = ctk.StringVar(value=self._selected_tag)
        self._tag_selector = ctk.CTkOptionMenu(
            ctrl_row,
            values=["All"] + BUILTIN_TAGS,
            variable=self._tag_selector_var,
            font=Theme.FONT_CAPTION,
            width=110, height=24,
            fg_color=Theme.BG_TERTIARY,
            button_color=Theme.BG_TERTIARY,
            button_hover_color=Theme.BORDER_COLOR,
            text_color=text_prim,
            command=lambda val: self.update_dashboard_data()
        )
        self._tag_selector.pack(side="left", padx=(6, 0))

        # Chart container
        self._chart6_host = ctk.CTkFrame(frame_chart6, fg_color="transparent")
        self._chart6_host.grid(row=1, column=0, sticky="nsew")

        self._draw_top_customers_by_tag()

    def _draw_top_customers_by_tag(self):
        """(Re)draws Chart 6 according to the currently selected tag filter."""
        for w in self._chart6_host.winfo_children():
            w.destroy()

        selected = self._tag_selector_var.get() if hasattr(self, '_tag_selector_var') else "All"
        self._selected_tag = selected

        bg_sec     = ThemedChartCanvas.get_color(Theme.BG_SECONDARY)
        text_prim  = ThemedChartCanvas.get_color(Theme.TEXT_PRIMARY)
        text_sec   = ThemedChartCanvas.get_color(Theme.TEXT_SECONDARY)
        debit_col  = ThemedChartCanvas.get_color(Theme.DEBIT_RED)
        credit_col = ThemedChartCanvas.get_color(Theme.CREDIT_GREEN)
        accent_col = ThemedChartCanvas.get_color(Theme.ACCENT)

        _TAG_COLORS_CHART = {
            "General":   "#94A3B8", "Retail":  "#38BDF8",
            "Wholesale": "#A78BFA", "VIP":     "#FCD34D",
            "Supplier":  "#4ADE80", "Family":  "#F472B6",
        }

        try:
            if selected == "All":
                top_data = self.service.get_top_customers_by_balance()
            else:
                top_data = self.service.get_top_customers_by_tag(selected, limit=5)
        except Exception:
            top_data = []

        fig6 = ThemedChartCanvas.create_figure(4, 2.2)
        ax6  = fig6.add_subplot(111)
        title = f"Top Customers ({selected})" if selected != "All" else "Top 5 Customers Overall"
        ThemedChartCanvas.style_axes(ax6, title)

        if top_data:
            sorted_data = sorted(top_data, key=lambda x: x["balance"])
            names    = [x["name"] for x in sorted_data]
            balances = [x["balance"] for x in sorted_data]
            tag_col  = _TAG_COLORS_CHART.get(selected, accent_col) if selected != "All" else accent_col
            bar_colors = [credit_col if b < 0 else tag_col for b in balances]
            ax6.barh(names, balances, color=bar_colors, height=0.5, edgecolor="none")
            ax6.axvline(0, color=text_prim, linewidth=0.8, linestyle="--")
        else:
            ax6.text(0.5, 0.5, "No Data for Selected Tag", color=text_sec, ha='center', va='center')

        canvas6 = FigureCanvasTkAgg(fig6, master=self._chart6_host)
        canvas6.draw()
        canvas6.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas6)


class CustomerAnalyticsPanel(ctk.CTkFrame):
    """
    Renders 4 customer-specific analytics charts:
    1. Credit History Trend (Line Chart)
    2. Debit History Trend (Line Chart)
    3. Running Balance Trend (Line Chart)
    4. Payment Mode Breakdown (Pie Chart)
    """
    def __init__(self, parent, analytics_service):
        super().__init__(parent, fg_color="transparent")
        self.service = analytics_service

        # Configure 2x2 responsive grid layout
        self.grid_columnconfigure((0, 1), weight=1, uniform="equal")
        self.grid_rowconfigure((0, 1), weight=1, uniform="equal")

        self.canvases = []

    def clear_charts(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.canvases.clear()

    def update_customer_data(self, customer_id: int):
        self.clear_charts()

        try:
            data = self.service.get_customer_analytics_data(customer_id)
        except Exception as e:
            print(f"Error gathering customer analytics: {e}")
            return

        cred_hist = data["credit_history"]
        deb_hist = data["debit_history"]
        run_hist = data["running_history"]
        pm_breakdown = data["payment_mode_breakdown"]

        # Read layout colors
        bg_sec = ThemedChartCanvas.get_color(Theme.BG_SECONDARY)
        border_col = ThemedChartCanvas.get_color(Theme.BORDER_COLOR)
        text_prim = ThemedChartCanvas.get_color(Theme.TEXT_PRIMARY)
        text_sec = ThemedChartCanvas.get_color(Theme.TEXT_SECONDARY)
        debit_color = ThemedChartCanvas.get_color(Theme.DEBIT_RED)
        credit_color = ThemedChartCanvas.get_color(Theme.CREDIT_GREEN)
        accent_color = ThemedChartCanvas.get_color(Theme.ACCENT)

        # -------------------------------------------------------------
        # Chart 1: Credit History Trend (Line Chart)
        # -------------------------------------------------------------
        frame_chart1 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        fig1 = ThemedChartCanvas.create_figure(4, 2.5)
        ax1 = fig1.add_subplot(111)
        ThemedChartCanvas.style_axes(ax1, "Credit History Trend")

        if cred_hist:
            dates = [x["date"] for x in cred_hist]
            amounts = [x["amount"] for x in cred_hist]
            ax1.plot(dates, amounts, color=credit_color, marker='o', linestyle='-', linewidth=2)
            ax1.tick_params(axis='x', rotation=30)
        else:
            ax1.text(0.5, 0.5, "No Credit Payments Logged", color=text_sec, ha='center', va='center')

        canvas1 = FigureCanvasTkAgg(fig1, master=frame_chart1)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas1)

        # -------------------------------------------------------------
        # Chart 2: Debit History Trend (Line Chart)
        # -------------------------------------------------------------
        frame_chart2 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        fig2 = ThemedChartCanvas.create_figure(4, 2.5)
        ax2 = fig2.add_subplot(111)
        ThemedChartCanvas.style_axes(ax2, "Debit/Charge History Trend")

        if deb_hist:
            dates = [x["date"] for x in deb_hist]
            amounts = [x["amount"] for x in deb_hist]
            ax2.plot(dates, amounts, color=debit_color, marker='o', linestyle='-', linewidth=2)
            ax2.tick_params(axis='x', rotation=30)
        else:
            ax2.text(0.5, 0.5, "No Debits/Charges Logged", color=text_sec, ha='center', va='center')

        canvas2 = FigureCanvasTkAgg(fig2, master=frame_chart2)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas2)

        # -------------------------------------------------------------
        # Chart 3: Running Balance Trend (Line Chart)
        # -------------------------------------------------------------
        frame_chart3 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart3.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        fig3 = ThemedChartCanvas.create_figure(4, 2.5)
        ax3 = fig3.add_subplot(111)
        ThemedChartCanvas.style_axes(ax3, "Running Balance Trend")

        if run_hist:
            dates = [x["date"] for x in run_hist]
            balances = [x["balance"] for x in run_hist]
            ax3.plot(dates, balances, color=accent_color, marker='s', linestyle='-', linewidth=2)
            ax3.axhline(0, color=text_prim, linewidth=0.8, linestyle="--")
            ax3.tick_params(axis='x', rotation=30)
        else:
            ax3.text(0.5, 0.5, "No Running History", color=text_sec, ha='center', va='center')

        canvas3 = FigureCanvasTkAgg(fig3, master=frame_chart3)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas3)

        # -------------------------------------------------------------
        # Chart 4: Payment Mode Breakdown (Pie Chart)
        # -------------------------------------------------------------
        frame_chart4 = ctk.CTkFrame(self, fg_color=Theme.BG_SECONDARY, corner_radius=Theme.CORNER_RADIUS, border_width=Theme.BORDER_WIDTH, border_color=Theme.BORDER_COLOR)
        frame_chart4.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        fig4 = ThemedChartCanvas.create_figure(4, 2.5)
        ax4 = fig4.add_subplot(111)
        ThemedChartCanvas.style_axes(ax4, "Payment Mode Breakdown")

        if pm_breakdown and sum(pm_breakdown.values()) > 0:
            labels = list(pm_breakdown.keys())
            sizes = list(pm_breakdown.values())
            
            # Premium color palette for payment modes from theme manager values
            warning_color = ThemedChartCanvas.get_color(Theme.WARNING_ORANGE)
            blue_color = ThemedChartCanvas.get_color(Theme.NEUTRAL_BLUE)
            colors = [accent_color, credit_color, warning_color, debit_color, blue_color][:len(labels)]
            bg_prim = ThemedChartCanvas.get_color(Theme.BG_PRIMARY)
            
            wedges, texts, autotexts = ax4.pie(
                sizes, 
                labels=labels, 
                autopct='%1.1f%%',
                colors=colors,
                startangle=90,
                textprops=dict(color=text_prim, fontsize=8)
            )
            for autotext in autotexts:
                autotext.set_color(bg_prim)
                autotext.set_weight('bold')
        else:
            ax4.text(0.5, 0.5, "No Payments Logged", color=text_sec, ha='center', va='center')

        canvas4 = FigureCanvasTkAgg(fig4, master=frame_chart4)
        canvas4.draw()
        canvas4.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvases.append(canvas4)
