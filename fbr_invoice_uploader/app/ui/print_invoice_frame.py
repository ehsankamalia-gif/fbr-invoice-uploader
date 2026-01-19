import customtkinter as ctk
from tkinter import messagebox
from app.services.print_service import print_service
from app.db.session import SessionLocal
from app.db.models import Invoice, Motorcycle, InvoiceItem
from app.services.price_service import price_service
from sqlalchemy.orm import joinedload

from PIL import Image, ImageTk
import os
import json
import tkinter as tk
import base64
from io import BytesIO

class PrintInvoiceFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.drag_data = {"x": 0, "y": 0, "item": None, "key": None}
        self.current_invoice = None
        self.current_item = None
        self.current_chassis = None
        self.load_layout_config()

        self.paper_var = ctk.StringVar()
        self.paper_orientation_var = ctk.StringVar()
        self.paper_width_var = ctk.StringVar()
        self.paper_height_var = ctk.StringVar()
        self.paper_unit_var = ctk.StringVar()
        self._init_paper_vars()

        self.base_preview_width_px = 600
        self.base_preview_height_px = 850
        self.preview_width_px = self.base_preview_width_px
        self.preview_height_px = self.base_preview_height_px
        
        # Configure Main Grid
        self.grid_columnconfigure(0, weight=0, minsize=400) # Fixed width for input panel
        self.grid_columnconfigure(1, weight=1) # Preview takes remaining space
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL ---
        self.left_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.left_panel.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(1, weight=1)

        # Title
        self.label_title = ctk.CTkLabel(self.left_panel, text="Print Invoice", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_title.grid(row=0, column=0, pady=(0, 20), sticky="w")

        # Gray Card Frame
        self.card_frame = ctk.CTkFrame(self.left_panel, fg_color="#D9D9D9", corner_radius=10) # Light gray background
        self.card_frame.grid(row=1, column=0, sticky="nsew")
        self.card_frame.grid_columnconfigure(0, weight=1)

        # -- Inside Card --
        # Chassis Search
        self.label_chassis = ctk.CTkLabel(self.card_frame, text="Enter Chassis Number:", font=ctk.CTkFont(size=14), text_color="black")
        self.label_chassis.pack(pady=(20, 5), padx=20)
        
        self.chassis_entry = ctk.CTkEntry(self.card_frame, width=250, height=35, fg_color="white", text_color="black", border_color="gray")
        self.chassis_entry.pack(pady=(0, 15), padx=20)
        self.chassis_entry.bind("<Return>", self.on_preview_enter)
        
        self.print_btn = ctk.CTkButton(self.card_frame, text="Print Invoice", command=self.on_print_click, width=200, height=40, fg_color="#3B8ED0", hover_color="#36719F")
        self.print_btn.pack(pady=(0, 20), padx=20)

        # Form Container (Grid)
        self.form_frame = ctk.CTkFrame(self.card_frame, fg_color="transparent")
        self.form_frame.pack(pady=10, padx=20, fill="x")
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Fields
        self.name_var = ctk.StringVar()
        self._create_form_row(0, "Name", self.name_var)
        
        # Father / Relation
        ctk.CTkLabel(self.form_frame, text="Father", font=ctk.CTkFont(size=12), text_color="black").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        
        father_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        father_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.rel_type_var = ctk.StringVar(value="S/O")
        self.rel_menu = ctk.CTkOptionMenu(father_frame, variable=self.rel_type_var, values=["S/O", "D/O", "W/O", "Org"], width=70, command=self.on_rel_change, fg_color="#3B8ED0", button_color="#36719F")
        self.rel_menu.pack(side="left", padx=(0, 5))
        
        self.father_var = ctk.StringVar()
        self.father_entry = ctk.CTkEntry(father_frame, textvariable=self.father_var, height=30, fg_color="white", text_color="black", border_color="gray")
        self.father_entry.pack(side="left", fill="x", expand=True)
        self.father_entry.bind("<KeyRelease>", self.on_input_change)

        self.phone_var = ctk.StringVar()
        self._create_form_row(2, "Phone", self.phone_var)

        self.address_var = ctk.StringVar()
        self._create_form_row(3, "Address", self.address_var)

        # Model (OptionMenu)
        self.model_var = ctk.StringVar()
        ctk.CTkLabel(self.form_frame, text="Model", font=ctk.CTkFont(size=12, weight="bold"), text_color="black").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.model_menu = ctk.CTkOptionMenu(self.form_frame, variable=self.model_var, values=[], command=self.on_model_change, fg_color="#3B8ED0", button_color="#36719F")
        self.model_menu.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Color (OptionMenu)
        self.color_var = ctk.StringVar()
        ctk.CTkLabel(self.form_frame, text="Color", font=ctk.CTkFont(size=12, weight="bold"), text_color="black").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.color_menu = ctk.CTkOptionMenu(self.form_frame, variable=self.color_var, values=[], command=self.on_color_change, fg_color="#3B8ED0", button_color="#36719F")
        self.color_menu.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        # Year Input
        self.year_var = ctk.StringVar()
        self._create_form_row(6, "Model Year", self.year_var)

        self.engine_var = ctk.StringVar()
        self._create_form_row(7, "Engine No", self.engine_var)

        self.amount_var = ctk.StringVar()
        self._create_form_row(8, "Amount", self.amount_var)

        self.sale_tax_var = ctk.StringVar()
        self._create_form_row(9, "Sale Tax", self.sale_tax_var)

        self.other_tax_var = ctk.StringVar()
        self._create_form_row(10, "Other Tax", self.other_tax_var)

        self.total_var = ctk.StringVar()
        self._create_form_row(11, "Total Price", self.total_var)

        # --- RIGHT PANEL (Preview) ---
        self.preview_container = ctk.CTkFrame(self, fg_color="white")
        self.preview_container.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        self.preview_container.grid_rowconfigure(0, weight=1)
        self.preview_container.grid_rowconfigure(1, weight=0)
        self.preview_container.grid_rowconfigure(2, weight=0)
        self.preview_container.grid_columnconfigure(0, weight=1)
        self.preview_container.grid_columnconfigure(1, weight=0)
        
        self.create_preview_panel()

        self.populate_models()

    def _create_form_row(self, row, label_text, variable):
        ctk.CTkLabel(self.form_frame, text=label_text, font=ctk.CTkFont(size=12), text_color="black").grid(row=row, column=0, padx=5, pady=5, sticky="e")
        entry = ctk.CTkEntry(self.form_frame, textvariable=variable, height=30, fg_color="white", text_color="black", border_color="gray")
        entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        
        # Immediate reflection on key release
        entry.bind("<KeyRelease>", self.on_input_change)
        return entry

    def on_input_change(self, event=None):
        """Updates the preview immediately when input fields change"""
        if hasattr(self, 'current_invoice') and self.current_invoice and hasattr(self, 'current_item') and self.current_item:
            self.update_preview_panel(self.current_invoice, self.current_item)
        else:
            # Manual mode preview
            invoice, item = self._create_temp_invoice_from_form()
            self.update_preview_panel(invoice, item)

    def on_rel_change(self, selected):
        # Re-trigger preview update
        if hasattr(self, 'current_invoice') and self.current_invoice and hasattr(self, 'current_item') and self.current_item:
            self.update_preview_panel(self.current_invoice, self.current_item)
        else:
            # Manual mode preview
            invoice, item = self._create_temp_invoice_from_form()
            self.update_preview_panel(invoice, item)

    def _create_temp_invoice_from_form(self):
        """Creates a temporary Invoice and InvoiceItem object from current form data"""
        from types import SimpleNamespace
        from datetime import datetime

        # Create mock objects
        invoice = SimpleNamespace()
        item = SimpleNamespace()
        customer = SimpleNamespace()
        motorcycle = SimpleNamespace()
        product_model = SimpleNamespace()

        # Fill Customer Data
        customer.name = self.name_var.get()
        customer.father_name = self.father_var.get()
        customer.address = self.address_var.get()
        customer.business_name = None 
        customer.phone = self.phone_var.get()
        
        invoice.customer = customer
        
        # Fill Invoice Data
        invoice.invoice_number = "MANUAL"
        invoice.fbr_invoice_number = "" # Not uploaded
        invoice.datetime = datetime.now()
        invoice.items = [item]

        # Fill Item/Motorcycle Data
        item.motorcycle = motorcycle
        item.quantity = 1
        
        # Financials
        try:
            item.sale_value = float(self.amount_var.get().replace(",", "") or 0)
            item.tax_charged = float(self.sale_tax_var.get().replace(",", "") or 0)
            item.further_tax = float(self.other_tax_var.get().replace(",", "") or 0)
            item.total_amount = float(self.total_var.get().replace(",", "") or 0)
            
            if item.sale_value > 0:
                item.tax_rate = (item.tax_charged / item.sale_value) * 100
            else:
                item.tax_rate = 18.0
        except ValueError:
            item.sale_value = 0.0
            item.tax_charged = 0.0
            item.further_tax = 0.0
            item.total_amount = 0.0
            item.tax_rate = 18.0

        motorcycle.chassis_number = self.chassis_entry.get()
        motorcycle.engine_number = self.engine_var.get()
        motorcycle.color = self.color_var.get()
        motorcycle.product_model = product_model
        
        product_model.model_name = self.model_var.get()

        return invoice, item

    def on_preview_enter(self, event=None):
        chassis = self.chassis_entry.get().strip()
        if chassis:
            self.preview_invoice_by_chassis(chassis)

    def on_print_click(self, event=None):
        chassis = self.chassis_entry.get().strip()
        if not chassis:
            messagebox.showwarning("Warning", "Please enter a Chassis Number.")
            return

        self.print_invoice_by_chassis(chassis)

    def _fetch_invoice_and_item(self, db, chassis):
        # Find InvoiceItem with this chassis number via Motorcycle relationship
        # Use joinedload to ensure relationships are available even if detached later
        item = db.query(InvoiceItem).join(Motorcycle).filter(Motorcycle.chassis_number == chassis).options(
            joinedload(InvoiceItem.motorcycle).joinedload(Motorcycle.product_model),
            joinedload(InvoiceItem.invoice).joinedload(Invoice.customer),
            joinedload(InvoiceItem.invoice).joinedload(Invoice.items).joinedload(InvoiceItem.motorcycle).joinedload(Motorcycle.product_model)
        ).first()
        
        if not item:
            # Fallback: Find the motorcycle first
            bike = db.query(Motorcycle).filter(Motorcycle.chassis_number == chassis).first()
            if bike:
                item = db.query(InvoiceItem).filter(InvoiceItem.motorcycle_id == bike.id).options(
                    joinedload(InvoiceItem.motorcycle).joinedload(Motorcycle.product_model),
                    joinedload(InvoiceItem.invoice).joinedload(Invoice.customer),
                    joinedload(InvoiceItem.invoice).joinedload(Invoice.items).joinedload(InvoiceItem.motorcycle).joinedload(Motorcycle.product_model)
                ).first()
        
        if not item:
            # Silent fail for manual entry support
            # messagebox.showerror("Not Found", f"No invoice found for chassis: {chassis}")
            return None, None
            
        invoice = item.invoice
        if not invoice:
                # messagebox.showerror("Error", "Invoice record missing for this item.")
                return None, None
                
        return invoice, item

    def populate_fields(self, invoice, item):
        # Customer Details
        if invoice.customer:
            # Check for business name
            if invoice.customer.business_name:
                self.rel_type_var.set("Org")
                self.name_var.set(invoice.customer.business_name)
                # If org, maybe father name is contact person or just empty?
                # Keeping father name as father name if available, or name if available
                self.father_var.set(invoice.customer.name or "") 
            else:
                self.rel_type_var.set("S/O")
                self.name_var.set(invoice.customer.name or "")
                self.father_var.set(invoice.customer.father_name or "")
            
            self.phone_var.set(invoice.customer.phone or "")
            self.address_var.set(invoice.customer.address or "")
        else:
            self.name_var.set("")
            self.father_var.set("")
            self.phone_var.set("")
            self.address_var.set("")
            self.rel_type_var.set("S/O")

        # Bike Details
        self.model_var.set("")
        self.color_var.set("")
        self.engine_var.set("")
        
        if item.motorcycle:
            if item.motorcycle.product_model:
                self.model_var.set(item.motorcycle.product_model.model_name or "")
            self.color_var.set(item.motorcycle.color or "")
            self.engine_var.set(item.motorcycle.engine_number or "")
        
        # Financials
        self.amount_var.set(f"{item.sale_value:,.2f}")
        self.sale_tax_var.set(f"{item.tax_charged:,.2f}")
        self.other_tax_var.set(f"{item.further_tax:,.2f}")
        self.total_var.set(f"{item.total_amount:,.2f}")

    def load_layout_config(self):
        self.layout_config = {
            "date": {"x": 90, "y": 135},
            "inv_no": {"x": 90, "y": 165},
            "name": {"x": 90, "y": 215},
            "address": {"x": 90, "y": 255},
            "desc": {"x": 280, "y": 400},
            "engine": {"x": 280, "y": 440},
            "chassis": {"x": 280, "y": 480},
            "model": {"x": 280, "y": 520},
            "color": {"x": 280, "y": 560},
            "reg_letter": {"x": 280, "y": 600},
            "item_total": {"x": 460, "y": 400},
            "amount": {"x": 460, "y": 450},
            "sale_tax": {"x": 460, "y": 480},
            "other_tax": {"x": 460, "y": 510},
            "nev_levy_label": {"x": 350, "y": 510},
            "pos_fee_value": {"x": 460, "y": 540},
            "pos_fee_label": {"x": 350, "y": 540},
            "fbr_inv_no": {"x": 90, "y": 185},
            "grand_total": {"x": 460, "y": 710},
            "qr": {"x": 340, "y": 620},
            "tax_rate_label": {"x": 460, "y": 480},
            "paper": {"name": "A4", "orientation": "portrait", "width_mm": 210, "height_mm": 297, "unit": "mm"},
        }
        
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
            config_path = os.path.join(project_root, "assets", "invoice_print_layout.json")
            
            if os.path.exists(config_path):
                # Check if file is empty
                if os.path.getsize(config_path) == 0:
                    print("Layout config file is empty. Using defaults.")
                    return

                with open(config_path, "r") as f:
                    try:
                        saved_config = json.load(f)
                        # Update defaults with saved values
                        for key, val in saved_config.items():
                            if key in self.layout_config:
                                self.layout_config[key].update(val)
                    except json.JSONDecodeError:
                        print("Error decoding layout config (invalid JSON). Using defaults.")
        except Exception as e:
            print(f"Error loading layout config: {e}")

    def _init_paper_vars(self):
        paper = self.layout_config.get("paper") or {}
        name = str(paper.get("name") or "A4")
        orientation = str(paper.get("orientation") or "portrait")
        unit = str(paper.get("unit") or "mm").strip().lower()
        width_mm = self._safe_float(str(paper.get("width_mm", 210)), 210)
        height_mm = self._safe_float(str(paper.get("height_mm", 297)), 297)
        self.paper_var.set(name)
        self.paper_orientation_var.set(orientation)
        self.paper_unit_var.set(unit if unit in set(self._paper_units()) else "mm")
        self.paper_width_var.set(self._format_dimension(self._mm_to_display(width_mm, self.paper_unit_var.get())))
        self.paper_height_var.set(self._format_dimension(self._mm_to_display(height_mm, self.paper_unit_var.get())))

    def _paper_presets(self):
        return {
            "A4": (210, 297),
            "Letter": (216, 279),
            "Legal": (216, 356),
            "A5": (148, 210),
            "Custom": (None, None),
        }

    def _paper_units(self):
        return ["mm", "cm", "inch"]

    def _orientation_presets(self):
        return ["portrait", "landscape"]

    def _save_paper_settings(self):
        unit = str(self.paper_unit_var.get() or "mm").strip().lower()
        if unit not in set(self._paper_units()):
            unit = "mm"
        self.layout_config["paper"] = {
            "name": self.paper_var.get(),
            "orientation": self.paper_orientation_var.get(),
            "width_mm": self._display_to_mm(self.paper_width_var.get(), unit, 210),
            "height_mm": self._display_to_mm(self.paper_height_var.get(), unit, 297),
            "unit": unit,
        }
        self._apply_paper_to_preview()
        self.save_layout_config()

    def _on_paper_change(self, selected: str):
        presets = self._paper_presets()
        width_height = presets.get(selected)
        self.paper_var.set(selected)

        if width_height and width_height[0] is not None and width_height[1] is not None:
            unit = str(self.paper_unit_var.get() or "mm").strip().lower()
            w = self._mm_to_display(float(width_height[0]), unit)
            h = self._mm_to_display(float(width_height[1]), unit)
            self.paper_width_var.set(self._format_dimension(w))
            self.paper_height_var.set(self._format_dimension(h))
            if hasattr(self, "paper_width_entry"):
                self.paper_width_entry.configure(state="disabled")
            if hasattr(self, "paper_height_entry"):
                self.paper_height_entry.configure(state="disabled")
        else:
            if hasattr(self, "paper_width_entry"):
                self.paper_width_entry.configure(state="normal")
            if hasattr(self, "paper_height_entry"):
                self.paper_height_entry.configure(state="normal")

        self._save_paper_settings()

    def _on_paper_unit_change(self, selected: str):
        next_unit = str(selected or "mm").strip().lower()
        if next_unit not in set(self._paper_units()):
            next_unit = "mm"

        paper_cfg = self.layout_config.get("paper") or {}
        prev_unit = str(paper_cfg.get("unit") or "mm").strip().lower()
        if prev_unit not in set(self._paper_units()):
            prev_unit = "mm"

        saved_width_mm = self._safe_float(str(paper_cfg.get("width_mm", 210)), 210)
        saved_height_mm = self._safe_float(str(paper_cfg.get("height_mm", 297)), 297)
        width_mm = self._display_to_mm(self.paper_width_var.get(), prev_unit, saved_width_mm)
        height_mm = self._display_to_mm(self.paper_height_var.get(), prev_unit, saved_height_mm)

        self.paper_unit_var.set(next_unit)
        self.paper_width_var.set(self._format_dimension(self._mm_to_display(width_mm, next_unit)))
        self.paper_height_var.set(self._format_dimension(self._mm_to_display(height_mm, next_unit)))

        self.layout_config["paper"] = {
            "name": self.paper_var.get(),
            "orientation": self.paper_orientation_var.get(),
            "width_mm": float(width_mm),
            "height_mm": float(height_mm),
            "unit": next_unit,
        }
        self._apply_paper_to_preview()
        self.save_layout_config()

    def _on_orientation_change(self, selected: str):
        self.paper_orientation_var.set(selected)
        self._save_paper_settings()

    def _safe_float(self, value: str, default: float) -> float:
        try:
            return float(str(value).strip())
        except Exception:
            return float(default)

    def _unit_factor_mm(self, unit: str) -> float:
        u = str(unit or "mm").strip().lower()
        if u == "cm":
            return 10.0
        if u == "inch":
            return 25.4
        return 1.0

    def _display_to_mm(self, value: str, unit: str, default_mm: float) -> float:
        v = self._safe_float(value, default_mm)
        factor = self._unit_factor_mm(unit)
        return float(v) * float(factor)

    def _mm_to_display(self, mm: float, unit: str) -> float:
        factor = self._unit_factor_mm(unit)
        if factor == 0:
            return float(mm)
        return float(mm) / float(factor)

    def _format_dimension(self, value: float) -> str:
        try:
            v = float(value)
        except Exception:
            return str(value)
        return f"{v:.3f}".rstrip("0").rstrip(".")

    def _get_paper_dimensions_mm(self):
        unit = str(self.paper_unit_var.get() or "mm").strip().lower()
        if unit not in set(self._paper_units()):
            unit = "mm"
        width_mm = self._display_to_mm(self.paper_width_var.get(), unit, 210)
        height_mm = self._display_to_mm(self.paper_height_var.get(), unit, 297)
        if str(self.paper_orientation_var.get()).lower() == "landscape":
            return height_mm, width_mm
        return width_mm, height_mm

    def _apply_paper_to_preview(self):
        width_mm, height_mm = self._get_paper_dimensions_mm()
        if width_mm <= 0 or height_mm <= 0:
            return

        self.preview_width_px = self.base_preview_width_px
        self.preview_height_px = int(round(self.preview_width_px * (height_mm / width_mm)))
        if self.preview_height_px < 200:
            self.preview_height_px = 200

        if not hasattr(self, "canvas"):
            return

        self.canvas.configure(width=self.preview_width_px, height=self.preview_height_px)
        self.canvas.configure(scrollregion=(0, 0, self.preview_width_px, self.preview_height_px))

        scale_x = self.preview_width_px / self.base_preview_width_px
        scale_y = self.preview_height_px / self.base_preview_height_px
        if hasattr(self, "preview_labels"):
            for key, item_id in self.preview_labels.items():
                cfg = self.layout_config.get(key)
                if not cfg:
                    continue
                x_base = float(cfg.get("x", 0))
                y_base = float(cfg.get("y", 0))
                self.canvas.coords(item_id, x_base * scale_x, y_base * scale_y)

    def save_layout_config(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
            assets_dir = os.path.join(project_root, "assets")
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir)
                
            config_path = os.path.join(assets_dir, "invoice_print_layout.json")
            with open(config_path, "w") as f:
                json.dump(self.layout_config, f, indent=4)
        except Exception as e:
            print(f"Error saving layout config: {e}")

    def on_drag_start(self, event):
        """Begin drag of an object"""
        try:
            # Convert window coords to canvas coords
            cx = self.canvas.canvasx(event.x)
            cy = self.canvas.canvasy(event.y)
            
            # SIMPLIFIED ROBUST LOGIC:
            # Always find the geometrically closest item.
            closest = self.canvas.find_closest(cx, cy)
            
            if not closest:
                return
                
            item = closest[0]
            
            # DISTANCE CHECK: Prevent grabbing distant items
            bbox = self.canvas.bbox(item)
            if bbox:
                bx = (bbox[0] + bbox[2]) / 2
                by = (bbox[1] + bbox[3]) / 2
                dist = ((cx - bx)**2 + (cy - by)**2)**0.5
                if dist > 100: # Ignore if > 100px away
                    return

            tags = self.canvas.gettags(item)
            
            # Check if it matches a known key
            target_key = None
            for tag in tags:
                if tag in self.layout_config:
                    target_key = tag
                    break
            
            if target_key:
                self.drag_data["item"] = item
                self.drag_data["x"] = cx
                self.drag_data["y"] = cy
                self.drag_data["key"] = target_key
                self.canvas.configure(cursor="fleur")

        except Exception as e:
            print(f"Drag start error: {e}")

    def on_drag_motion(self, event):
        """Handle dragging of an object"""
        if self.drag_data["item"]:
            # compute how much the mouse has moved
            cx = self.canvas.canvasx(event.x)
            cy = self.canvas.canvasy(event.y)
            
            delta_x = cx - self.drag_data["x"]
            delta_y = cy - self.drag_data["y"]
            
            # move the object the appropriate amount
            self.canvas.move(self.drag_data["item"], delta_x, delta_y)
            
            # record the new position
            self.drag_data["x"] = cx
            self.drag_data["y"] = cy

    def on_drag_stop(self, event):
        """End drag of an object"""
        if self.drag_data["item"] and self.drag_data["key"]:
            # Get final coordinates
            coords = self.canvas.coords(self.drag_data["item"])
            if coords:
                scale_x = self.preview_width_px / self.base_preview_width_px
                scale_y = self.preview_height_px / self.base_preview_height_px
                if scale_x == 0:
                    scale_x = 1
                if scale_y == 0:
                    scale_y = 1
                self.layout_config[self.drag_data["key"]]["x"] = coords[0] / scale_x
                self.layout_config[self.drag_data["key"]]["y"] = coords[1] / scale_y
                self.save_layout_config()
                
            self.drag_data["item"] = None
            self.drag_data["key"] = None
            self.canvas.configure(cursor="")

    def create_preview_panel(self):
        self.bg_photo = None
        width, height = self.preview_width_px, self.preview_height_px

        # Create Canvas for true transparency and layering
        # Red border added as requested
        self.canvas = tk.Canvas(
            self.preview_container, 
            width=width, 
            height=height, 
            bg="white", 
            highlightthickness=4, 
            highlightbackground="red", 
            highlightcolor="red",
            relief="flat"
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Add Scrollbars
        self.v_scroll = ctk.CTkScrollbar(self.preview_container, orientation="vertical", command=self.canvas.yview)
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        
        self.h_scroll = ctk.CTkScrollbar(self.preview_container, orientation="horizontal", command=self.canvas.xview)
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        # Configure scroll region
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.configure(scrollregion=(0, 0, width, height))

        self.preview_actions = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        self.preview_actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        self.preview_actions.grid_columnconfigure(0, weight=0)
        self.preview_actions.grid_columnconfigure(1, weight=0)
        self.preview_actions.grid_columnconfigure(2, weight=0)
        self.preview_actions.grid_columnconfigure(3, weight=0)
        self.preview_actions.grid_columnconfigure(4, weight=0)
        self.preview_actions.grid_columnconfigure(5, weight=0)
        self.preview_actions.grid_columnconfigure(6, weight=1)

        self.paper_label = ctk.CTkLabel(self.preview_actions, text="Paper", text_color="black")
        self.paper_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        paper_options = list(self._paper_presets().keys())
        self.paper_menu = ctk.CTkOptionMenu(
            self.preview_actions,
            variable=self.paper_var,
            values=paper_options,
            command=self._on_paper_change,
            fg_color="#3B8ED0",
            button_color="#36719F",
        )
        self.paper_menu.grid(row=0, column=1, sticky="w", padx=(0, 10))

        self.orientation_menu = ctk.CTkOptionMenu(
            self.preview_actions,
            variable=self.paper_orientation_var,
            values=self._orientation_presets(),
            command=self._on_orientation_change,
            fg_color="#3B8ED0",
            button_color="#36719F",
        )
        self.orientation_menu.grid(row=0, column=2, sticky="w", padx=(0, 10))

        self.paper_width_entry = ctk.CTkEntry(self.preview_actions, width=70, textvariable=self.paper_width_var)
        self.paper_width_entry.grid(row=0, column=3, sticky="w", padx=(0, 6))
        self.paper_height_entry = ctk.CTkEntry(self.preview_actions, width=70, textvariable=self.paper_height_var)
        self.paper_height_entry.grid(row=0, column=4, sticky="w", padx=(0, 6))

        self.paper_unit_menu = ctk.CTkOptionMenu(
            self.preview_actions,
            variable=self.paper_unit_var,
            values=self._paper_units(),
            command=self._on_paper_unit_change,
            fg_color="#3B8ED0",
            button_color="#36719F",
            width=80,
        )
        self.paper_unit_menu.grid(row=0, column=5, sticky="w", padx=(0, 10))

        self.paper_width_entry.bind("<FocusOut>", lambda e: self._save_paper_settings())
        self.paper_height_entry.bind("<FocusOut>", lambda e: self._save_paper_settings())
        self.paper_width_entry.bind("<Return>", lambda e: self._save_paper_settings())
        self.paper_height_entry.bind("<Return>", lambda e: self._save_paper_settings())

        self.preview_print_btn = ctk.CTkButton(
            self.preview_actions,
            text="Print",
            command=self.on_preview_print_click,
            width=160,
            height=36,
            fg_color="#3B8ED0",
            hover_color="#36719F",
        )
        self.preview_print_btn.grid(row=0, column=6, sticky="e")

        self._on_paper_change(self.paper_var.get())
        self._apply_paper_to_preview()

        # Overlay Text Items
        self.preview_labels = {}
        
        def create_overlay(key, default_x, default_y, font=("Arial", 10), anchor="nw"):
            # Use saved config coordinates if available, else defaults (though defaults are in config now)
            x_base = self.layout_config.get(key, {}).get("x", default_x)
            y_base = self.layout_config.get(key, {}).get("y", default_y)
            scale_x = self.preview_width_px / self.base_preview_width_px
            scale_y = self.preview_height_px / self.base_preview_height_px
            x = x_base * scale_x
            y = y_base * scale_y
            
            # Create text item on canvas
            # Tag with key and "draggable"
            item_id = self.canvas.create_text(x, y, text=f"[{key}]", font=font, fill="black", anchor=anchor, tags=(key, "draggable"))
            self.preview_labels[key] = item_id
            
        def create_image_overlay(key, default_x, default_y, width=100, height=100):
            x_base = self.layout_config.get(key, {}).get("x", default_x)
            y_base = self.layout_config.get(key, {}).get("y", default_y)
            scale_x = self.preview_width_px / self.base_preview_width_px
            scale_y = self.preview_height_px / self.base_preview_height_px
            x = x_base * scale_x
            y = y_base * scale_y
            
            # Create placeholder image
            if not hasattr(self, 'preview_images'):
                self.preview_images = {}
            
            # Transparent placeholder
            img = Image.new("RGBA", (int(width), int(height)), (255, 255, 255, 0))
            photo = ImageTk.PhotoImage(img)
            self.preview_images[key] = photo
            
            item_id = self.canvas.create_image(x, y, image=photo, anchor="nw", tags=(key, "draggable"))
            self.preview_labels[key] = item_id

        # Header / Meta
        create_overlay("date", 90, 135, font=("Arial", 10, "bold"))
        create_overlay("inv_no", 90, 165, font=("Arial", 10, "bold"))
        create_overlay("fbr_inv_no", 90, 185, font=("Arial", 8))
        
        create_overlay("name", 90, 215)
        create_overlay("address", 90, 255)
        
        # Grid Items
        # Adjusting X to align better with the "dotted lines" if any
        val_x = 280 
        create_overlay("desc", val_x, 400)
        create_overlay("engine", val_x, 440)
        create_overlay("chassis", val_x, 480)
        create_overlay("model", val_x, 520)
        create_overlay("color", val_x, 560)
        create_overlay("reg_letter", val_x, 600)
        
        create_overlay("item_total", 460, 400, font=("Arial", 10, "bold"))
        
        create_overlay("amount", 460, 450)
        create_overlay("sale_tax", 460, 480)
        create_overlay("other_tax", 460, 510)
        create_overlay("nev_levy_label", 350, 510)
        create_overlay("tax_rate_label", 460, 480)
        
        create_overlay("pos_fee_value", 460, 540)
        create_overlay("pos_fee_label", 350, 540)
        
        # QR Code
        create_image_overlay("qr", 340, 620, 100, 100)

        # Footer Total
        create_overlay("grand_total", 460, 710, font=("Arial", 12, "bold"))

        # Global Canvas Bindings for easier dragging
        self.canvas.bind("<Button-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_stop)

    def on_preview_print_click(self):
        chassis = self.chassis_entry.get().strip()
        invoice = self.current_invoice
        item = self.current_item
        if not invoice or not item:
            if not chassis:
                messagebox.showwarning("Warning", "Please enter a Chassis Number.")
                return
            db = SessionLocal()
            try:
                invoice, item = self._fetch_invoice_and_item(db, chassis)
            finally:
                db.close()
            if not invoice or not item:
                return
            self.current_invoice = invoice
            self.current_item = item
            self.current_chassis = chassis

        self._save_paper_settings()

        paper_width_mm, paper_height_mm = self._get_paper_dimensions_mm()
        if paper_width_mm <= 0 or paper_height_mm <= 0:
            unit = str(self.paper_unit_var.get() or "mm").strip().lower()
            messagebox.showwarning("Warning", f"Invalid paper size. Please enter width/height in {unit}.")
            return
            
        # Collect form overrides
        overrides = {
            "name": self.name_var.get(),
            "father_name": self.father_var.get(),
            "rel_type": self.rel_type_var.get(),
            "address": self.address_var.get(),
            "model": self.year_var.get(),
            "color": self.color_var.get(),
            "engine": self.engine_var.get(),
            "amount": self.amount_var.get(),
            "sale_tax": self.sale_tax_var.get(),
            "other_tax": self.other_tax_var.get(),
        }

        success, message = print_service.print_honda_live_preview(
            invoice,
            layout_config=self.layout_config,
            chassis_filter=self.current_chassis or chassis,
            explicit_item=item,
            overrides=overrides,
            paper_width_mm=paper_width_mm,
            paper_height_mm=paper_height_mm,
            preview_width_px=self.base_preview_width_px,
            preview_height_px=self.base_preview_height_px,
        )
        if not success:
            messagebox.showerror("Error", f"Failed to print invoice: {message}")

    def update_preview_panel(self, invoice, item):
        # Update text of overlay items
        if not hasattr(self, 'preview_labels'):
            return

        date_str = invoice.datetime.strftime('%d-%m-%Y')
        self.canvas.itemconfigure(self.preview_labels["date"], text=date_str)
        self.canvas.itemconfigure(self.preview_labels["inv_no"], text=str(invoice.invoice_number))
        
        c_name = invoice.customer.name if invoice.customer else ""
        c_father = invoice.customer.father_name if invoice.customer else ""
        
        # Override with manual edits from form
        c_name = self.name_var.get()
        c_father = self.father_var.get()
        rel_type = self.rel_type_var.get()

        if c_father:
            if rel_type == "Org":
                 # Format: Business Name (Contact: Person Name)
                 c_name = f"{c_name} (Attn: {c_father})"
            else:
                 c_name += f" {rel_type} {c_father}"
        
        self.canvas.itemconfigure(self.preview_labels["name"], text=c_name)
        self.canvas.itemconfigure(self.preview_labels["address"], text=self.address_var.get())
        
        # Item Details
        desc_text = "Honda Motorcycle"
        
        # Prioritize form value for Model
        model_name = self.model_var.get()
        if not model_name and item.motorcycle and item.motorcycle.product_model:
             model_name = item.motorcycle.product_model.model_name
             
        if model_name:
             desc_text += f" {model_name}"
        
        self.canvas.itemconfigure(self.preview_labels["desc"], text=desc_text)
        
        eng = self.engine_var.get()
        chas = item.motorcycle.chassis_number if item.motorcycle else ""
        col = self.color_var.get()
        
        self.canvas.itemconfigure(self.preview_labels["engine"], text=eng)
        self.canvas.itemconfigure(self.preview_labels["chassis"], text=chas)
        self.canvas.itemconfigure(self.preview_labels["model"], text=self.year_var.get())
        self.canvas.itemconfigure(self.preview_labels["color"], text=col)
        self.canvas.itemconfigure(self.preview_labels["reg_letter"], text="") 
        
        # Calculate Totals
        # Parse values from variables (handling commas)
        def parse_float(val):
            try:
                return float(str(val).replace(",", "").strip())
            except:
                return 0.0

        amount = parse_float(self.amount_var.get())
        sale_tax = parse_float(self.sale_tax_var.get())
        other_tax = parse_float(self.other_tax_var.get())

        # Horizontal Total: Price + Sales Tax (excluding N.E.V Levy)
        horizontal_total = amount + sale_tax
        
        # Grand Total: Horizontal Total + N.E.V Levy + POS Fee
        final_grand_total = horizontal_total + other_tax + 1.0
        
        self.canvas.itemconfigure(self.preview_labels["item_total"], text=f"{horizontal_total:,.0f}")
        self.canvas.itemconfigure(self.preview_labels["grand_total"], text=f"{final_grand_total:,.0f}")

        self.canvas.itemconfigure(self.preview_labels["amount"], text=f"{amount:,.2f}")
        self.canvas.itemconfigure(self.preview_labels["sale_tax"], text=f"{sale_tax:,.2f}")
        self.canvas.itemconfigure(self.preview_labels["other_tax"], text=f"{other_tax:,.2f}")
        
        # New Labels
        self.canvas.itemconfigure(self.preview_labels["fbr_inv_no"], text=getattr(invoice, "fbr_invoice_number", "") or "")
        self.canvas.itemconfigure(self.preview_labels["nev_levy_label"], text="N.E.V Levy")
        self.canvas.itemconfigure(self.preview_labels["pos_fee_label"], text="POS Fee")
        self.canvas.itemconfigure(self.preview_labels["pos_fee_value"], text="1.00")
        
        # 18% Label
        # Use tax rate from item if available, else default to 18%
        tax_rate_val = item.tax_rate if hasattr(item, 'tax_rate') else 18.0
        self.canvas.itemconfigure(self.preview_labels["tax_rate_label"], text=f"{tax_rate_val:.0f}%")

        # QR Code Update
        if "qr" in self.preview_labels:
            fbr_inv_num = getattr(invoice, "fbr_invoice_number", None)
            if fbr_inv_num:
                qr_b64 = print_service.generate_qr_base64(fbr_inv_num)
                if qr_b64:
                    try:
                        qr_bytes = base64.b64decode(qr_b64)
                        img = Image.open(BytesIO(qr_bytes))
                        img = img.resize((100, 100))
                        photo = ImageTk.PhotoImage(img)
                        
                        if not hasattr(self, 'preview_images'):
                            self.preview_images = {}
                        self.preview_images["qr"] = photo
                        
                        self.canvas.itemconfigure(self.preview_labels["qr"], image=photo)
                        self.canvas.itemconfigure(self.preview_labels["qr"], state="normal")
                    except Exception as e:
                        print(f"QR Display Error: {e}")
            else:
                self.canvas.itemconfigure(self.preview_labels["qr"], state="hidden")

    def clear_preview_panel(self):
        """Clears all preview fields and hides QR/FBR info"""
        if not hasattr(self, 'preview_labels'):
            return

        # Clear text fields
        keys_to_clear = ["date", "inv_no", "fbr_inv_no", "name", "address", 
                   "desc", "engine", "chassis", "model", "color", "reg_letter",
                   "item_total", "amount", "sale_tax", "other_tax", 
                   "nev_levy_label", "tax_rate_label", "pos_fee_value", 
                   "pos_fee_label", "grand_total"]
                   
        for key in keys_to_clear:
            if key in self.preview_labels:
                 self.canvas.itemconfigure(self.preview_labels[key], text="")

        # Hide QR Code
        if "qr" in self.preview_labels:
            self.canvas.itemconfigure(self.preview_labels["qr"], state="hidden")
            
        # Reset current objects
        self.current_invoice = None
        self.current_item = None
        self.current_chassis = None

    def preview_invoice_by_chassis(self, chassis):
        db = SessionLocal()
        try:
            invoice, item = self._fetch_invoice_and_item(db, chassis)
            if invoice and item:
                self.current_invoice = invoice
                self.current_item = item
                self.current_chassis = chassis
                self.populate_fields(invoice, item)
                self.update_preview_panel(invoice, item)
            else:
                # Not found in DB -> Switch to Manual Mode
                self.current_invoice = None
                self.current_item = None
                self.current_chassis = chassis
                self.clear_preview_panel()
                
                # Pre-fill chassis field in form
                # self.chassis_entry is already filled by user
                
                # Trigger manual preview generation
                self.on_input_change()
                
        except Exception as e:
            messagebox.showerror("Error", f"Preview error: {e}")
        finally:
            db.close()

    def print_invoice_by_chassis(self, chassis):
        db = SessionLocal()
        try:
            invoice, item = self._fetch_invoice_and_item(db, chassis)
            
            if not invoice or not item:
                # If not found in DB, use manual data from form
                invoice, item = self._create_temp_invoice_from_form()
                
                # We don't populate fields since we are using current form data
                self.current_invoice = None # Mark as manual
                self.current_item = None
            else:
                # Only populate fields if we are switching to a new chassis
                # or if this is the first load. If the user is printing the 
                # currently loaded chassis, preserve their manual edits.
                if chassis != self.current_chassis:
                    self.populate_fields(invoice, item)

                self.current_invoice = invoice
                self.current_item = item

            self.current_chassis = chassis

            self.update_preview_panel(invoice, item)

            self.on_preview_print_click()
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            db.close()


    def populate_models(self):
        try:
            active_prices = price_service.get_all_active_prices()
            model_names = [p.product_model.model_name for p in active_prices if p.product_model] if active_prices else []
            # Deduplicate while preserving order
            seen = set()
            models = []
            for name in model_names:

                if name and name not in seen:
                    seen.add(name)
                    models.append(name)
            if not models:
                models = ["CD70", "CG125"]
            self.model_menu.configure(values=models)
            self.model_menu.set(models[0])
            self.on_model_change(models[0])
        except Exception:
            self.model_menu.configure(values=["CD70", "CG125"])
            self.model_menu.set("CD70")
            self.on_model_change("CD70")

    def on_model_change(self, choice):
        try:
            prices = price_service.get_active_prices_for_model(choice)
            
            # Update Price Fields from the first active price
            if prices and len(prices) > 0:
                price = prices[0]
                self.amount_var.set(f"{price.base_price:,.2f}")
                self.sale_tax_var.set(f"{price.tax_amount:,.2f}")
                self.other_tax_var.set(f"{price.levy_amount:,.2f}")
                self.total_var.set(f"{price.total_price:,.2f}")
            
            all_colors = []
            for p in prices or []:
                if p.optional_features and isinstance(p.optional_features, dict):
                    c_str = p.optional_features.get("colors", "")
                    if c_str:
                        parts = [c.strip() for c in c_str.split(",")]
                        for part in parts:
                            if part and part not in all_colors:
                                all_colors.append(part)
            self.color_menu.configure(values=all_colors or [])
            if all_colors:
                self.color_menu.set(all_colors[0])
                self.on_color_change(all_colors[0])
            else:
                self.color_menu.set("")
            
            # Update preview to show new model and prices
            self.on_input_change()

        except Exception as e:
            print(f"Error in on_model_change: {e}")
            self.color_menu.configure(values=[])
            self.color_menu.set("")
            # Update preview to show new model (even if error in colors)
            self.on_input_change()

    def on_color_change(self, color_choice):
        self.color_var.set(color_choice)
        
        # Update financials based on Model + Color
        try:
            model = self.model_var.get()
            if model:
                price = price_service.get_price_by_model_and_color(model, color_choice)
                if price:
                    self.amount_var.set(f"{price.base_price:,.2f}")
                    self.sale_tax_var.set(f"{price.tax_amount:,.2f}")
                    self.other_tax_var.set(f"{price.levy_amount:,.2f}")
                    self.total_var.set(f"{price.total_price:,.2f}")
        except Exception as e:
            print(f"Error updating price for color: {e}")

        # Update preview
        self.on_input_change()
