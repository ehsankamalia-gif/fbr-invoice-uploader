import customtkinter as ctk
from tkinter import ttk, messagebox
import re
from app.services.price_service import price_service
from app.ui.price_form_dialog import PriceFormDialog

class PriceListDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Honda Motorcycle Price List")
        self.geometry("1000x600")
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        # Configure Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        ctk.CTkLabel(header_frame, text="Honda Motorcycle Retail Price List", 
                   font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        ctk.CTkLabel(header_frame, text="(All Prices in PKR)", 
                   font=ctk.CTkFont(size=12)).pack(side="right", anchor="s")

        # Treeview Frame
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Treeview Style
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Price.Treeview", 
                        background="#2b2b2b", 
                        foreground="white", 
                        fieldbackground="#2b2b2b", 
                        rowheight=30,
                        font=("Arial", 11))
        style.configure("Price.Treeview.Heading", 
                        background="#1f538d", 
                        foreground="white", 
                        font=("Arial", 11, "bold"))
        style.map('Price.Treeview', background=[('selected', '#1f538d')])
        
        # Columns
        columns = ("model", "colors", "excl", "tax", "levy", "incl")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", style="Price.Treeview")
        
        # Headings
        self.tree.heading("model", text="Model")
        self.tree.heading("colors", text="Colors")
        self.tree.heading("excl", text="Retail Price (Excl. Tax)")
        self.tree.heading("tax", text="Sales Tax (@ 18%)")
        self.tree.heading("levy", text="N.E.V. Levy")
        self.tree.heading("incl", text="Retail Price (Inclusive)")
        
        # Column Config
        self.tree.column("model", width=150)
        self.tree.column("colors", width=150)
        self.tree.column("excl", width=120, anchor="e")
        self.tree.column("tax", width=120, anchor="e")
        self.tree.column("levy", width=100, anchor="e")
        self.tree.column("incl", width=120, anchor="e")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_price)
        
        # Action Buttons
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=2, column=0, pady=20, sticky="ew", padx=20)

        ctk.CTkButton(action_frame, text="Add New Price", command=self.add_price, width=150, fg_color="#2ecc71", hover_color="#27ae60").pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Edit Selected", command=self.edit_price, width=150, fg_color="#3498db", hover_color="#2980b9").pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Delete Selected", command=self.delete_price, width=150, fg_color="#e74c3c", hover_color="#c0392b").pack(side="left", padx=5)
        
        ctk.CTkButton(action_frame, text="Close", command=self.destroy, width=100, fg_color="gray").pack(side="right")

        # Populate Data
        self.load_data()

    def load_data(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)

    def ensure_visible(self, event):
        try:
            focus_item = self.tree.focus()
            if focus_item:
                self.tree.see(focus_item)
        except Exception:
            pass
            
        # Load from service
        for p in price_service.get_all_active_prices():
            colors = ""
            if p.optional_features and isinstance(p.optional_features, dict):
                colors = p.optional_features.get("colors", "")
            
            # Clean model name for display (remove Red, Special, Std)
            model_name = p.product_model.model_name if p.product_model else "Unknown"
            display_model = re.sub(r'\s*\((Red|Special|Std)\)', '', model_name, flags=re.IGNORECASE).strip()
                
            # Store ID in text attribute for retrieval (Unique Identifier)
            self.tree.insert("", "end", text=str(p.id), values=(
                display_model,
                colors,
                f"{p.base_price:,.2f}",
                f"{p.tax_amount:,.2f}",
                f"{p.levy_amount:,.0f}",
                f"{p.total_price:,.0f}"
            ))

    def get_selected_item(self):
        selection = self.tree.selection()
        if not selection:
            return None
        
        # Get ID from text attribute (hidden ID)
        item = self.tree.item(selection[0])
        try:
            price_id = int(item['text'])
            # Find full object by ID to ensure uniqueness
            return price_service.get_price_by_id(price_id)
        except (ValueError, TypeError):
            return None

    def add_price(self):
        PriceFormDialog(self, price_service, on_save=self.load_data)

    def edit_price(self, event=None):
        item = self.get_selected_item()
        if not item:
            # If triggered by double click but somehow nothing selected (unlikely but safe)
            if event:
                return
            messagebox.showwarning("Warning", "Please select a row to edit")
            return
        PriceFormDialog(self, price_service, price_data=item, on_save=self.load_data)

    def delete_price(self):
        item = self.get_selected_item()
        if not item:
            messagebox.showwarning("Warning", "Please select a row to delete")
            return
            
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete {item.product_model.model_name}?"):
            price_service.delete_price_model(item.product_model.model_name)
            self.load_data()
