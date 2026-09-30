# Ledger Management System

A premium desktop-based Ledger & Credit-Debit Management System built with Python, CustomTkinter, SQLite, and automated report pipelines. Designed for small and medium businesses to manage customer directories, record daily credits/debits, compute running balances, compile PDF/Excel statements, and dispatch status alerts via native WhatsApp Desktop and secure SMTP Email.

---

## Project Overview

### The Problem It Solves
Small and medium businesses frequently struggle to track client credit extensions, daily payments, and outstanding balances. Manual bookkeeping is prone to calculations drift, lacks secure database indexing, and fails to keep business owners notified of daily activities.

### Target Users
- Small business owners, vendors, and retailers.
- Independent distributors and agencies managing client credit ledger loops.
- Accountants requiring lightweight offline transaction trackers.

### Key Benefits
- **Vibrant & Responsive Dark UI**: A professional user experience styled with custom accent palettes using CustomTkinter.
- **Offline Data Security**: High-performance local SQL indexing and cascading database deletes.
- **Automated Closing Dispatches**: Automatically generates a Daily Summary PDF statement and sends it to the owner's WhatsApp and Email on application exit.
- **Thread-Isolated Alerts**: Startup notifications run in background threads to ensure instant GUI boot times.

---

## Features

| Component | Detailed Functionality | Status |
| :--- | :--- | :--- |
| **Dashboard Screen** | Displays high-level KPI stat cards (Total Outstanding, Today's Credit, Today's Debit, Customer Count) and a scrollable table of the 10 most recent transactions. Includes Matplotlib trend integrations. | Active |
| **Customer Directory** | Add, edit, search, and delete customers. Supports live filters and double-click navigation to ledgers. | Active |
| **Transaction Entry** | credit, debit, or charge entry with type segmentation, automatic autocomplete customer list, description details, notes, and payment mode selectors. | Active |
| **Ledger Statement** | Compiles chronologically sorted transactions list for each customer with running ledger balance computation. | Active |
| **Reports Engine** | Select date ranges, filter by customer, run financial summaries, and output tabular balances. | Active |
| **PDF Statement Export** | Generates wrapped, styled Platypus tables, custom branding headers, page numbering canvas overlays using ReportLab. | Active |
| **Excel Spreadsheet Export** | Auto-fits columns, colorizes steel-blue headers, applies explicit cell formats using OpenPyXL. | Active |
| **Backup & Restore** | Clone active database to user-selected locations, restore database files, and purge all tables safely. | Active |
| **Windows Tray Alerts** | Dispatches background tray balloon alerts on startup and close using native PowerShell sub-routines. | Active |
| **WhatsApp Automation** | Focuses the native WhatsApp Desktop App via Win32 APIs, pre-fills numbers/text, copies files to Clipboard, and pastes (`Ctrl+V`) and sends PDF statements. | Active (Commented) |
| **Email Reports** | Sends SMTP emails using secure TLS/SSL ports (587/465) with base64 encoded daily summaries and PDF reports. | Active |

---

## Screenshots Section

*Placeholders for user interface visuals:*

- **Dashboard**: `screenshots/dashboard.png`
- **Customer List**: `screenshots/customers.png`
- **Ledger View**: `screenshots/ledger.png`
- **Reports Screen**: `screenshots/reports.png`

---

## Technology Stack

- **GUI Core**: CustomTkinter (v5.2.2) & Tkinter
- **Database**: SQLite3 (Thread-safe, WAL logging enabled)
- **PDF Engine**: ReportLab (v4.5.1)
- **Excel Engine**: OpenPyXL (v3.1.5)
- **Data Plotting**: Matplotlib (v3.10.9)
- **Image Handling**: Pillow (v12.2.0)
- **Automation Tools**: PowerShell Script Host (WScript.Shell) & Win32 User32 APIs

---

## Architecture

The application implements a clean **Three-Tier Architecture** to separate concerns:

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                    │
│      (CustomTkinter App Shell, Screens, Components)     │
└────────────────────────────┬────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────┐
│                      Service Layer                      │
│ (CustomerService, LedgerService, ExportService, SMTP...) │
└────────────────────────────┬────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    Repository Layer                     │
│    (CustomerRepository, TransactionRepository, SQL...)   │
└────────────────────────────┬────────────────────────────┘
                             ▼
┌──────────────────
             (SQLite Database, Schema Index)             │
└─────────────────────────────────────────────────────────┘
```

- **UI Layer (`ui/`)**: Draws screens and custom scrollable data grids. Contains no direct database commands or aggregates.
- **Service Layer (`services/`)**: Enforces business logic validation, handles mathematical running balance calculations, generates PDFs, and connects SMTP servers.
- **Repository Layer (`repositories/`)**: Abstracts SQLite connection pools, parses database rows to model entities, and ensures parameterization to prevent SQL injection.
- **Database Layer (`database/`)**: Manages the persistent local file database (`ledger.db`) and enforces schema constraints and indexes.

---

## Project Structure

```
ledger_app/
├── main.py                     # App entry point
├── database/
│   ├── __init__.py
│   ├── db_connection.py        # Database connection pool singleton
│   └── schema.py               # SQLite tables migration schemas
├── models/
│   ├── __init__.py
│   ├── customer.py             # Customer entity dataclass
│   ├── payment_mode.py         # PaymentMode entity dataclass
│   └── transaction.py          # Transaction entity dataclass
├── repositories/
│   ├── __init__.py
│   ├── base_repository.py      # Base repository class wrapper
│   ├── customer_repository.py  # Customer database actions
│   ├── payment_mode_repository.py # Payment modes lookup actions
│   └── transaction_repository.py # Transaction database actions
├── services/
│   ├── __init__.py
│   ├── customer_service.py     # Customer validations & metrics
│   ├── email_service.py        # SMTP email dispatch & attachments
│   ├── export_service.py       # ReportLab PDF & OpenPyXL Excel builders
│   ├── ledger_service.py       # Running balance aggregates
│   ├── notification_service.py # System tray notification popups
│   ├── report_service.py       # Date range & financial statement aggregates
│   ├── transaction_service.py  # Transaction validations
│   └── whatsapp_service.py     # Native WhatsApp Desktop SendKeys automation
└── ui/
    ├── __init__.py
    ├── app.py                  # Parent frame container & route switcher
    ├── theme.py                # Colors design tokens & fonts
    ├── components/
    │   ├── __init__.py
    │   ├── data_table.py       # Zebra-striped scrollable data table
    │   └── stat_card.py        # Dynamic metric indicators
    └── screens/
        ├── __init__.py
        ├── dashboard.py        # Analytics metrics & charts dashboard
        ├── customer_management.py # Search directory & customer forms
        ├── ledger_view.py      # Chronicled statement ledger grid
        ├── reports.py          # Date range filters & export triggers
        ├── settings.py         # App profiles, backups, SMTP configurations
        └── transaction_entry.py # Add transaction autocomplete form
```

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/ledger-app.git
   cd ledger-app
   ```

2. **Setup Virtual Environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python main.py
   ```

---

## Usage Guide

### 1. Add Customer
Go to the **Customers** screen, click **+ Add Customer**, enter Name, Phone, Address, Notes, and Opening Balance. Click Save.

### 2. Record Transaction
Go to the **New Entry** screen. Start typing the customer's name in the autocomplete field, select the transaction type (**DEBIT**, **CREDIT**, or **DAILY_CHARGE**), specify the amount, payment mode, optional notes, and press submit.

### 3. View Ledger
Go to **Customers**, double-click a row to open the client's chronicled ledger. You can add transactions quickly or download statements directly.

### 4. Generate Reports
Go to **Reports**, pick a date range, filter by a customer (optional), and click search to populate the grid.

### 5. Export PDF
From the **Reports** or **Ledger** screens, click **Export PDF** to create a print-ready document.

### 6. Export Excel
Click **Export Excel** from the Reports screen to generate a styled spreadsheet database record.

### 7. Backup Database
Navigate to **Settings**, click **💾 Backup Database**, and select the destination directory.

---

## Business Logic

### Credits & Debits
- **Credit (`CREDIT`)**: Decreases the client's outstanding balance (client paid you money).
- **Debit (`DEBIT` / `DAILY_CHARGE`)**: Increases the client's outstanding balance (client owes you money / fee applied).

### Running Balance Calculation
Calculated chronologically for client statement ledgers:
$$\text{Running Balance} = \text{Opening Balance} + \sum \text{DEBIT} + \sum \text{DAILY\_CHARGE} - \sum \text{CREDIT}$$

### Total Outstanding Balance
Calculated across all clients:
$$\text{Total Outstanding} = \sum \text{Client Current Balances}$$

---

## Database Schema

### Table: `customers`
Stores client directories and opening balance records.
```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    notes TEXT,
    opening_balance REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
```

### Table: `payment_modes`
Preseeded standard payment methods: `'Cash'`, `'UPI / Online'`, `'Card'`, `'Bank Transfer'`, and `'Cheque'`.
```sql
CREATE TABLE payment_modes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode_name TEXT UNIQUE NOT NULL
);
```

### Table: `transactions`
Detailed ledger entries linking transactions to payment modes and customers.
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('CREDIT', 'DEBIT', 'DAILY_CHARGE')),
    amount REAL NOT NULL CHECK(amount >= 0.0),
    payment_mode_id INTEGER,
    description TEXT,
    transaction_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_mode_id) REFERENCES payment_modes(id) ON DELETE SET NULL
);
```

---

## Notifications & Reporting

```
                    ┌─────────────────────────┐
                    │    Window Close (x)     │
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │    Generate PDF Report  │
                    └────────────┬────────────┘
                                 ▼
                     ┌───────────┴───────────┐
            ┌────────▼────────┐     ┌────────▼────────┐
            │ Native WhatsApp │     │   Secure SMTP   │
            │ SendKeys Alert  │     │   Email Send    │
            └─────────────────┘     └─────────────────┘
```

- **Startup Notification**: On boot, the app gathers active metrics (customer counts, credits, debits) and triggers a system tray balloon alert. The task runs asynchronously in a daemon thread.
- **Shutdown Notification**: Gathers metrics tracked on the current calendar day and dispatches a closing tray alert.
- **Daily Summary PDF**: On close, the application compiles daily metrics and writes a styled PDF document inside: `reports/YYYY-MM-DD/daily_summary.pdf`.
- **Email Report Send**: SMTP login is performed using the credentials configured in the settings screen. The daily closing text and the `daily_summary.pdf` file are transmitted synchronously on exit.
- **WhatsApp Integration**: Invokes the `whatsapp://` URI scheme to open the native WhatsApp Desktop App, targets the recipient, and simulates keystrokes to transmit the text summary and clipboard-copied PDF. *Note: WhatsApp hooks are temporarily commented in `ui/app.py` for headless debugging.*

---

## Export & Backup Locations

- **Daily PDF Reports**: `reports/YYYY-MM-DD/daily_summary.pdf`
- **Customer Statement Exports**: Saved at the user's custom selected directory (default folder: `reports/`).
- **Database Backups**: Written as a `.db` file at user-selected locations.

---

## Build Executable

To compile the application into a standalone Windows executable (`.exe`):

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Compile with Assets**:
   ```bash
   pyinstaller --noconfirm --onedir --windowed --name "JalajLedger" --add-data "venv/Lib/site-packages/customtkinter;customtkinter/" main.py
   ```

---

## Troubleshooting

### `ModuleNotFoundError`
- **Cause**: Script executed outside the virtual environment.
- **Fix**: Run `.\venv\Scripts\activate` before launching `python main.py`.

### SQLite Database Locked
- **Cause**: Multiple open connections or overlapping database write routines.
- **Fix**: The application handles WAL mode, but ensure no SQL browser editor is holding an active edit lock on `ledger.db`.

### Email (SMTP) Authentication Error
- **Cause**: Google rejects login attempts using standard Gmail passwords.
- **Fix**: Go to Google Account Settings -> Security. Enable 2FA, generate a **16-Character App Password**, and input this App Password under Settings -> Email Configuration.

---

## Roadmap

- **Multi-device Database Sync**: Secure cloud-sync capabilities.
- **Graphical Matplotlib Analytics**: Add quarterly trend comparison charts to the Dashboard screen.
- **CSV Data Imports**: Bulk upload customer lists from spreadsheet files.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Author

- **Jalaj Singhal** - *Lead Architect & Systems Engineer* - [jalajsinghal25@gmail.com](mailto:jalajsinghal25@gmail.com)
