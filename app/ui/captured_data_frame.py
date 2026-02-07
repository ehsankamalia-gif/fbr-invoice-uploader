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

        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_chk = ctk.CTkCheckBox(
            self.header_frame,
            text="Select All",
            variable=self.select_all_var,
            command=self.toggle_select_all,
            width=80
        )
        self.select_all_chk.grid(row=0, column=4, padx=5, sticky="e")

        self.delete_btn = ctk.CTkButton(
            self.header_frame,
            text="Delete",
            width=80,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=self.delete_selected
        )
        self.delete_btn.grid(row=0, column=5, padx=5, sticky="e")

        self._search_job = None
        
        self.prev_selection = set()

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
        self.columns = ("check", "id", "name", "father", "cnic", "cell", "chassis", "engine", "model", "color", "date")
        self.tree = ttk.Treeview(
            self.table_frame, 
            columns=self.columns, 
            show="headings", 
            selectmode="extended"
        )

        # Column Headings & Widths
        self.tree.heading("check", text="✔")
        self.tree.column("check", width=30, anchor="center")

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
        
        # Bindings
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

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

    def on_tree_click(self, event):
        """Handle click on checkbox column."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            # check is #1 (first column)
            if column == "#1":
                item = self.tree.identify_row(event.y)
                if item:
                    if item in self.tree.selection():
                        self.tree.selection_remove(item)
                    else:
                        self.tree.selection_add(item)
                    return "break"

    def on_tree_select(self, event):
        """Update checkbox symbols on selection change."""
        current_selection = set(self.tree.selection())
        
        # Update Select All checkbox state based on selection
        all_items = self.tree.get_children()
        if all_items and len(current_selection) == len(all_items):
            self.select_all_var.set(True)
        else:
            self.select_all_var.set(False)

        changed_items = current_selection.symmetric_difference(self.prev_selection)
        
        for item_id in changed_items:
            try:
                values = list(self.tree.item(item_id, "values"))
                if item_id in current_selection:
                    values[0] = "☑"
                else:
                    values[0] = "☐"
                self.tree.item(item_id, values=values)
            except Exception:
                pass
        
        self.prev_selection = current_selection

    def toggle_select_all(self):
        """Select or deselect all items."""
        if self.select_all_var.get():
            # Select All
            self.tree.selection_set(self.tree.get_children())
        else:
            # Deselect All
            self.tree.selection_remove(self.tree.get_children())

    def delete_selected(self):
        """Handle deletion of selected records."""
        logger.info("Delete button clicked.")
        selected_items = self.tree.selection()
        logger.info(f"Selected items: {selected_items}")
        
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select at least one record to delete.")
            return

        # Get IDs of selected items
        ids_to_delete = []
        for item in selected_items:
            values = self.tree.item(item, "values")
            logger.info(f"Item {item} values: {values}")
            if values:
                try:
                    # ID is second column (index 1) because of Checkbox at index 0
                    ids_to_delete.append(int(values[1])) 
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing ID from values {values}: {e}")

        count = len(ids_to_delete)
        logger.info(f"IDs to delete: {ids_to_delete}")
        
        if count == 0:
            messagebox.showwarning("Error", "Could not determine record IDs.")
            return

        # Confirmation Dialog
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete {count} selected record(s)?\n\nThis action will move them to trash.",
            icon="warning"
        )

        if not confirm:
            logger.info("Deletion cancelled by user.")
            return

        # Loading State
        self.configure(cursor="watch")
        self.delete_btn.configure(state="disabled")
        self.update_idletasks()

        try:
            logger.info(f"Calling captured_data_service.delete_records with {ids_to_delete}")
            success, message = captured_data_service.delete_records(ids_to_delete, soft_delete=True)
            logger.info(f"Service returned: success={success}, message={message}")
            
            if success:
                messagebox.showinfo("Success", message)
                # Refresh current page. If empty, go to prev page?
                # For simplicity, just reload current page.
                self.load_data()
            else:
                messagebox.showerror("Error", message)

        except Exception as e:
            logger.error(f"UI Error deleting records: {e}", exc_info=True)
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        
        finally:
            self.configure(cursor="")
            self.delete_btn.configure(state="normal")

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
            
            self.prev_selection = set()
            self.select_all_var.set(False)

            # Populate tree
            for record in result['data']:
                self.tree.insert("", "end", values=(
                    "☐", # Checkbox
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
