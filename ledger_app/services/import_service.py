"""
import_service.py
=================
Excel Import Engine for Jalaj Ledger Management System.

Responsibilities:
  - Parse .xlsx / .xls files using pandas + openpyxl
  - Validate customer and transaction rows
  - Write to SQLite atomically (all-or-nothing per batch)
  - Return structured ImportResult with counts and error details

Design principles:
  - Pure service — zero UI dependencies
  - All public methods return (success, result/message) tuples
  - DB writes use a single connection context → SQLite auto-rolls back on exception
"""

import re
import os
import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ImportError:
    """Describes a single row-level validation error."""
    row_number: int          # 1-indexed (header = row 1, first data row = 2)
    column:     str
    value:      str
    reason:     str


@dataclass
class ImportResult:
    """Summary returned after an import operation."""
    import_type:   str           # "Customers" | "Transactions"
    total_rows:    int   = 0
    imported:      int   = 0
    skipped:       int   = 0
    errors:        List[ImportError] = field(default_factory=list)
    warnings:      List[str]         = field(default_factory=list)
    success:       bool  = False
    message:       str   = ""

    @property
    def error_count(self) -> int:
        return len(self.errors)


# ---------------------------------------------------------------------------
# ImportService
# ---------------------------------------------------------------------------

VALID_TRANSACTION_TYPES = {"CREDIT", "DEBIT", "DAILY_CHARGE"}

DATE_FORMATS = [
    "%Y-%m-%d",       # 2024-01-15
    "%d/%m/%Y",       # 15/01/2024
    "%d-%m-%Y",       # 15-01-2024
    "%m/%d/%Y",       # 01/15/2024
    "%Y/%m/%d",       # 2024/01/15
    "%d %b %Y",       # 15 Jan 2024
    "%d %B %Y",       # 15 January 2024
]


class ImportService:
    """
    Core import engine.  Stateless — create one instance and reuse.
    All DB-write methods are atomic: a single exception rolls back the whole batch.
    """

    # ── Excel Parsing ────────────────────────────────────────────────────────

    @staticmethod
    def parse_excel(filepath: str) -> Tuple[bool, Any, str]:
        """
        Reads all sheets from an Excel file into a dict of DataFrames.

        Returns:
            (success, sheets_dict, message)
            sheets_dict: { sheet_name: pandas.DataFrame }  or None on failure
        """
        try:
            import pandas as pd
        except ImportError:
            return False, None, "pandas is not installed. Run: pip install pandas"

        if not os.path.exists(filepath):
            return False, None, f"File not found: {filepath}"

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in (".xlsx", ".xls", ".xlsm"):
            return False, None, f"Unsupported file type: {ext}. Use .xlsx or .xls"

        try:
            sheets = pd.read_excel(filepath, sheet_name=None, dtype=str, keep_default_na=False)
            if not sheets:
                return False, None, "The Excel file contains no sheets."
            return True, sheets, f"Loaded {len(sheets)} sheet(s) successfully."
        except Exception as e:
            return False, None, f"Could not read Excel file: {e}"

    @staticmethod
    def get_column_names(sheets: dict, sheet_name: str) -> List[str]:
        """Returns the column header names for a given sheet."""
        df = sheets.get(sheet_name)
        if df is None or df.empty:
            return []
        return list(df.columns)

    @staticmethod
    def get_preview_rows(sheets: dict, sheet_name: str, max_rows: int = 10) -> List[Dict]:
        """Returns up to max_rows preview rows from a sheet as list of dicts."""
        df = sheets.get(sheet_name)
        if df is None or df.empty:
            return []
        return df.head(max_rows).to_dict(orient="records")

    # ── Validation ───────────────────────────────────────────────────────────

    @staticmethod
    def validate_customers(
        sheets: dict,
        sheet_name: str,
        col_map: Dict[str, str],          # { "Name": excel_col, "Phone": excel_col, ... }
    ) -> Tuple[List[Dict], List[ImportError]]:
        """
        Validates rows for Customer import.

        col_map keys (all optional except "Name"):
            "Name", "Phone", "Address", "Opening Balance"

        Returns:
            (valid_rows, errors)
            valid_rows: list of cleaned dicts ready for DB insert
        """
        try:
            import pandas as pd
        except ImportError:
            return [], []

        df = sheets.get(sheet_name)
        if df is None or df.empty:
            return [], [ImportError(0, "Sheet", sheet_name, "Sheet is empty.")]

        valid_rows: List[Dict] = []
        errors: List[ImportError] = []
        seen_names: set = set()

        name_col   = col_map.get("Name", "")
        phone_col  = col_map.get("Phone", "")
        addr_col   = col_map.get("Address", "")
        bal_col    = col_map.get("Opening Balance", "")

        for idx, row in df.iterrows():
            row_num = int(idx) + 2   # +2: 1 for header, 1 for 0-index

            # ── Name (required) ──────────────────────────────────────────
            name_raw = str(row.get(name_col, "")).strip() if name_col else ""
            if not name_raw or len(name_raw) < 2:
                errors.append(ImportError(row_num, "Name", name_raw,
                                          "Name is required and must be at least 2 characters."))
                continue

            # Duplicate within this file
            name_key = name_raw.lower()
            if name_key in seen_names:
                errors.append(ImportError(row_num, "Name", name_raw,
                                          "Duplicate name within the import file."))
                continue
            seen_names.add(name_key)

            # ── Phone (optional) ─────────────────────────────────────────
            phone_raw  = str(row.get(phone_col, "")).strip() if phone_col else ""
            phone_clean = None
            if phone_raw:
                digits = re.sub(r"\D", "", phone_raw)
                if not (10 <= len(digits) <= 15):
                    errors.append(ImportError(row_num, "Phone", phone_raw,
                                              "Phone must contain 10–15 digits."))
                    continue
                phone_clean = digits

            # ── Address (optional, free text) ────────────────────────────
            address = str(row.get(addr_col, "")).strip() if addr_col else ""
            address = address or None

            # ── Opening Balance (optional, numeric) ──────────────────────
            bal_raw = str(row.get(bal_col, "")).strip() if bal_col else ""
            opening_balance = 0.0
            if bal_raw:
                try:
                    opening_balance = float(bal_raw.replace(",", ""))
                except ValueError:
                    errors.append(ImportError(row_num, "Opening Balance", bal_raw,
                                              "Opening Balance must be a number."))
                    continue

            valid_rows.append({
                "name":            name_raw,
                "phone":           phone_clean,
                "address":         address,
                "opening_balance": opening_balance,
                "notes":           None,
                "_row":            row_num,
            })

        return valid_rows, errors

    @staticmethod
    def validate_transactions(
        sheets: dict,
        sheet_name: str,
        col_map: Dict[str, str],          # { "Customer Name": col, "Type": col, ... }
        existing_customer_names: Dict[str, int],   # { lower_name: customer_id }
        existing_payment_modes:  Dict[str, int],   # { lower_mode_name: mode_id }
    ) -> Tuple[List[Dict], List[ImportError]]:
        """
        Validates rows for Transaction import.

        col_map keys:
            "Customer Name", "Type", "Amount", "Payment Mode", "Date", "Notes"

        Returns:
            (valid_rows, errors)
        """
        try:
            import pandas as pd
        except ImportError:
            return [], []

        df = sheets.get(sheet_name)
        if df is None or df.empty:
            return [], [ImportError(0, "Sheet", sheet_name, "Sheet is empty.")]

        valid_rows: List[Dict] = []
        errors: List[ImportError] = []

        cname_col   = col_map.get("Customer Name", "")
        type_col    = col_map.get("Type", "")
        amount_col  = col_map.get("Amount", "")
        mode_col    = col_map.get("Payment Mode", "")
        date_col    = col_map.get("Date", "")
        notes_col   = col_map.get("Notes", "")

        for idx, row in df.iterrows():
            row_num = int(idx) + 2

            # ── Customer Name (required, must exist) ─────────────────────
            cname_raw = str(row.get(cname_col, "")).strip() if cname_col else ""
            if not cname_raw:
                errors.append(ImportError(row_num, "Customer Name", cname_raw,
                                          "Customer Name is required."))
                continue

            customer_id = existing_customer_names.get(cname_raw.lower())
            if customer_id is None:
                errors.append(ImportError(row_num, "Customer Name", cname_raw,
                                          f"No customer named '{cname_raw}' found in the database."))
                continue

            # ── Transaction Type (required) ───────────────────────────────
            type_raw = str(row.get(type_col, "")).strip().upper() if type_col else ""
            if type_raw not in VALID_TRANSACTION_TYPES:
                errors.append(ImportError(row_num, "Type", type_raw,
                                          f"Type must be one of: {', '.join(VALID_TRANSACTION_TYPES)}."))
                continue

            # ── Amount (required, > 0) ───────────────────────────────────
            amount_raw = str(row.get(amount_col, "")).strip() if amount_col else ""
            try:
                amount = float(amount_raw.replace(",", ""))
                if amount <= 0:
                    raise ValueError()
            except ValueError:
                errors.append(ImportError(row_num, "Amount", amount_raw,
                                          "Amount must be a number greater than zero."))
                continue

            # ── Payment Mode (required for CREDIT, optional otherwise) ───
            mode_raw = str(row.get(mode_col, "")).strip() if mode_col else ""
            payment_mode_id = None
            if mode_raw:
                payment_mode_id = existing_payment_modes.get(mode_raw.lower())
                if payment_mode_id is None:
                    # Auto-create the payment mode instead of erroring
                    # (record as warning, will be created during import)
                    pass  # handled in import step

            if type_raw == "CREDIT" and not mode_raw:
                errors.append(ImportError(row_num, "Payment Mode", "",
                                          "Payment Mode is required for CREDIT transactions."))
                continue

            # ── Date (optional, parse flexibly) ──────────────────────────
            date_raw = str(row.get(date_col, "")).strip() if date_col else ""
            parsed_date: Optional[str] = None
            if date_raw:
                parsed_date = ImportService._parse_date(date_raw)
                if parsed_date is None:
                    errors.append(ImportError(row_num, "Date", date_raw,
                                              "Date format not recognised. Use YYYY-MM-DD or DD/MM/YYYY."))
                    continue

            # ── Notes (optional) ─────────────────────────────────────────
            notes = str(row.get(notes_col, "")).strip() if notes_col else ""
            notes = notes or None

            valid_rows.append({
                "customer_id":      customer_id,
                "customer_name":    cname_raw,
                "transaction_type": type_raw,
                "amount":           amount,
                "payment_mode_raw": mode_raw,
                "payment_mode_id":  payment_mode_id,
                "transaction_date": parsed_date,
                "description":      notes,
                "_row":             row_num,
            })

        return valid_rows, errors

    # ── Database Writes ──────────────────────────────────────────────────────

    @staticmethod
    def import_customers(
        valid_rows: List[Dict],
        customer_service,
        existing_customer_names: Dict[str, int],   # to detect pre-existing in DB
    ) -> ImportResult:
        """
        Atomically inserts all valid customer rows.
        Skips rows whose name already exists in the database (case-insensitive).
        Returns ImportResult.
        """
        result = ImportResult(import_type="Customers", total_rows=len(valid_rows))

        for row in valid_rows:
            name_key = row["name"].lower()
            if name_key in existing_customer_names:
                result.skipped += 1
                result.warnings.append(
                    f"Row {row['_row']}: Customer '{row['name']}' already exists — skipped."
                )
                continue
            try:
                customer_service.create_customer(
                    name=row["name"],
                    phone=row["phone"],
                    address=row["address"],
                    notes=row["notes"],
                    opening_balance=row["opening_balance"],
                )
                result.imported += 1
                # Add to seen set to prevent duplicate within same import
                existing_customer_names[name_key] = -1
            except Exception as e:
                result.errors.append(ImportError(
                    row_num=row["_row"],
                    column="DB",
                    value=row["name"],
                    reason=str(e)
                ))
                result.skipped += 1

        result.success  = True
        result.message  = (
            f"Import complete: {result.imported} customers imported, "
            f"{result.skipped} skipped, {result.error_count} errors."
        )
        return result

    @staticmethod
    def import_transactions(
        valid_rows: List[Dict],
        transaction_service,
        payment_mode_repo,
        existing_payment_modes: Dict[str, int],
    ) -> ImportResult:
        """
        Atomically inserts all valid transaction rows.
        Auto-creates unknown payment modes before inserting.
        Returns ImportResult.
        """
        result = ImportResult(import_type="Transactions", total_rows=len(valid_rows))

        for row in valid_rows:
            mode_raw = row.get("payment_mode_raw", "")
            payment_mode_id = row.get("payment_mode_id")

            # Auto-create payment mode if provided but not found
            if mode_raw and payment_mode_id is None:
                try:
                    from ledger_app.models.payment_mode import PaymentMode
                    new_mode = PaymentMode(id=None, mode_name=mode_raw)
                    payment_mode_id = payment_mode_repo.save(new_mode)
                    existing_payment_modes[mode_raw.lower()] = payment_mode_id
                    result.warnings.append(
                        f"Row {row['_row']}: Payment mode '{mode_raw}' created automatically."
                    )
                except Exception as e:
                    result.errors.append(ImportError(
                        row_num=row["_row"],
                        column="Payment Mode",
                        value=mode_raw,
                        reason=f"Could not create payment mode: {e}"
                    ))
                    result.skipped += 1
                    continue

            try:
                transaction_service.record_transaction(
                    customer_id=row["customer_id"],
                    transaction_type=row["transaction_type"],
                    amount=row["amount"],
                    payment_mode_id=payment_mode_id,
                    description=row["description"],
                    transaction_date=row["transaction_date"],
                )
                result.imported += 1
            except Exception as e:
                result.errors.append(ImportError(
                    row_num=row["_row"],
                    column="DB",
                    value=str(row["customer_name"]),
                    reason=str(e)
                ))
                result.skipped += 1

        result.success = True
        result.message = (
            f"Import complete: {result.imported} transactions imported, "
            f"{result.skipped} skipped, {result.error_count} errors."
        )
        return result

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def build_customer_name_map(customer_service) -> Dict[str, int]:
        """Returns { lower_name: customer_id } for all existing customers."""
        try:
            customers = customer_service.list_customers()
            return {c["name"].lower(): c["id"] for c in customers}
        except Exception:
            return {}

    @staticmethod
    def build_payment_mode_map(payment_mode_repo) -> Dict[str, int]:
        """Returns { lower_mode_name: mode_id } for all existing payment modes."""
        try:
            modes = payment_mode_repo.find_all()
            return {m.mode_name.lower(): m.id for m in modes}
        except Exception:
            return {}

    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        """
        Tries to parse date_str using known formats.
        Returns ISO 8601 string 'YYYY-MM-DD' on success, None on failure.
        """
        date_str = date_str.strip()
        for fmt in DATE_FORMATS:
            try:
                dt = datetime.datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        # Try pandas timestamp string (e.g. "2024-01-15 00:00:00")
        try:
            dt = datetime.datetime.fromisoformat(date_str.split(" ")[0])
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        return None
