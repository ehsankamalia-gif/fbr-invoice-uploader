import os
import sys
import time
from PIL import Image

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from tkinter import messagebox

# Defer other imports to allow splash screen to show first

def show_splash():
    """
    Shows a simple splash screen while the app loads.
    Returns the splash root window.
    """
    splash_root = ctk.CTk()
    splash_root.overrideredirect(True) # Borderless
    
    # Dimensions
    width = 500
    height = 300
    
    # Center
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    splash_root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Background
    splash_root.configure(fg_color="#2C3E50")
    
    # Try to load splash image
    try:
        # Check assets folder
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        splash_img_path = os.path.join(assets_dir, "splash.png")
        
        if os.path.exists(splash_img_path):
            # Load and display image
            pil_image = Image.open(splash_img_path)
            # Resize if needed to fit nicely
            pil_image = pil_image.resize((480, 200), Image.Resampling.LANCZOS)
            img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(480, 200))
            
            label_img = ctk.CTkLabel(splash_root, text="", image=img)
            label_img.pack(pady=(20, 10))
        else:
             # Fallback Text if image missing
             ctk.CTkLabel(splash_root, text="HONDA FBR UPLOADER", font=("Arial", 30, "bold"), text_color="white").pack(pady=50)

    except Exception as e:
        print(f"Splash image error: {e}")
        ctk.CTkLabel(splash_root, text="HONDA FBR UPLOADER", font=("Arial", 30, "bold"), text_color="white").pack(pady=50)

    # Loading Text
    lbl_loading = ctk.CTkLabel(splash_root, text="Initializing Application...", font=("Arial", 14), text_color="#BDC3C7")
    lbl_loading.pack(pady=5)
    
    # Progress Bar (Indeterminate)
    progress = ctk.CTkProgressBar(splash_root, width=400, mode="indeterminate")
    progress.pack(pady=10)
    progress.start()
    
    splash_root.update()
    return splash_root, lbl_loading, progress

def main():
    # 1. Show Splash Screen
    splash, status_lbl, progress = show_splash()
    
    # 2. Perform Imports (Simulation of work)
    try:
        status_lbl.configure(text="Loading database settings...")
        splash.update()
        
        from app.db.session import check_connection, init_db
        from app.core.config import reload_settings
        from app.ui.db_settings_dialog import DatabaseSettingsDialog
        
        # 3. Check DB Connection
        status_lbl.configure(text="Connecting to database...")
        splash.update()
        
        if not check_connection():
            # If connection fails, we need to hide splash and show settings
            splash.withdraw()
            
            # Create a temp root for dialogs
            root = ctk.CTk()
            root.withdraw()
            
            messagebox.showerror("Connection Error", "Database connection failed.\nPlease update your connection settings.")
            
            while not check_connection():
                dialog = DatabaseSettingsDialog(root)
                root.wait_window(dialog)
                reload_settings()
                init_db()
                if check_connection():
                    break
                if not messagebox.askretrycancel("Connection Failed", "Database connection still failed. Retry?"):
                    sys.exit(1)
            root.destroy()
            
            # Show splash again for final loading
            splash.deiconify()
        
        # 4. Initialize DB
        status_lbl.configure(text="Initializing database...")
        splash.update()
        init_db()
        
        # 5. Import Main App (Heavy Import)
        status_lbl.configure(text="Loading user interface...")
        splash.update()
        
        try:
            from app.ui.main_window import App
        except (AssertionError, ImportError) as e:
            if "SQLCoreOperations" in str(e) or "TypingOnly" in str(e):
                splash.destroy()
                messagebox.showerror("Critical Error", "Incompatible Environment.\nPlease run using run.bat")
                sys.exit(1)
            raise

        # 6. Launch App
        status_lbl.configure(text="Starting...")
        splash.update()
        time.sleep(0.5) # Small delay to let user see "Starting"
        
        # Stop animation to prevent Tkinter errors
        progress.stop()
        
        # Withdraw first to hide from user
        splash.withdraw()
        
        # Cancel all pending 'after' callbacks to prevent "invalid command name" errors
        try:
            for after_id in splash.tk.call('after', 'info'):
                splash.after_cancel(after_id)
        except Exception:
            pass
            
        splash.update_idletasks() # Finish pending tasks
        
        try:
            splash.destroy()
        except Exception:
            pass # Ignore errors during destruction
        
        app = App()
        app.mainloop()
        
    except Exception as e:
        try:
            splash.destroy()
        except:
            pass
        messagebox.showerror("Startup Error", f"An unexpected error occurred:\n{e}")
        raise

if __name__ == "__main__":
    main()
