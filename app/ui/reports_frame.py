import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import csv
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models import Invoice, Motorcycle, Customer, ProductModel, InvoiceItem
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app.services.print_service import print_service
from app.ui.calendar_dialog import CalendarDialog

class ReportsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        self.title = ctk.CTkLabel(self.header_frame, text="Reports & Analytics", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(self.header_frame, text="Refresh Data", command=self.load_data)
        self.refresh_btn.pack(side="right")
        
        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_sales = self.tabview.add("Sales Report")
        self.tab_inventory = self.tabview.add("Inventory Report")
        
        # Configure Tabs
        self.setup_sales_tab()
        self.setup_inventory_tab()
        
        # Initial Load
        self.load_data()

    def setup_sales_tab(self):
        self.tab_sales.grid_columnconfigure(0, weight=1)
        self.tab_sales.grid_rowconfigure(0, weight=0) # Controls row
        self.tab_sales.grid_rowconfigure(1, weight=1) # Table row
        
        # Controls
        self.sales_controls = ctk.CTkFrame(self.tab_sales, fg_color="transparent")
        self.sales_controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Filters
        ctk.CTkLabel(self.sales_controls, text="Search:").pack(side="left", padx=(0, 5))
        self.sales_search = ctk.CTkEntry(self.sales_controls, width=300, placeholder_text="Inv #, Buyer, Chassis or Engine")
        self.sales_search.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.sales_controls, text="Status:").pack(side="left", padx=(10, 5))
        self.sales_status_var = ctk.StringVar(value="All")
        self.sales_status_combo = ctk.CTkComboBox(self.sales_controls, values=["All", "Synced", "Pending"], variable=self.sales_status_var, width=120)
        self.sales_status_combo.pack(side="left", padx=5)

        # Period Filter
        ctk.CTkLabel(self.sales_controls, text="Period:").pack(side="left", padx=(10, 5))
        self.sales_period_var = ctk.StringVar(value="All Time")
        self.sales_period_combo = ctk.CTkComboBox(self.sales_controls, values=["All Time", "Today", "This Month", "Custom"], variable=self.sales_period_var, width=120, command=self.toggle_date_inputs)
        self.sales_period_combo.pack(side="left", padx=5)
        
        self.date_frame = ctk.CTkFrame(self.sales_controls, fg_color="transparent")
        self.date_frame.pack(side="left", padx=0) # Hidden initially by toggle_date_inputs logic
        
        self.start_date_entry = ctk.CTkEntry(self.date_frame, width=100, placeholder_text="YYYY-MM-DD")
        self.start_date_entry.pack(side="left", padx=2)
        
        # Calendar Button for Start Date
        ctk.CTkButton(self.date_frame, text="📅", width=30, command=lambda: self.open_calendar(self.start_date_entry)).pack(side="left", padx=(0, 5))
        
        self.end_date_entry = ctk.CTkEntry(self.date_frame, width=100, placeholder_text="YYYY-MM-DD")
        self.end_date_entry.pack(side="left", padx=2)
        
        # Calendar Button for End Date
        ctk.CTkButton(self.date_frame, text="📅", width=30, command=lambda: self.open_calendar(self.end_date_entry)).pack(side="left", padx=(0, 5))
        
        self.filter_sales_btn = ctk.CTkButton(self.sales_controls, text="Filter", width=80, command=self.load_sales)
        self.filter_sales_btn.pack(side="left", padx=10)

        # Initial Toggle
        self.toggle_date_inputs("All Time")

        self.export_sales_btn = ctk.CTkButton(self.sales_controls, text="Export CSV", command=self.export_sales)
        self.export_sales_btn.pack(side="right")
        
        self.print_sales_btn = ctk.CTkButton(self.sales_controls, text="Print Invoice", fg_color="green", hover_color="darkgreen", command=self.print_selected_invoice)
        self.print_sales_btn.pack(side="right", padx=10)
        
        # Table Frame
        self.sales_table_frame = ctk.CTkFrame(self.tab_sales)
        self.sales_table_frame.grid(row=1, column=0, sticky="nsew")
        
        # Treeview Scrollbars
        v_scroll = ttk.Scrollbar(self.sales_table_frame)
        v_scroll.pack(side="right", fill="y")
        
        # Treeview
        columns = ("date", "inv_num", "buyer", "chassis", "engine", "total", "status")
        self.sales_tree = ttk.Treeview(self.sales_table_frame, columns=columns, show="headings", yscrollcommand=v_scroll.set)
        
        self.sales_tree.heading("date", text="Date")
        self.sales_tree.heading("inv_num", text="Invoice #")
        self.sales_tree.heading("buyer", text="Buyer")
        self.sales_tree.heading("chassis", text="Chassis Number")
        self.sales_tree.heading("engine", text="Engine Number")
        self.sales_tree.heading("total", text="Total")
        self.sales_tree.heading("status", text="FBR Status")
        
        self.sales_tree.column("date", width=120)
        self.sales_tree.column("inv_num", width=100)
        self.sales_tree.column("buyer", width=150)
        self.sales_tree.column("chassis", width=120)
        self.sales_tree.column("engine", width=120)
        self.sales_tree.column("total", width=100)
        self.sales_tree.column("status", width=80)
        
        self.sales_tree.pack(side="left", fill="both", expand=True)
        v_scroll.config(command=self.sales_tree.yview)
        # Bind double click
        self.sales_tree.bind("<Double-1>", self.show_sales_detail)

    def setup_inventory_tab(self):
        self.tab_inventory.grid_columnconfigure(0, weight=1)
        self.tab_inventory.grid_rowconfigure(0, weight=0) # Controls row
        self.tab_inventory.grid_rowconfigure(1, weight=1) # Table row
        
        # Controls
        self.inv_controls = ctk.CTkFrame(self.tab_inventory, fg_color="transparent")
        self.inv_controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Filters
        ctk.CTkLabel(self.inv_controls, text="Search:").pack(side="left", padx=(0, 5))
        self.inv_search = ctk.CTkEntry(self.inv_controls, width=200, placeholder_text="Chassis, Engine or Model")
        self.inv_search.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.inv_controls, text="Status:").pack(side="left", padx=(10, 5))
        self.inv_status_var = ctk.StringVar(value="All")
        self.inv_status_combo = ctk.CTkComboBox(self.inv_controls, values=["All", "IN_STOCK", "SOLD"], variable=self.inv_status_var, width=120)
        self.inv_status_combo.pack(side="left", padx=5)
        
        self.filter_inv_btn = ctk.CTkButton(self.inv_controls, text="Filter", width=80, command=self.load_inventory)
        self.filter_inv_btn.pack(side="left", padx=5)

        self.export_inv_btn = ctk.CTkButton(self.inv_controls, text="Export CSV", command=self.export_inventory)
        self.export_inv_btn.pack(side="right")
        
        # Table Frame
        self.inv_table_frame = ctk.CTkFrame(self.tab_inventory)
        self.inv_table_frame.grid(row=1, column=0, sticky="nsew")
        
        # Treeview Scrollbars
        v_scroll = ttk.Scrollbar(self.inv_table_frame)
        v_scroll.pack(side="right", fill="y")
        
        # Treeview
        columns = ("chassis", "engine", "model", "color", "status")
        self.inv_tree = ttk.Treeview(self.inv_table_frame, columns=columns, show="headings", yscrollcommand=v_scroll.set)
        
        self.inv_tree.heading("chassis", text="Chassis Number")
        self.inv_tree.heading("engine", text="Engine Number")
        self.inv_tree.heading("model", text="Model")
        self.inv_tree.heading("color", text="Color")
        self.inv_tree.heading("status", text="Status")
        
        self.inv_tree.column("chassis", width=150)
        self.inv_tree.column("engine", width=150)
        self.inv_tree.column("model", width=100)
        self.inv_tree.column("color", width=100)
        self.inv_tree.column("status", width=100)
        
        self.inv_tree.pack(side="left", fill="both", expand=True)
        v_scroll.config(command=self.inv_tree.yview)

    def toggle_date_inputs(self, choice):
        if choice == "Custom":
            self.date_frame.pack(side="left", padx=5, before=self.filter_sales_btn)
        else:
            self.date_frame.pack_forget()

    def open_calendar(self, entry_widget):
        current_text = entry_widget.get().strip()
        current_date = None
        if current_text:
             try:
                 current_date = datetime.strptime(current_text, "%Y-%m-%d")
             except ValueError:
                 pass

        def on_date_select(date_str):
            entry_widget.delete(0, "end")
            entry_widget.insert(0, date_str)
            
        CalendarDialog(self, on_date_select, current_date=current_date)

    def load_data(self):
        self.load_sales()
        self.load_inventory()

    def load_sales(self):
        # Clear existing items
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
            
        db = SessionLocal()
        try:
            query = db.query(Invoice).join(Customer).options(
                joinedload(Invoice.items).joinedload(InvoiceItem.motorcycle)
            ).order_by(Invoice.datetime.desc())
            
            # Apply Filters
            search_text = self.sales_search.get().strip()
            status_filter = self.sales_status_var.get()
            period = self.sales_period_var.get()
            
            # Date Filter
            now = datetime.now()
            start_date = None
            end_date = None
            
            if period == "Today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "This Month":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # End of month
                import calendar
                last_day = calendar.monthrange(now.year, now.month)[1]
                end_date = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
            elif period == "Custom":
                s_str = self.start_date_entry.get().strip()
                e_str = self.end_date_entry.get().strip()
                if s_str:
                    try:
                        start_date = datetime.strptime(s_str, "%Y-%m-%d")
                    except ValueError:
                        pass
                if e_str:
                    try:
                        end_date = datetime.strptime(e_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                    except ValueError:
                        pass

            if start_date:
                query = query.filter(Invoice.datetime >= start_date)
            if end_date:
                query = query.filter(Invoice.datetime <= end_date)

            if search_text:
                search = f"%{search_text}%"
                query = query.outerjoin(Invoice.items).outerjoin(InvoiceItem.motorcycle).filter(
                    or_(
                        Invoice.invoice_number.ilike(search),
                        Customer.name.ilike(search),
                        Customer.cnic.ilike(search),
                        Motorcycle.chassis_number.ilike(search),
                        Motorcycle.engine_number.ilike(search)
                    )
                )
                
            if status_filter == "Synced":
                query = query.filter(Invoice.is_fiscalized == True)
            elif status_filter == "Pending":
                query = query.filter(Invoice.is_fiscalized == False)
            
            invoices = query.all()
            
            for inv in invoices:
                date_str = inv.datetime.strftime("%Y-%m-%d %H:%M")
                status = "Synced" if inv.is_fiscalized else "Pending"
                buyer_name = inv.customer.name if inv.customer else "N/A"
                
                # Get chassis and engine numbers
                chassis_list = []
                engine_list = []
                for item in inv.items:
                    if item.motorcycle:
                        chassis_list.append(item.motorcycle.chassis_number or "")
                        engine_list.append(item.motorcycle.engine_number or "")
                
                chassis_str = ", ".join(filter(None, chassis_list))
                engine_str = ", ".join(filter(None, engine_list))
                
                self.sales_tree.insert("", "end", values=(
                    date_str,
                    inv.invoice_number,
                    buyer_name,
                    chassis_str,
                    engine_str,
                    f"{inv.total_amount:,.2f}",
                    status
                ))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sales: {e}")
        finally:
            db.close()

    def load_inventory(self):
        # Clear existing items
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)
            
        db = SessionLocal()
        try:
            query = db.query(Motorcycle).options(joinedload(Motorcycle.product_model))
            
            # Apply Filters
            search_text = self.inv_search.get().strip()
            status_filter = self.inv_status_var.get()
            
            if search_text:
                search = f"%{search_text}%"
                query = query.join(ProductModel).filter(
                    or_(
                        Motorcycle.chassis_number.ilike(search),
                        Motorcycle.engine_number.ilike(search),
                        ProductModel.model_name.ilike(search)
                    )
                )
                
            if status_filter and status_filter != "All":
                query = query.filter(Motorcycle.status == status_filter)
            
            bikes = query.all()
            
            for bike in bikes:
                self.inv_tree.insert("", "end", values=(
                    bike.chassis_number,
                    bike.engine_number,
                    bike.product_model.model_name if bike.product_model else "Unknown",
                    bike.color,
                    bike.status
                ))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory: {e}")
        finally:
            db.close()

    def export_sales(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
            
        db = SessionLocal()
        try:
            invoices = db.query(Invoice).options(
                joinedload(Invoice.customer),
                joinedload(Invoice.items).joinedload(InvoiceItem.motorcycle)
            ).all()
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Invoice No", "Date", "Buyer", "CNIC", "Chassis Number", "Engine Number", "Total Amount", "Tax", "Further Tax", "FBR Status"])
                for inv in invoices:
                    # Get chassis and engine numbers
                    chassis_list = []
                    engine_list = []
                    for item in inv.items:
                        if item.motorcycle:
                            chassis_list.append(item.motorcycle.chassis_number or "")
                            engine_list.append(item.motorcycle.engine_number or "")
                    
                    chassis_str = ", ".join(filter(None, chassis_list))
                    engine_str = ", ".join(filter(None, engine_list))

                    writer.writerow([
                        inv.invoice_number,
                        inv.datetime,
                        inv.customer.name if inv.customer else "",
                        inv.customer.cnic if inv.customer else "",
                        chassis_str,
                        engine_str,
                        inv.total_amount,
                        inv.total_tax_charged,
                        inv.total_further_tax,
                        "Fiscalized" if inv.is_fiscalized else "Pending"
                    ])
            messagebox.showinfo("Success", "Sales report exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
        finally:
            db.close()

    def show_sales_detail(self, event):
        selection = self.sales_tree.selection()
        if not selection:
            return
            
        item = self.sales_tree.item(selection[0])
        # Values are (Date, Invoice #, Buyer, Total, Status)
        inv_num = item['values'][1]
        
        db = SessionLocal()
        try:
            inv = db.query(Invoice).options(
                joinedload(Invoice.customer), 
                joinedload(Invoice.items).joinedload(InvoiceItem.motorcycle).joinedload(Motorcycle.product_model)
            ).filter(Invoice.invoice_number == inv_num).first()
            
            if inv:
                self.open_sales_detail_dialog(inv)
        finally:
            db.close()

    def open_sales_detail_dialog(self, inv):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Invoice Detail: {inv.invoice_number}")
        dialog.geometry("900x700")
        
        # Main Scrollable Frame
        scroll_frame = ctk.CTkScrollableFrame(dialog)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- Customer Info ---
        cust_frame = ctk.CTkFrame(scroll_frame)
        cust_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(cust_frame, text="Customer Information", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        if inv.customer:
            grid_frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
            grid_frame.pack(fill="x", padx=10, pady=5)
            
            fields = [
                ("Name:", inv.customer.name),
                ("CNIC:", inv.customer.cnic),
                ("Phone:", inv.customer.phone),
                ("NTN:", inv.customer.ntn),
                ("Type:", inv.customer.type),
                ("Address:", inv.customer.address)
            ]
            
            for i, (label, value) in enumerate(fields):
                row = i // 2
                col = (i % 2) * 2
                ctk.CTkLabel(grid_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=row, column=col, sticky="w", padx=5, pady=2)
                ctk.CTkLabel(grid_frame, text=str(value or "N/A")).grid(row=row, column=col+1, sticky="w", padx=5, pady=2)
        else:
            ctk.CTkLabel(cust_frame, text="No Customer Linked").pack()

        # --- Invoice Info ---
        inv_frame = ctk.CTkFrame(scroll_frame)
        inv_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(inv_frame, text="Invoice Information", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        grid_frame = ctk.CTkFrame(inv_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=5)
        
        fields = [
            ("Invoice #:", inv.invoice_number),
            ("Date:", inv.datetime.strftime("%Y-%m-%d %H:%M:%S")),
            ("POS ID:", inv.pos_id),
            ("USIN:", inv.usin),
            ("Payment Mode:", inv.payment_mode),
            ("Sync Status:", inv.sync_status)
        ]
        
        for i, (label, value) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2
            ctk.CTkLabel(grid_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=row, column=col, sticky="w", padx=5, pady=2)
            ctk.CTkLabel(grid_frame, text=str(value or "N/A")).grid(row=row, column=col+1, sticky="w", padx=5, pady=2)

        # --- Items ---
        items_frame = ctk.CTkFrame(scroll_frame)
        items_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(items_frame, text="Invoice Items", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        # Items Table Header
        header_frame = ctk.CTkFrame(items_frame)
        header_frame.pack(fill="x", padx=5)
        headers = ["Item", "Qty", "Rate", "Value", "Tax", "Total"]
        for col, h in enumerate(headers):
            ctk.CTkLabel(header_frame, text=h, font=ctk.CTkFont(weight="bold"), width=100).grid(row=0, column=col, padx=2)
            
        # Items List
        for item in inv.items:
            row_frame = ctk.CTkFrame(items_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=5, pady=2)
            
            vals = [
                item.item_name,
                f"{item.quantity}",
                f"{item.sale_value/item.quantity if item.quantity else 0:,.2f}", # Approx rate
                f"{item.sale_value:,.2f}",
                f"{item.tax_charged:,.2f}",
                f"{item.total_amount:,.2f}"
            ]
            for col, v in enumerate(vals):
                ctk.CTkLabel(row_frame, text=v, width=100).grid(row=0, column=col, padx=2)
                
        # --- Financial Summary ---
        sum_frame = ctk.CTkFrame(scroll_frame)
        sum_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(sum_frame, text="Financial Summary", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        grid_frame = ctk.CTkFrame(sum_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=5)
        
        fields = [
            ("Total Sale Value:", f"{inv.total_sale_value:,.2f}"),
            ("Total Tax:", f"{inv.total_tax_charged:,.2f}"),
            ("Further Tax:", f"{inv.total_further_tax:,.2f}"),
            ("Discount:", f"{inv.discount:,.2f}"),
            ("Grand Total:", f"{inv.total_amount:,.2f}")
        ]
        
        for i, (label, value) in enumerate(fields):
            ctk.CTkLabel(grid_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=i, column=0, sticky="w", padx=20, pady=2)
            ctk.CTkLabel(grid_frame, text=value).grid(row=i, column=1, sticky="e", padx=20, pady=2)

        # --- FBR Response ---
        if inv.fbr_response_message or inv.fbr_invoice_number:
            fbr_frame = ctk.CTkFrame(scroll_frame)
            fbr_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(fbr_frame, text="FBR Response Details", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
            
            grid_frame = ctk.CTkFrame(fbr_frame, fg_color="transparent")
            grid_frame.pack(fill="x", padx=10, pady=5)
            
            fields = [
                ("FBR Invoice #:", inv.fbr_invoice_number),
                ("Response Code:", inv.fbr_response_code),
                ("Message:", inv.fbr_response_message)
            ]
            
            for i, (label, value) in enumerate(fields):
                ctk.CTkLabel(grid_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=i, column=0, sticky="w", padx=5, pady=2)
                ctk.CTkLabel(grid_frame, text=str(value or "N/A"), wraplength=600).grid(row=i, column=1, sticky="w", padx=5, pady=2)

    def show_inventory_detail(self, event):
        selection = self.inv_tree.selection()
        if not selection:
            return

    def ensure_visible_sales(self, event):
        try:
            focus_item = self.sales_tree.focus()
            if focus_item:
                self.sales_tree.see(focus_item)
        except Exception:
            pass

    def ensure_visible_inv(self, event):
        try:
            focus_item = self.inv_tree.focus()
            if focus_item:
                self.inv_tree.see(focus_item)
        except Exception:
            pass

            
        item = self.inv_tree.item(selection[0])
        # Values are (chassis, engine, model, color, status)
        chassis = item['values'][0]
        
        db = SessionLocal()
        try:
            bike = db.query(Motorcycle).options(
                joinedload(Motorcycle.product_model),
                joinedload(Motorcycle.supplier)
            ).filter(Motorcycle.chassis_number == chassis).first()
            
            if bike:
                self.open_inventory_detail_dialog(bike)
        finally:
            db.close()

    def open_inventory_detail_dialog(self, bike):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Motorcycle Detail: {bike.chassis_number}")
        dialog.geometry("600x500")
        
        # Main Frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="Motorcycle Details", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        
        grid_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=5)
        
        model_name = bike.product_model.model_name if bike.product_model else "Unknown"
        make = bike.product_model.make if bike.product_model else "Honda"
        supplier_name = bike.supplier.name if bike.supplier else "N/A"
        
        fields = [
            ("Make:", make),
            ("Model:", model_name),
            ("Year:", bike.year),
            ("Color:", bike.color),
            ("Chassis Number:", bike.chassis_number),
            ("Engine Number:", bike.engine_number),
            ("VIN:", bike.vin),
            ("Status:", bike.status),
            ("Cost Price:", f"{bike.cost_price:,.2f}"),
            ("Sale Price:", f"{bike.sale_price:,.2f}"),
            ("Supplier:", supplier_name),
            ("Purchase Date:", bike.purchase_date.strftime("%Y-%m-%d") if bike.purchase_date else "N/A")
        ]
        
        for i, (label, value) in enumerate(fields):
            ctk.CTkLabel(grid_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(grid_frame, text=str(value or "N/A")).grid(row=i, column=1, sticky="w", padx=10, pady=5)


    def print_selected_invoice(self):
        selection = self.sales_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an invoice to print.")
            return
            
        item = self.sales_tree.item(selection[0])
        # Values are (Date, Invoice #, Buyer, Total, Status)
        invoice_number = str(item['values'][1]) 
        
        db = SessionLocal()
        try:
            invoice = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).options(
                joinedload(Invoice.customer),
                joinedload(Invoice.items).joinedload(InvoiceItem.motorcycle).joinedload(Motorcycle.product_model)
            ).first()
            
            if not invoice:
                messagebox.showerror("Error", "Invoice not found in database.")
                return
                
            success, message = print_service.print_invoice(invoice)
            if not success:
                messagebox.showerror("Error", f"Failed to print invoice: {message}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Print error: {e}")
        finally:
            db.close()


    def export_inventory(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
            
        db = SessionLocal()
        try:
            bikes = db.query(Motorcycle).options(joinedload(Motorcycle.product_model)).all()
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Chassis", "Engine", "Make", "Model", "Year", "Color", "Cost", "Price", "Status"])
                for bike in bikes:
                    model_name = bike.product_model.model_name if bike.product_model else "Unknown"
                    make = bike.product_model.make if bike.product_model else "Honda"
                    writer.writerow([
                        bike.chassis_number,
                        bike.engine_number,
                        make,
                        model_name,
                        bike.year,
                        bike.color,
                        bike.cost_price,
                        bike.sale_price,
                        bike.status
                    ])
            messagebox.showinfo("Success", "Inventory report exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
        finally:
            db.close()
