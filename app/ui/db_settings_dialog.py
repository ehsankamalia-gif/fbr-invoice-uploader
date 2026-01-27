import customtkinter as ctk
from tkinter import messagebox
from app.services.settings_service import settings_service
from sqlalchemy import create_engine, text
import urllib.parse

class DatabaseSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Database Connection Settings")
        self.geometry("500x500")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()

        # Center window
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.main_frame, text="Database Connection", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Server
        self._add_label("Server Host:", 1)
        self.server_entry = ctk.CTkEntry(self.main_frame)
        self.server_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Port
        self._add_label("Port:", 2)
        self.port_entry = ctk.CTkEntry(self.main_frame)
        self.port_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        # Database Name
        self._add_label("Database Name:", 3)
        self.name_entry = ctk.CTkEntry(self.main_frame)
        self.name_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # User
        self._add_label("User:", 4)
        self.user_entry = ctk.CTkEntry(self.main_frame)
        self.user_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

        # Password
        self._add_label("Password:", 5)
        self.password_entry = ctk.CTkEntry(self.main_frame, show="*")
        self.password_entry.grid(row=5, column=1, padx=10, pady=10, sticky="ew")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=20)

        ctk.CTkButton(btn_frame, text="Save Settings", command=self.save, width=150, height=40).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Close", command=self.destroy, fg_color="gray", width=120, height=40).pack(side="left", padx=10)

        self.load_settings()

    def _add_label(self, text, row):
        ctk.CTkLabel(self.main_frame, text=text, font=ctk.CTkFont(size=14)).grid(row=row, column=0, padx=10, pady=10, sticky="e")

    def load_settings(self):
        settings = settings_service.get_db_settings()
        
        self.server_entry.insert(0, settings.get("server", ""))
        self.port_entry.insert(0, settings.get("port", ""))
        self.name_entry.insert(0, settings.get("name", ""))
        self.user_entry.insert(0, settings.get("user", ""))
        self.password_entry.insert(0, settings.get("password", ""))

    def save(self):
        server = self.server_entry.get().strip()
        port = self.port_entry.get().strip()
        name = self.name_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.password_entry.get().strip()

        if not all([server, port, name, user]):
            messagebox.showerror("Validation Error", "All fields except password are required.")
            return

        # Test Connection before saving
        try:
            encoded_password = urllib.parse.quote_plus(password)
            db_url = f"mysql+pymysql://{user}:{encoded_password}@{server}:{port}/{name}"
            
            # Create a temporary engine with short timeout
            test_engine = create_engine(db_url, connect_args={"connect_timeout": 5})
            
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                
        except Exception as e:
            error_msg = str(e)
            if "1045" in error_msg and "Access denied" in error_msg:
                messagebox.showwarning("Authentication Failed", "Access denied for user. Please check your username and password.")
                return
            elif "2003" in error_msg or "Can't connect" in error_msg:
                 messagebox.showwarning("Connection Failed", "Could not connect to the database server. Please check the Server Host and Port.")
                 return
            elif "1049" in error_msg or "Unknown database" in error_msg:
                 messagebox.showwarning("Database Not Found", f"Unknown database '{name}'. Please check the Database Name.")
                 return
            else:
                messagebox.showerror("Connection Error", f"Failed to connect to database: {e}")
                return

        try:
            settings_service.save_db_settings(server, port, name, user, password)
            messagebox.showinfo("Success", "Database settings saved successfully.\nPlease restart the application for changes to take effect.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
