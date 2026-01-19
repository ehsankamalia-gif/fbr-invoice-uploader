import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from pathlib import Path
from app.services.form_capture_service import form_capture_service

class CapturedDataFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.json_file = Path("captured_forms.json")
        print(f"CapturedDataFrame looking for file at: {self.json_file.absolute()}")
        self.auto_refresh = True
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Captured Form Data", 
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
        self.search_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="Search url, field or value...", 
                                       textvariable=self.search_var, width=300)
        self.search_entry.pack(side="left", padx=10, pady=10)
        
        self.auto_refresh_switch = ctk.CTkSwitch(self.filter_frame, text="Auto Refresh", command=self.toggle_auto_refresh)
        self.auto_refresh_switch.select()
        self.auto_refresh_switch.pack(side="right", padx=10)

        # Table Frame
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.grid_rowconfigure(3, weight=1) # Give table space
        
        # Treeview
        columns = ("timestamp", "url", "type", "selector", "value")
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
        self.tree.heading("timestamp", text="Time")
        self.tree.heading("url", text="Page URL")
        self.tree.heading("type", text="Type")
        self.tree.heading("selector", text="Field Selector")
        self.tree.heading("value", text="Captured Value")
        
        # Column Widths
        self.tree.column("timestamp", width=150, stretch=False)
        self.tree.column("url", width=300, stretch=True)
        self.tree.column("type", width=100, stretch=False)
        self.tree.column("selector", width=200, stretch=True)
        self.tree.column("value", width=250, stretch=True)
        
        # Styling
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Arial", 11))
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        
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
            self.after(2000, self.start_auto_refresh)

    def load_data(self):
        # Store current selection to restore it (optional, skipped for simplicity)
        
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.all_items = []
        
        if not self.json_file.exists():
             # Silent return for auto-refresh
            return

        try:
            with open(self.json_file, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    return # File might be writing, skip this cycle
                
            pages = data.get("pages", {})
            
            if not pages:
                 # File exists but empty content
                 return
            
            for url, page_data in pages.items():
                fields = page_data.get("fields", {})
                for selector, field_data in fields.items():
                    try:
                        if not isinstance(field_data, dict):
                            continue
                            
                        ts = field_data.get("timestamp", 0)
                        dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        
                        item = (
                            dt_str,
                            url,
                            field_data.get("type", "unknown"),
                            selector,
                            str(field_data.get("value", ""))
                        )
                        self.all_items.append(item)
                    except Exception as e:
                        print(f"Skipping malformed item {selector}: {e}")
            
            # Sort by timestamp desc
            self.all_items.sort(key=lambda x: x[0], reverse=True)
            
            self.filter_data()
            
        except Exception as e:
            print(f"Error loading captured data: {e}")

    def filter_data(self):
        query = self.search_var.get().lower()
        
        # Clear view
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for item in self.all_items:
            # item is tuple: (time, url, type, selector, value)
            match = False
            for col in item:
                if query in str(col).lower():
                    match = True
                    break
            
            if match:
                self.tree.insert("", "end", values=item)

    def clear_data(self):
        if not messagebox.askyesno("Confirm", "Are you sure you want to clear all captured data?"):
            return
            
        try:
            # Use service to clear data (handles both memory and file)
            form_capture_service.clear_session_data()
            self.load_data()
            messagebox.showinfo("Success", "Data cleared.")
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
