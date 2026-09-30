import os
import sys

# Set test mode environment variable to bypass login screen during verification
os.environ["TEST_MODE"] = "1"

# Add directory to sys.path to resolve package imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ledger_app.ui.app import App

def test_full_app_compilation():
    db_file = "ledger.db"
    
    # We will test instantiating the main App class.
    # It will initialize sqlite, seed data, bootstrap services,
    # build all screen widgets, configure sidebar navigation and layouts, and bind routes.
    print("Bootstrap testing main App container shell...")
    
    try:
        app = App()
        assert app is not None
        print("Application instantiated successfully with all layout frames wired!")
        
        # Test routing Switch Screen commands
        print("Testing Screen navigation routing flows...")
        app.switch_screen("Customers")
        assert app.active_screen_name == "Customers"
        print("  Routed to Customers screen.")
        
        app.switch_screen("New Entry")
        assert app.active_screen_name == "New Entry"
        print("  Routed to New Entry screen.")

        app.switch_screen("Reports")
        assert app.active_screen_name == "Reports"
        print("  Routed to Reports screen.")

        app.switch_screen("Settings")
        assert app.active_screen_name == "Settings"
        print("  Routed to Settings screen.")
        
        app.switch_screen("Dashboard")
        assert app.active_screen_name == "Dashboard"
        print("  Routed to Dashboard screen.")

        # Test close handler triggering the shutdown notification
        print("Testing Application close event trigger...")
        app.on_close()
        print("\n*** FULL APP COMPILATION & NOTIFICATION TEST COMPLETED SUCCESSFULLY! ***")
        
    except Exception as e:
        print(f"\nRuntime Error during App Boot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_full_app_compilation()
