import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from tkinter import messagebox
from app.db.session import check_connection, init_db
from app.core.config import reload_settings
from app.ui.db_settings_dialog import DatabaseSettingsDialog

try:
    from app.ui.main_window import App
except (AssertionError, ImportError) as e:
    # Catching specific SQLAlchemy/Typing error common in wrong environments
    if "SQLCoreOperations" in str(e) or "TypingOnly" in str(e):
        print("\n" + "="*60)
        print("CRITICAL ERROR: INCOMPATIBLE ENVIRONMENT DETECTED")
        print("="*60)
        print(f"Error details: {e}")
        print("-" * 60)
        print("You are likely running this application with a Python environment")
        print("that has incompatible libraries installed.")
        print("\nPLEASE FOLLOW THESE STEPS:")
        print("1. Do not run 'python -m app.main' directly.")
        print("2. Instead, double-click 'run.bat' in the project folder.")
        print("   OR run 'run.bat' from the terminal.")
        print("="*60 + "\n")
        input("Press Enter to exit...")
        sys.exit(1)
    raise

def main():
    # Check DB Connection
    if not check_connection():
        # Create a temp root for dialogs
        root = ctk.CTk()
        root.withdraw() # Hide it
        
        # Center the window roughly (optional, but good for dialog placement)
        try:
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width // 2)
            y = (screen_height // 2)
            root.geometry(f"1x1+{x}+{y}")
        except:
            pass
            
        messagebox.showerror("Connection Error", "Database connection failed.\nPlease update your connection settings.")
        
        while not check_connection():
            dialog = DatabaseSettingsDialog(root)
            # Wait for dialog to close
            root.wait_window(dialog)
            
            # Reload settings and retry connection
            reload_settings()
            init_db()
            
            if check_connection():
                messagebox.showinfo("Success", "Database connected successfully!")
                break
            
            # If still failed, ask user what to do
            if not messagebox.askretrycancel("Connection Failed", "Database connection still failed. Retry?"):
                root.destroy()
                sys.exit(1)
                
        root.destroy()

    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
