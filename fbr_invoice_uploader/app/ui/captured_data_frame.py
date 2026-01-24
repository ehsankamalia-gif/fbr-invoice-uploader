import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from pathlib import Path
from app.services.form_capture_service import form_capture_service
from app.db.session import SessionLocal
from app.db.models import CapturedData

class CapturedDataFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        self.auto_refresh = True
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Captured Form Data (Database)", 
                                      font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")
        
        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.btn_frame.pack(side="right")
        
        self.refresh_btn = ctk.CTkButton(self.btn_frame, text="Refresh", width=100, command=self.load_data)
        self.refresh_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(self.btn_frame, text="Clear Data", width=100, 
                                     fg_color="#C0392B", hover_color="#E74C3C",
                                     command=self.clear_data)
        self.clear_btn.pack(side="left", padx=5)

        # Credentials Frame
        self.credentials_frame = ctk.CTkFrame(self)
        self.credentials_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(self.credentials_frame, text="Dealer Code:").pack(side="left", padx=10)
        self.dealer_code_var = ctk.StringVar()
        self.dealer_code_entry = ctk.CTkEntry(self.credentials_frame, textvariable=self.dealer_code_var, width=150)
        self.dealer_code_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.credentials_frame, text="Password:").pack(side="left", padx=10)
        self.password_var = ctk.StringVar()
        self.password_entry = ctk.CTkEntry(self.credentials_frame, textvariable=self.password_var, show="*", width=150)
        self.password_entry.pack(side="left", padx=5)
        
        self.save_creds_btn = ctk.CTkButton(self.credentials_frame, text="Save Credentials", 
                                          command=self.save_credentials, width=120)
        self.save_creds_btn.pack(side="left", padx=20)
        
        self.load_credentials()

        # Filter Frame
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *args: self.filter_data())
        self.search_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="Search Name, CNIC, Chassis...", 
                                       textvariable=self.search_var, width=300)
        self.search_entry.pack(side="left", padx=10, pady=10)
        
        self.auto_refresh_switch = ctk.CTkSwitch(self.filter_frame, text="Auto Refresh", command=self.toggle_auto_refresh)
        self.auto_refresh_switch.select()
        self.auto_refresh_switch.pack(side="right", padx=10)

        # Table Frame
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Treeview
        # New Columns based on CapturedData model
        columns = ("created_at", "name", "father", "cnic", "cell", "address", "chassis", "engine", "model", "color")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Grid layout for table and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
        
        # Column Headings
        self.tree.heading("created_at", text="Date/Time")
        self.tree.heading("name", text="Name")
        self.tree.heading("father", text="Father Name")
        self.tree.heading("cnic", text="CNIC")
        self.tree.heading("cell", text="Mobile")
        self.tree.heading("address", text="Address")
        self.tree.heading("chassis", text="Chassis No")
        self.tree.heading("engine", text="Engine No")
        self.tree.heading("model", text="Model")
        self.tree.heading("color", text="Color")
        
        # Column Widths
        self.tree.column("created_at", width=140, stretch=False)
        self.tree.column("name", width=150, stretch=True)
        self.tree.column("father", width=150, stretch=True)
        self.tree.column("cnic", width=120, stretch=False)
        self.tree.column("cell", width=100, stretch=False)
        self.tree.column("address", width=200, stretch=True)
        self.tree.column("chassis", width=120, stretch=False)
        self.tree.column("engine", width=100, stretch=False)
        self.tree.column("model", width=80, stretch=False)
        self.tree.column("color", width=80, stretch=False)
        
        # Styling
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        
        # Load initial data
        self.all_items = []
        self.load_data()
        self.start_auto_refresh()

    def toggle_auto_refresh(self):
        self.auto_refresh = bool(self.auto_refresh_switch.get())
        if self.auto_refresh:
            self.start_auto_refresh()

    def ensure_visible(self, event):
        try:
            focus_item = self.tree.focus()
            if focus_item:
                self.tree.see(focus_item)
        except Exception:
            pass

    def start_auto_refresh(self):
        if self.auto_refresh and self.winfo_exists():
            self.load_data()
            self.after(5000, self.start_auto_refresh) # 5 seconds refresh for DB

    def load_data(self):
        # Clear existing tree view items (visual only)
        # We will re-populate self.all_items and then filter
        
        try:
            db = SessionLocal()
            records = db.query(CapturedData).order_by(CapturedData.created_at.desc()).all()
            
            self.all_items = []
            
            for r in records:
                # Format datetime
                dt_str = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
                
                item = (
                    dt_str,
                    r.name or "",
                    r.father or "",
                    r.cnic or "",
                    r.cell or "",
                    r.address or "",
                    r.chassis_number or "",
                    r.engine_number or "",
                    r.model or "",
                    r.color or ""
                )
                self.all_items.append(item)
            
            db.close()
            
            self.filter_data()
            
        except Exception as e:
            print(f"Error loading captured data from DB: {e}")

    def filter_data(self):
        query = self.search_var.get().lower()
        
        # Clear view
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for item in self.all_items:
            # item is tuple
            match = False
            if not query:
                match = True
            else:
                for col in item:
                    if query in str(col).lower():
                        match = True
                        break
            
            if match:
                self.tree.insert("", "end", values=item)

    def clear_data(self):
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete ALL captured data from the database? This cannot be undone."):
            return
            
        try:
            db = SessionLocal()
            num_deleted = db.query(CapturedData).delete()
            db.commit()
            db.close()
            
            # Also clear legacy file if exists
            try:
                form_capture_service.clear_session_data()
            except:
                pass
                
            self.load_data()
            messagebox.showinfo("Success", f"Deleted {num_deleted} records.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear data: {e}")


    def load_credentials(self):
        try:
            config_path = Path("capture_config.json")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    login_config = config.get("login_config", {})
                    self.dealer_code_var.set(login_config.get("dealer_code", ""))
                    self.password_var.set(login_config.get("password", ""))
        except Exception as e:
            print(f"Error loading credentials: {e}")

    def save_credentials(self):
        try:
            config_path = Path("capture_config.json")
            config = {}
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            
            if "login_config" not in config:
                config["login_config"] = {}
                
            config["login_config"]["dealer_code"] = self.dealer_code_var.get()
            config["login_config"]["password"] = self.password_var.get()
            
            # Default selectors if missing
            if "username_selector" not in config["login_config"]:
                config["login_config"]["username_selector"] = "#txt_dealer_code"
            if "password_selector" not in config["login_config"]:
                config["login_config"]["password_selector"] = "#txt_password"
            if "submit_selector" not in config["login_config"]:
                config["login_config"]["submit_selector"] = "#btn_login"
                
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            # Reload config in service
            form_capture_service.load_config()
            
            messagebox.showinfo("Success", "Credentials saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save credentials: {e}")
