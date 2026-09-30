import os
import sys

# Ensure the root of the project is in python's search path to allow clean packages imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import App

def main():
    """Boots the Ledger Management application."""
    print("Launching Jalajs Ledger Management System...")
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
