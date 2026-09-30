"""
Single-file PyInstaller launcher for Jalaj Ledger.
Handles frozen (--onefile) mode: sets working directory to the
folder where the .exe lives so settings.json / ledger.db resolve correctly.
"""
import os
import sys

if getattr(sys, "frozen", False):
    # Running as a bundled .exe — chdir to the exe's directory
    os.chdir(os.path.dirname(sys.executable))
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ledger_app.services.settings_preprocessor import preprocess_settings
    preprocess_settings()
except Exception as e:
    print(f"Error executing settings preprocessor: {e}")

from ledger_app.ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
