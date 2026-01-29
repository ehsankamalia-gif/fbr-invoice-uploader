import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os
from app.services.backup_service import backup_service, BackupConfig

class BackupFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Title
        self.grid_rowconfigure(1, weight=0) # Settings
        self.grid_rowconfigure(2, weight=0) # History Label
        self.grid_rowconfigure(3, weight=1) # History List

        # Title
        self.title_label = ctk.CTkLabel(self, text="Backup & Restore", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # --- Settings Section ---
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.settings_frame.grid_columnconfigure(1, weight=1)
        self.settings_frame.grid_columnconfigure(3, weight=1)

        # Enabled Toggle
        self.enabled_var = ctk.BooleanVar(value=backup_service.config.enabled)
        self.enabled_switch = ctk.CTkSwitch(self.settings_frame, text="Enable Scheduled Backups", variable=self.enabled_var, command=self.save_settings)
        self.enabled_switch.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Interval
        ctk.CTkLabel(self.settings_frame, text="Interval:").grid(row=0, column=1, padx=10, sticky="e")
        self.interval_combo = ctk.CTkOptionMenu(self.settings_frame, values=["daily", "weekly", "monthly"], command=self.save_settings)
        self.interval_combo.set(backup_service.config.interval)
        self.interval_combo.grid(row=0, column=2, padx=10, sticky="w")

        # Time
        ctk.CTkLabel(self.settings_frame, text="Time (HH:MM):").grid(row=0, column=3, padx=10, sticky="e")
        self.time_entry = ctk.CTkEntry(self.settings_frame, width=80)
        self.time_entry.insert(0, backup_service.config.time_str)
        self.time_entry.grid(row=0, column=4, padx=10, sticky="w")
        self.time_entry.bind("<FocusOut>", self.save_settings)

        # Retention
        ctk.CTkLabel(self.settings_frame, text="Retention (Days):").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.retention_entry = ctk.CTkEntry(self.settings_frame, width=60)
        self.retention_entry.insert(0, str(backup_service.config.retention_days))
        self.retention_entry.grid(row=1, column=1, padx=10, sticky="w")
        self.retention_entry.bind("<FocusOut>", self.save_settings)

        # Encryption
        self.encrypt_var = ctk.BooleanVar(value=backup_service.config.encrypt)
        self.encrypt_switch = ctk.CTkSwitch(self.settings_frame, text="Encrypt Backups", variable=self.encrypt_var, command=self.save_settings)
        self.encrypt_switch.grid(row=1, column=2, padx=10, sticky="w", columnspan=2)

        # Paths
        ctk.CTkLabel(self.settings_frame, text="Local Path:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.local_path_entry = ctk.CTkEntry(self.settings_frame)
        self.local_path_entry.insert(0, backup_service.config.local_path)
        self.local_path_entry.grid(row=2, column=1, padx=10, sticky="ew", columnspan=3)
        ctk.CTkButton(self.settings_frame, text="Browse", width=80, command=self.browse_local).grid(row=2, column=4, padx=10)

        ctk.CTkLabel(self.settings_frame, text="Cloud/Sync Path:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.cloud_path_entry = ctk.CTkEntry(self.settings_frame)
        self.cloud_path_entry.insert(0, backup_service.config.cloud_path)
        self.cloud_path_entry.grid(row=3, column=1, padx=10, sticky="ew", columnspan=3)
        ctk.CTkButton(self.settings_frame, text="Browse", width=80, command=self.browse_cloud).grid(row=3, column=4, padx=10)

        # Actions
        self.action_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.action_frame.grid(row=4, column=0, columnspan=5, pady=20)

        self.backup_btn = ctk.CTkButton(self.action_frame, text="Backup Now", width=150, height=35,
                                      command=self.create_manual_backup, fg_color="green", hover_color="darkgreen",
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.backup_btn.pack(side="left", padx=10)

        ctk.CTkLabel(self.action_frame, text="Auto-saves on change", text_color="gray").pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(self.action_frame, text="", text_color="gray")
        self.status_label.pack(side="right", padx=10)

        # --- History Section ---
        self.history_label = ctk.CTkLabel(self, text="Backup History", font=ctk.CTkFont(size=18, weight="bold"))
        self.history_label.grid(row=2, column=0, padx=20, pady=(20, 5), sticky="w")

        self.history_frame = ctk.CTkScrollableFrame(self)
        self.history_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.history_frame.grid_columnconfigure(0, weight=1)

        self.refresh_history()

    def browse_local(self):
        path = filedialog.askdirectory()
        if path:
            self.local_path_entry.delete(0, "end")
            self.local_path_entry.insert(0, path)
            self.save_settings()

    def browse_cloud(self):
        path = filedialog.askdirectory()
        if path:
            self.cloud_path_entry.delete(0, "end")
            self.cloud_path_entry.insert(0, path)
            self.save_settings()

    def save_settings(self, event=None):
        try:
            config = backup_service.config
            config.enabled = self.enabled_var.get()
            config.interval = self.interval_combo.get()
            config.time_str = self.time_entry.get()
            config.local_path = self.local_path_entry.get()
            config.cloud_path = self.cloud_path_entry.get()
            config.retention_days = int(self.retention_entry.get())
            config.encrypt = self.encrypt_var.get()
            
            backup_service.save_config()
            
            if config.enabled:
                backup_service.start_scheduler()
            else:
                backup_service.stop_scheduler()
                
        except Exception as e:
            messagebox.showerror("Error", f"Invalid settings: {e}")

    def create_manual_backup(self):
        self.backup_btn.configure(state="disabled", text="Backing up...")
        self.status_label.configure(text="Backing up...", text_color="gray")
        
        def run():
            res = backup_service.create_backup(is_manual=True)
            self.after(0, lambda: self.finish_backup(res))
            
        threading.Thread(target=run, daemon=True).start()

    def finish_backup(self, res):
        self.backup_btn.configure(state="normal", text="Backup Now")
        if res["success"]:
            self.status_label.configure(text="Backup successful", text_color="green")
            self.after(5000, lambda: self.status_label.configure(text=""))
            messagebox.showinfo("Success", res["message"], parent=self.winfo_toplevel())
            self.refresh_history()
        else:
            self.status_label.configure(text="Backup failed", text_color="red")
            self.after(5000, lambda: self.status_label.configure(text=""))
            messagebox.showerror("Error", res["message"], parent=self.winfo_toplevel())

    def refresh_history(self):
        # Clear old widgets
        for widget in self.history_frame.winfo_children():
            widget.destroy()

        backups = backup_service.list_backups()
        
        if not backups:
            ctk.CTkLabel(self.history_frame, text="No backups found.").pack(pady=20)
            return

        for idx, backup in enumerate(backups):
            row = ctk.CTkFrame(self.history_frame)
            row.pack(fill="x", padx=5, pady=2)
            
            # Icon/Name
            ctk.CTkLabel(row, text="📦").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=backup["name"], font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
            
            # Details
            info = f"{backup['date']} | {backup['size_mb']} MB"
            ctk.CTkLabel(row, text=info, text_color="gray").pack(side="left", padx=10)
            
            # Actions
            ctk.CTkButton(row, text="Restore", width=60, fg_color="orange", hover_color="darkorange",
                          command=lambda p=backup["path"]: self.confirm_restore(p)).pack(side="right", padx=5, pady=5)
            
            ctk.CTkButton(row, text="Delete", width=60, fg_color="red", hover_color="darkred",
                          command=lambda p=backup["path"]: self.delete_backup(p)).pack(side="right", padx=5, pady=5)

    def confirm_restore(self, path):
        if messagebox.askyesno("Confirm Restore", "Restoring will OVERWRITE current data.\nAre you sure?"):
            self.run_restore(path)

    def run_restore(self, path):
        self.status_label.configure(text="Restoring...", text_color="gray")
        def run():
            res = backup_service.restore_backup(path)
            def notify():
                if res.get("success"):
                    self.status_label.configure(text="Restore successful", text_color="green")
                    self.after(5000, lambda: self.status_label.configure(text=""))
                    messagebox.showinfo("Restore", res.get("message", "Restore successful."), parent=self.winfo_toplevel())
                else:
                    self.status_label.configure(text="Restore failed", text_color="red")
                    self.after(5000, lambda: self.status_label.configure(text=""))
                    messagebox.showerror("Restore Failed", res.get("message", "Restore failed."), parent=self.winfo_toplevel())
            self.after(0, notify)
        threading.Thread(target=run, daemon=True).start()

    def delete_backup(self, path):
        if messagebox.askyesno("Confirm Delete", "Delete this backup permanently?"):
            try:
                os.remove(path)
                self.refresh_history()
            except Exception as e:
                messagebox.showerror("Error", str(e))
