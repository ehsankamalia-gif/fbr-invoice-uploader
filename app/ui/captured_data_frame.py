import customtkinter as ctk
from tkinter import messagebox, ttk
import logging
from app.services.captured_data_service import captured_data_service
import math

logger = logging.getLogger(__name__)

class CapturedDataFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # State
        self.current_page = 1
        self.per_page = 20
        self.total_pages = 1
        self.search_query = ""
        self.is_loading = False

        # --- Header ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Captured Data Explorer", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Search Bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)
        self.search_entry = ctk.CTkEntry(
            self.header_frame, 
            textvariable=self.search_var, 
            placeholder_text="Search by Name, CNIC, Chassis...", 
            width=300
        )
        self.search_entry.grid(row=0, column=2, padx=10, sticky="e")
        
        self.refresh_btn = ctk.CTkButton(
            self.header_frame, 
            text="Refresh", 
            width=80, 
            command=self.load_data
        )
        self.refresh_btn.grid(row=0, column=3, padx=5, sticky="e")

        self._search_job = None

        # --- Data Table Area ---
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)

        # Treeview Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=30,
            borderwidth=0
        )
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure(
            "Treeview.Heading",
            background="#333333",
            foreground="white",
            relief="flat",
            font=('Arial', 10, 'bold')
        )
        style.map("Treeview.Heading", background=[('active', '#404040')])

        # Columns
        self.columns = ("id", "name", "father", "cnic", "cell", "chassis", "engine", "model", "color", "date")
        self.tree = ttk.Treeview(
            self.table_frame, 
            columns=self.columns, 
            show="headings", 
            selectmode="browse"
        )

        # Column Headings & Widths
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=50, anchor="center")
        
        self.tree.heading("name", text="Name")
        self.tree.column("name", width=150)
        
        self.tree.heading("father", text="Father Name")
        self.tree.column("father", width=150)
        
        self.tree.heading("cnic", text="CNIC")
        self.tree.column("cnic", width=120)
        
        self.tree.heading("cell", text="Cell No")
        self.tree.column("cell", width=100)
        
        self.tree.heading("chassis", text="Chassis No")
        self.tree.column("chassis", width=120)
        
        self.tree.heading("engine", text="Engine No")
        self.tree.column("engine", width=100)
        
        self.tree.heading("model", text="Model")
        self.tree.column("model", width=80)

        self.tree.heading("color", text="Color")
        self.tree.column("color", width=80)
        
        self.tree.heading("date", text="Date")
        self.tree.column("date", width=120)

        # Scrollbars
        self.vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        # --- Pagination Footer ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.prev_btn = ctk.CTkButton(
            self.footer_frame, 
            text="Previous", 
            width=80, 
            state="disabled",
            command=self.prev_page
        )
        self.prev_btn.pack(side="left", padx=5)

        self.page_label = ctk.CTkLabel(self.footer_frame, text="Page 1 of 1")
        self.page_label.pack(side="left", padx=10)

        self.next_btn = ctk.CTkButton(
            self.footer_frame, 
            text="Next", 
            width=80, 
            state="disabled",
            command=self.next_page
        )
        self.next_btn.pack(side="left", padx=5)

        self.total_label = ctk.CTkLabel(self.footer_frame, text="Total Records: 0", text_color="gray")
        self.total_label.pack(side="right", padx=10)

        # Load initial data
        self.load_data()

    def on_search_change(self, *args):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(500, self.reset_and_load)

    def reset_and_load(self):
        self.current_page = 1
        self.load_data()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_data()

    def load_data(self):
        if self.is_loading:
            return
        
        self.is_loading = True
        self.configure(cursor="watch")
        self.update_idletasks() # Force UI update

        try:
            self.search_query = self.search_var.get().strip()
            
            result = captured_data_service.get_captured_data(
                page=self.current_page,
                per_page=self.per_page,
                search_query=self.search_query
            )

            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Populate tree
            for record in result['data']:
                self.tree.insert("", "end", values=(
                    record.id,
                    record.name or "-",
                    record.father or "-",
                    record.cnic or "-",
                    record.cell or "-",
                    record.chassis_number,
                    record.engine_number or "-",
                    record.model or "-",
                    record.color or "-",
                    record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else "-"
                ))

            # Update pagination info
            self.total_pages = result['total_pages']
            self.total_records = result['total_records']
            
            self.page_label.configure(text=f"Page {self.current_page} of {self.total_pages}")
            self.total_label.configure(text=f"Total Records: {self.total_records}")

            # Update buttons state
            if self.current_page <= 1:
                self.prev_btn.configure(state="disabled")
            else:
                self.prev_btn.configure(state="normal")

            if self.current_page >= self.total_pages:
                self.next_btn.configure(state="disabled")
            else:
                self.next_btn.configure(state="normal")

        except Exception as e:
            logger.error(f"Error loading captured data: {e}")
            messagebox.showerror("Error", f"Failed to load data: {e}")
        finally:
            self.is_loading = False
            self.configure(cursor="")

    def destroy(self):
        # Cleanup
        super().destroy()
