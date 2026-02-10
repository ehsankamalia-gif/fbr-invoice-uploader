import customtkinter as ctk
from tkinter import messagebox
import re

class PriceFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, price_service, price_data=None, on_save=None):
        super().__init__(parent)
        self.price_service = price_service
        self.price_data = price_data
        self.on_save = on_save
        
        self.title("Price Form")
        self.geometry("500x600")
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Header
        header_text = "Edit Price" if price_data else "Add New Price"
        self.header_label = ctk.CTkLabel(self, text=header_text, font=ctk.CTkFont(size=20, weight="bold"))
        self.header_label.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Fields
        self.create_fields()
        
        # Buttons
        self.create_buttons()
        
        # Populate if editing
        if self.price_data:
            self.populate_fields()

    def create_fields(self):
        # Model
        ctk.CTkLabel(self, text="Model Name:").grid(row=1, column=0, padx=20, pady=10, sticky="e")
        self.model_entry = ctk.CTkEntry(self, width=250)
        self.model_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")
        
        # Colors
        ctk.CTkLabel(self, text="Colors (comma separated):").grid(row=2, column=0, padx=20, pady=10, sticky="e")
        self.colors_entry = ctk.CTkEntry(self, width=250)
        self.colors_entry.grid(row=2, column=1, padx=20, pady=10, sticky="w")
        
        # Base Price (Excl. Tax)
        ctk.CTkLabel(self, text="Base Price (Excl. Tax):").grid(row=3, column=0, padx=20, pady=10, sticky="e")
        self.base_price_entry = ctk.CTkEntry(self, width=250)
        self.base_price_entry.grid(row=3, column=1, padx=20, pady=10, sticky="w")
        self.base_price_entry.bind("<KeyRelease>", self.calculate_tax)
        
        # Sales Tax
        ctk.CTkLabel(self, text="Sales Tax (18%):").grid(row=4, column=0, padx=20, pady=10, sticky="e")
        self.tax_entry = ctk.CTkEntry(self, width=250)
        self.tax_entry.grid(row=4, column=1, padx=20, pady=10, sticky="w")
        self.tax_entry.bind("<KeyRelease>", self.calculate_total)
        
        # Levy
        ctk.CTkLabel(self, text="N.E.V. Levy:").grid(row=5, column=0, padx=20, pady=10, sticky="e")
        self.levy_entry = ctk.CTkEntry(self, width=250)
        self.levy_entry.grid(row=5, column=1, padx=20, pady=10, sticky="w")
        self.levy_entry.insert(0, "0")
        self.levy_entry.bind("<KeyRelease>", self.calculate_total)
        
        # Total Price
        ctk.CTkLabel(self, text="Total Price (Inclusive):").grid(row=6, column=0, padx=20, pady=10, sticky="e")
        self.total_entry = ctk.CTkEntry(self, width=250)
        self.total_entry.grid(row=6, column=1, padx=20, pady=10, sticky="w")
        
    def create_buttons(self):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=7, column=0, columnspan=2, pady=30)
        
        ctk.CTkButton(btn_frame, text="Save", command=self.save, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120, fg_color="gray").pack(side="left", padx=10)
        
    def populate_fields(self):
        # Model
        if self.price_data.product_model:
            self.model_entry.insert(0, self.price_data.product_model.model_name)
            
        # Colors
        if self.price_data.optional_features and isinstance(self.price_data.optional_features, dict):
            colors = self.price_data.optional_features.get("colors", "")
            self.colors_entry.insert(0, colors)
            
        # Prices
        self.base_price_entry.insert(0, str(int(self.price_data.base_price)))
        self.tax_entry.insert(0, str(int(self.price_data.tax_amount)))
        self.levy_entry.delete(0, "end")
        self.levy_entry.insert(0, str(int(self.price_data.levy_amount)))
        self.total_entry.insert(0, str(int(self.price_data.total_price)))
        
    def calculate_tax(self, event=None):
        try:
            base_price = float(self.base_price_entry.get() or 0)
            tax = base_price * 0.18
            
            # Update Tax field
            current_focus = self.focus_get()
            if current_focus != self.tax_entry:
                self.tax_entry.delete(0, "end")
                self.tax_entry.insert(0, f"{tax:.0f}")
                
            self.calculate_total()
        except ValueError:
            pass

    def calculate_total(self, event=None):
        try:
            base_price = float(self.base_price_entry.get() or 0)
            tax = float(self.tax_entry.get() or 0)
            levy = float(self.levy_entry.get() or 0)
            
            total = base_price + tax + levy
            
            # Update Total field
            current_focus = self.focus_get()
            if current_focus != self.total_entry:
                self.total_entry.delete(0, "end")
                self.total_entry.insert(0, f"{total:.0f}")
        except ValueError:
            pass

    def save(self):
        # Validation
        model = self.model_entry.get().strip()
        if not model:
            messagebox.showerror("Error", "Model Name is required")
            return
            
        try:
            base_price = float(self.base_price_entry.get())
            tax = float(self.tax_entry.get())
            levy = float(self.levy_entry.get())
            total = float(self.total_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Prices must be valid numbers")
            return
            
        colors = self.colors_entry.get().strip()
        optional_features = {"colors": colors} if colors else {}
        
        try:
            if self.price_data:
                # Update
                self.price_service.update_price(
                    price_id=self.price_data.id,
                    model=model,
                    base_price=base_price,
                    tax=tax,
                    levy=levy,
                    total=total,
                    optional_features=optional_features
                )
                messagebox.showinfo("Success", "Price updated successfully")
            else:
                # Add
                self.price_service.add_price(
                    model=model,
                    base_price=base_price,
                    tax=tax,
                    levy=levy,
                    total=total,
                    optional_features=optional_features
                )
                messagebox.showinfo("Success", "Price added successfully")
                
            if self.on_save:
                self.on_save()
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save price: {str(e)}")
