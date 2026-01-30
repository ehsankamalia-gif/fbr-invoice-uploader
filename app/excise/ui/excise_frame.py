import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import threading
from app.excise.db import init_excise_db
from app.excise.services import excise_service
from app.db.session import SessionLocal
from app.excise.models import ExciseOwner, ExciseVehicle, ExciseRegistration

class ExciseFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Initialize DB tables for this module
        init_excise_db()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # --- Header ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        ctk.CTkLabel(self.header_frame, text="Excise & Taxation Module", 
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        ctk.CTkButton(self.header_frame, text="📂 Import Excel Data", 
                      command=self.import_excel,
                      fg_color="#00897B", hover_color="#00695C").pack(side="right")
        
        # --- Stats ---
        self.stats_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.stats_frame.pack(side="right", padx=30)
        
        self.lbl_owners = ctk.CTkLabel(self.stats_frame, text="Owners: 0", font=("Arial", 14, "bold"))
        self.lbl_owners.pack(side="left", padx=15)
        
        self.lbl_vehicles = ctk.CTkLabel(self.stats_frame, text="Vehicles: 0", font=("Arial", 14, "bold"))
        self.lbl_vehicles.pack(side="left", padx=15)
        
        # --- Data Table ---
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.columns = ("reg_no", "chassis", "engine", "owner", "cnic", "tax_upto")
        self.tree = ttk.Treeview(self.tree_frame, columns=self.columns, show="headings", selectmode="browse")
        
        self.tree.heading("reg_no", text="Reg No")
        self.tree.heading("chassis", text="Chassis No")
        self.tree.heading("engine", text="Engine No")
        self.tree.heading("owner", text="Owner Name")
        self.tree.heading("cnic", text="CNIC")
        self.tree.heading("tax_upto", text="Tax Paid Upto")
        
        self.tree.column("reg_no", width=100)
        self.tree.column("chassis", width=150)
        self.tree.column("engine", width=100)
        self.tree.column("owner", width=200)
        self.tree.column("cnic", width=120)
        self.tree.column("tax_upto", width=100)
        
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.refresh_data()

    def import_excel(self):
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel Files", "*.xlsx;*.xls;*.xlsm")]
        )
        
        if not file_path:
            return
            
        # Run in thread to not freeze UI
        threading.Thread(target=self._run_import, args=(file_path,), daemon=True).start()
        
    def _run_import(self, file_path):
        # Disable button or show loading...
        # For simplicity, we just run it
        
        def update_progress(current, total):
            pass # Could update a progress bar here
            
        success, msg = excise_service.import_from_excel(file_path, update_progress)
        
        self.after(0, lambda: self._import_finished(success, msg))
        
    def _import_finished(self, success, msg):
        if success:
            messagebox.showinfo("Import Success", msg)
            self.refresh_data()
        else:
            messagebox.showerror("Import Failed", msg)

    def refresh_data(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        db = SessionLocal()
        try:
            # Join query to get normalized data
            results = db.query(ExciseRegistration).join(ExciseOwner).join(ExciseVehicle).all()
            
            for reg in results:
                self.tree.insert("", "end", values=(
                    reg.registration_number,
                    reg.vehicle.chassis_number,
                    reg.vehicle.engine_number,
                    reg.owner.name,
                    reg.owner.cnic,
                    reg.token_tax_paid_upto or "-"
                ))
            
            # Update stats
            owner_count = db.query(ExciseOwner).count()
            vehicle_count = db.query(ExciseVehicle).count()
            
            self.lbl_owners.configure(text=f"Owners: {owner_count}")
            self.lbl_vehicles.configure(text=f"Vehicles: {vehicle_count}")
            
        except Exception as e:
            print(f"Error loading data: {e}")
        finally:
            db.close()
