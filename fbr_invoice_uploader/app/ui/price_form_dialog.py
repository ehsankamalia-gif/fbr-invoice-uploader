import customtkinter as ctk
from tkinter import messagebox

class PriceFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, price_service, price_data=None, on_save=None):
        super().__init__(parent)
        self.price_service = price_service
        self.price_data = price_data
        self.on_save = on_save
        self.original_model = price_data.product_model.model_name if price_data else None

        self.title("Edit Price" if price_data else "Add New Price")
        self.geometry("450x550")
        self.resizable(False, False)
        
        # Modal
        self.transient(parent)
        self.grab_set()

        # Layout
        self.grid_columnconfigure(1, weight=1)
        
        # 1. Model
        ctk.CTkLabel(self, text="Model Name:").grid(row=0, column=0, padx=20, pady=10, sticky="e")
        self.model_entry = ctk.CTkEntry(self)
        self.model_entry.grid(row=0, column=1, padx=20, pady=10, sticky="ew")

        # 2. Colors
        ctk.CTkLabel(self, text="Colors:").grid(row=1, column=0, padx=20, pady=10, sticky="e")
        self.colors_entry = ctk.CTkEntry(self, placeholder_text="e.g. Red, Black")
        self.colors_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # 3. Excl Price
        ctk.CTkLabel(self, text="Retail Price (Excl):").grid(row=2, column=0, padx=20, pady=10, sticky="e")
        self.excl_entry = ctk.CTkEntry(self)
        self.excl_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
        self.excl_entry.bind("<KeyRelease>", self.calculate_totals)

        # 4. Tax (18%)
        ctk.CTkLabel(self, text="Sales Tax (18%):").grid(row=3, column=0, padx=20, pady=10, sticky="e")
        self.tax_entry = ctk.CTkEntry(self)
        self.tax_entry.grid(row=3, column=1, padx=20, pady=10, sticky="ew")
        self.tax_entry.bind("<KeyRelease>", self.update_total_manual)

        # 5. Levy
        ctk.CTkLabel(self, text="N.E.V. Levy:").grid(row=4, column=0, padx=20, pady=10, sticky="e")
        self.levy_entry = ctk.CTkEntry(self)
        self.levy_entry.grid(row=4, column=1, padx=20, pady=10, sticky="ew")
        self.levy_entry.bind("<KeyRelease>", self.update_total_manual)

        # 6. Total (ReadOnly/Calculated)
        ctk.CTkLabel(self, text="Total Price (Incl):").grid(row=5, column=0, padx=20, pady=10, sticky="e")
        self.total_entry = ctk.CTkEntry(self, state="readonly")
        self.total_entry.grid(row=5, column=1, padx=20, pady=10, sticky="ew")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, pady=30)
        
        ctk.CTkButton(btn_frame, text="Save", command=self.save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="gray").pack(side="left", padx=10)

        # Pre-fill if editing
        if self.price_data:
            self.model_entry.insert(0, self.price_data.product_model.model_name)
            colors = ""
            if self.price_data.optional_features and isinstance(self.price_data.optional_features, dict):
                colors = self.price_data.optional_features.get("colors", "")
            self.colors_entry.insert(0, colors)
            self.excl_entry.insert(0, str(self.price_data.base_price))
            self.tax_entry.insert(0, str(self.price_data.tax_amount))
            self.levy_entry.insert(0, str(self.price_data.levy_amount))
            self.update_total_manual() # Calculate total display

    def calculate_totals(self, event=None):
        try:
            excl = float(self.excl_entry.get().replace(',', '') or 0)
            
            # Auto Calc Tax (18%)
            tax = round(excl * 0.18)
            
            # Auto Calc Levy (Approx 1.1% or keep existing if editing?)
            # For new entries, let's default to ~1.12% based on CD70 (1500/134237)
            # Or just let user enter it. Let's try 1.1% as default
            levy = float(self.levy_entry.get().replace(',', '') or 0)
            if not levy and event: # Only auto-fill levy if empty
                levy = round(excl * 0.0112)
            
            total = excl + tax + levy
            
            # Update fields
            current_tax = self.tax_entry.get().replace(',', '')
            if current_tax != str(tax):
                self.tax_entry.delete(0, "end")
                self.tax_entry.insert(0, str(tax))
                
            current_levy = self.levy_entry.get().replace(',', '')
            if current_levy != str(levy) and not current_levy:
                self.levy_entry.delete(0, "end")
                self.levy_entry.insert(0, str(levy))
            
            self.update_total_display(total)
            
        except ValueError:
            pass

    def update_total_manual(self, event=None):
        try:
            excl = float(self.excl_entry.get().replace(',', '') or 0)
            tax = float(self.tax_entry.get().replace(',', '') or 0)
            levy = float(self.levy_entry.get().replace(',', '') or 0)
            self.update_total_display(excl + tax + levy)
        except ValueError:
            pass

    def update_total_display(self, value):
        self.total_entry.configure(state="normal")
        self.total_entry.delete(0, "end")
        self.total_entry.insert(0, f"{value:,.0f}")
        self.total_entry.configure(state="readonly")

    def save(self):
        # Validate
        model = self.model_entry.get()
        if not model:
            messagebox.showerror("Error", "Model Name is required")
            return

        try:
            excl = float(self.excl_entry.get().replace(',', ''))
            tax = float(self.tax_entry.get().replace(',', ''))
            levy = float(self.levy_entry.get().replace(',', ''))
            total = float(self.total_entry.get().replace(',', ''))
            colors = self.colors_entry.get().upper()
            
            if self.price_data:
                # Update existing record
                self.price_service.update_price(
                    price_id=self.price_data.id,
                    model=model,
                    base_price=excl,
                    tax=tax,
                    levy=levy,
                    total=total,
                    optional_features={"colors": colors}
                )
            else:
                # Save via Service (adds new version)
                self.price_service.add_price(
                    model=model,
                    base_price=excl,
                    tax=tax,
                    levy=levy,
                    total=total,
                    optional_features={"colors": colors}
                )
            
            if self.on_save:
                self.on_save()
            
            self.destroy()
            
        except ValueError:
            messagebox.showerror("Error", "Numeric fields must be valid numbers")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
