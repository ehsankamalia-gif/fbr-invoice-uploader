import customtkinter as ctk
from tkinter import messagebox, filedialog
import re
from datetime import datetime
import requests
import qrcode
from PIL import Image
from tenacity import RetryError
from app.db.session import SessionLocal, init_db
from app.services.invoice_service import invoice_service
from app.services.price_service import price_service
from app.services.settings_service import settings_service
from app.services.ocr_service import ocr_service
from app.api.schemas import InvoiceCreate, InvoiceItemCreate
from app.ui.inventory_frame import InventoryFrame
from app.ui.reports_frame import ReportsFrame
from app.ui.dealer_frame import DealerFrame
from app.ui.print_invoice_frame import PrintInvoiceFrame
from app.ui.price_list_dialog import PriceListDialog
from app.ui.fbr_settings_dialog import FBRSettingsDialog
from app.ui.backup_frame import BackupFrame
from app.ui.spare_ledger_frame import SpareLedgerFrame
from app.services.dealer_service import dealer_service
from app.services.backup_service import backup_service
from app.services.form_capture_service import form_capture_service
from app.services.update_service import UpdateService
from app.ui.captured_data_frame import CapturedDataFrame

from app.utils.price_data import price_manager
import app.core.config as config
import threading

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

from app.db.models import Motorcycle, Invoice, Customer, CustomerType, CapturedData

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Honda FBR Invoice Uploader")
        self.geometry("800x600")

        # Initialize DB
        init_db()
        
        # Initialize Settings (must happen after DB init)
        try:
            settings_service.initialize_defaults()
        except Exception as e:
            print(f"Settings initialization warning: {e}")
        
        # Migrate prices if needed
        self.migrate_prices()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_home_frame()
        self.create_inventory_frame()
        self.create_invoice_frame()
        self.create_reports_frame()
        self.create_dealer_frame()
        self.create_print_frame()
        self.create_backup_frame()
        self.create_spare_ledger_frame()
        self.create_captured_data_frame()

        self.select_frame_by_name("home")
        
        # Start Backup Scheduler if enabled
        backup_service.start_scheduler()
        # Start ledger auto-close daily check
        self.after(60000, self.ledger_auto_close_tick)
        
        # Handle Window Close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Clean up resources before closing"""
        try:
            form_capture_service.stop_capture_session()
        except Exception as e:
            print(f"Error stopping capture: {e}")
        self.destroy()

    def ledger_auto_close_tick(self):
        try:
            from app.services.spare_ledger_service import spare_ledger_service
            spare_ledger_service.auto_close_daily_check()
        except Exception:
            pass
        finally:
            # Run again in 60 seconds
            if self.winfo_exists():
                self.after(60000, self.ledger_auto_close_tick)

    def migrate_prices(self):
        # Import data from legacy JSON if DB is empty
        try:
            legacy_data = price_manager.get_all()
            price_service.bulk_import_from_json(legacy_data)
        except Exception as e:
            print(f"Migration warning: {e}")

    def create_sidebar(self):
        # Increased width for better look, distinct background color
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("gray95", "gray15"))
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")

        # Logo / Brand
        self.brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.brand_frame.grid(row=0, column=0, sticky="ew", pady=(30, 10))
        
        # Main Title "HONDA"
        self.logo_label = ctk.CTkLabel(self.brand_frame, text="HONDA", 
                                     font=ctk.CTkFont(family="Arial", size=28, weight="bold"),
                                     text_color=("#C0392B", "#E74C3C"))
        self.logo_label.pack(anchor="w", padx=25)
        
        # Subtitle "FBR SYSTEM"
        self.sub_label = ctk.CTkLabel(self.brand_frame, text="FBR INTEGRATION", 
                                     font=ctk.CTkFont(size=11, weight="bold"),
                                     text_color=("gray40", "gray60"))
        self.sub_label.pack(anchor="w", padx=27, pady=(0, 2))

        # Dealer Name
        self.dealer_name_label = ctk.CTkLabel(self.brand_frame, text="Ehsan Traders", 
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     text_color=("gray40", "gray60"))
        self.dealer_name_label.pack(anchor="w", padx=27, pady=(0, 8))

        # Environment badge (Styled)
        self.env_badge = ctk.CTkLabel(self.brand_frame, text="",
                                      font=ctk.CTkFont(size=10, weight="bold"),
                                      text_color="white",
                                      corner_radius=4)
        self.env_badge.pack(anchor="w", padx=25, pady=5)
        self.update_env_badge()
        
        # Separator Line
        self.separator = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color=("gray85", "gray25"))
        self.separator.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        self.create_nav_buttons()

    def update_env_badge(self):
        # Use settings_service to get the true active environment directly from file
        # This avoids issues with load_dotenv caching or stale config objects
        active_env = settings_service.get_active_environment()
        is_prod = active_env == "PRODUCTION"
        
        env_color = "#27AE60" if is_prod else "#E67E22" 
        env_text = "  PRODUCTION  " if is_prod else "  SANDBOX ENV  "
        
        self.env_badge.configure(text=env_text, fg_color=env_color)

    def create_nav_buttons(self):
        # Container for navigation items (using pack for hierarchical layout)
        self.nav_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_rowconfigure(2, weight=1) # Main nav area expands
        self.sidebar_frame.grid_rowconfigure(13, weight=0) # Remove weight from spacer
        
        self.menu_groups = {}
        self.nav_buttons = {}

        # 1. Dashboard (Single Item)
        self.create_single_nav_item("Dashboard", "home", self.home_button_event, "📊")

        # 2. Invoice Management
        self.create_menu_group("Invoice Management", "invoice_grp", "📄", [
            ("New Invoice", "invoice", self.invoice_button_event),
            ("Print Invoice", "print_invoice", self.print_invoice_button_event),
            ("Reports", "reports", self.reports_button_event)
        ])

        # 3. Inventory & Dealers
        self.create_menu_group("Inventory & Dealers", "inventory_grp", "📦", [
            ("Inventory", "inventory", self.inventory_button_event),
            ("Dealers", "dealer", self.dealer_button_event),
            ("Price List", "pricelist", self.open_price_list)
        ])

        # 4. System Management
        self.create_menu_group("System Management", "system_grp", "⚙️", [
            ("Backup & Restore", "backup", self.backup_button_event),
            ("FBR Settings", "settings", self.open_fbr_settings),
            ("Spare Ledger", "spare_ledger", self.spare_ledger_button_event),
            ("Check for Updates", "update", self.check_updates)
        ])

        # 5. Form Capture
        self.create_menu_group("Form Capture", "capture_grp", "📷", [
            ("Live Form Capture", "capture_live", self.form_capture_button_event),
            ("View Captured Data", "captured_data", self.captured_data_button_event)
        ])

        # Map legacy button attributes for compatibility
        self.home_button = self.nav_buttons.get("home")
        self.invoice_button = self.nav_buttons.get("invoice")
        self.print_inv_button = self.nav_buttons.get("print_invoice")
        self.reports_button = self.nav_buttons.get("reports")
        self.inventory_button = self.nav_buttons.get("inventory")
        self.dealer_button = self.nav_buttons.get("dealer")
        self.backup_button = self.nav_buttons.get("backup")
        self.captured_data_button = self.nav_buttons.get("captured_data")
        self.settings_button = self.nav_buttons.get("settings")
        self.spare_ledger_button = self.nav_buttons.get("spare_ledger")
        self.price_list_button = self.nav_buttons.get("pricelist")
        self.capture_button = self.nav_buttons.get("capture_live")

        # Exit Button (Red/Professional Look)
        self.exit_button = ctk.CTkButton(self.sidebar_frame, text="Exit", 
                                            command=self.on_closing,
                                            font=ctk.CTkFont(size=15, weight="bold"),
                                            corner_radius=6, 
                                            height=45, 
                                            border_spacing=10, 
                                            anchor="center", 
                                            fg_color="#C0392B", 
                                            hover_color="#E74C3C",
                                            text_color="white")
        self.exit_button.grid(row=3, column=0, sticky="ew", padx=10, pady=20)

    def create_single_nav_item(self, text, name, command, icon=""):
        btn = ctk.CTkButton(self.nav_container, text=f"  {icon}  {text}", 
                            command=command,
                            font=ctk.CTkFont(size=14, weight="bold"),
                            corner_radius=6, 
                            height=40, 
                            anchor="w", 
                            fg_color="transparent", 
                            text_color=("gray10", "gray90"), 
                            hover_color=("gray70", "gray30"))
        btn.pack(fill="x", padx=10, pady=2)
        self.nav_buttons[name] = btn
        return btn

    def create_menu_group(self, title, group_id, icon, items):
        # Parent Button Frame
        group_frame = ctk.CTkFrame(self.nav_container, fg_color="transparent")
        group_frame.pack(fill="x", padx=0, pady=2)
        
        # Parent Button
        parent_btn = ctk.CTkButton(group_frame, text=f"  {icon}  {title}", 
                                   command=lambda: self.toggle_menu(group_id),
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   corner_radius=6, 
                                   height=40, 
                                   anchor="w", 
                                   fg_color="transparent", 
                                   text_color=("gray10", "gray90"), 
                                   hover_color=("gray70", "gray30"))
        parent_btn.pack(fill="x", padx=10)
        
        # Indicator (Chevron)
        indicator = ctk.CTkLabel(parent_btn, text="▶", font=ctk.CTkFont(size=12), text_color="gray50")
        indicator.place(relx=0.9, rely=0.5, anchor="center")
        
        # Submenu Container
        submenu_frame = ctk.CTkFrame(group_frame, fg_color="transparent")
        # Initially hidden
        
        # Create Sub-items
        for text, name, command in items:
            sub_btn = ctk.CTkButton(submenu_frame, text=f"      {text}", 
                                    command=command,
                                    font=ctk.CTkFont(size=13),
                                    corner_radius=6, 
                                    height=35, 
                                    anchor="w", 
                                    fg_color="transparent", 
                                    text_color=("gray40", "gray60"), 
                                    hover_color=("gray80", "gray25"))
            sub_btn.pack(fill="x", padx=10, pady=1)
            self.nav_buttons[name] = sub_btn

        self.menu_groups[group_id] = {
            "frame": submenu_frame,
            "indicator": indicator,
            "expanded": False,
            "buttons": [name for _, name, _ in items]
        }

    def toggle_menu(self, group_id):
        group = self.menu_groups[group_id]
        is_expanded = group["expanded"]

        # 1. Automatically collapse any currently expanded menu (Accordion behavior)
        self.collapse_all_menus(except_id=group_id)

        # 2. Toggle the clicked menu
        if is_expanded:
            group["frame"].pack_forget()
            group["indicator"].configure(text="▶")
            group["expanded"] = False
        else:
            # Smooth transition (simulated by layout manager)
            group["frame"].pack(fill="x", pady=(0, 5))
            group["indicator"].configure(text="▼")
            group["expanded"] = True

    def collapse_all_menus(self, except_id=None):
        """Helper to collapse all menus except the specified one."""
        for g_id, group in self.menu_groups.items():
            if g_id != except_id and group["expanded"]:
                group["frame"].pack_forget()
                group["indicator"].configure(text="▶")
                group["expanded"] = False

    def expand_menu_containing(self, name):
        """Auto-expand the menu group containing the named button."""
        for group_id, group in self.menu_groups.items():
            if name in group["buttons"]:
                # Ensure this is the only one expanded
                if not group["expanded"]:
                    self.toggle_menu(group_id)
                else:
                    # If already expanded, just ensure others are closed
                    self.collapse_all_menus(except_id=group_id)
                return

    def check_updates(self):
        """Checks for software updates."""
        try:
            updater = UpdateService()
            available, msg, download_url = updater.check_for_updates()
            
            if available:
                if download_url and updater.is_frozen:
                    # EXE Update available
                    if messagebox.askyesno("Update Available", f"{msg}\n\nDo you want to download and install the update now?"):
                        self.show_download_progress(updater, download_url)
                else:
                    # Script update or manual link
                    if messagebox.askyesno("Update Available", f"{msg}\n\nDo you want to update now?"):
                        if updater.is_frozen:
                            # Fallback for frozen if no download URL but update available
                            import webbrowser
                            webbrowser.open(download_url if download_url else "https://github.com/ehsankamalia-gif/fbr-invoice-uploader/releases")
                        else:
                            success, update_msg = updater.perform_update()
                            if success:
                                messagebox.showinfo("Update Successful", "Application updated successfully.\nPlease restart the application.")
                                self.on_closing()
                            else:
                                messagebox.showerror("Update Failed", update_msg)
            else:
                messagebox.showinfo("Software Update", "Application is already updated.")
                
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to check for updates:\n{str(e)}")

    def show_download_progress(self, updater, url):
        """Shows a progress dialog and handles the download in a thread."""
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Downloading Update")
        progress_window.geometry("400x150")
        progress_window.transient(self)
        progress_window.grab_set()
        
        # Center the window
        progress_window.update_idletasks()
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (progress_window.winfo_width() // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (progress_window.winfo_height() // 2)
            progress_window.geometry(f"+{x}+{y}")
        except:
            pass
        
        lbl = ctk.CTkLabel(progress_window, text="Downloading update...", font=("Arial", 14))
        lbl.pack(pady=(20, 10))
        
        progress_bar = ctk.CTkProgressBar(progress_window, width=300)
        progress_bar.pack(pady=10)
        progress_bar.set(0)
        
        status_lbl = ctk.CTkLabel(progress_window, text="0%")
        status_lbl.pack(pady=5)
        
        def progress_callback(current, total):
            if total > 0:
                progress = current / total
                # Update UI in main thread
                self.after(0, lambda: progress_bar.set(progress))
                self.after(0, lambda: status_lbl.configure(text=f"{int(progress * 100)}%"))

        def run_download():
            try:
                # Download
                exe_path = updater.download_update(url, progress_callback)
                
                # Close progress window
                self.after(0, progress_window.destroy)
                
                # Apply Update
                def confirm_install():
                     if messagebox.askyesno("Download Complete", "Update downloaded successfully.\nThe application will now restart to apply changes."):
                        updater.apply_update(exe_path)
                
                self.after(0, confirm_install)
                    
            except Exception as e:
                self.after(0, progress_window.destroy)
                def show_error():
                    messagebox.showerror("Download Failed", str(e))
                self.after(0, show_error)

        threading.Thread(target=run_download, daemon=True).start()

    def create_spare_ledger_frame(self):
        self.spare_ledger_frame = SpareLedgerFrame(self)
        self.spare_ledger_frame.grid(row=0, column=1, sticky="nsew")
        self.spare_ledger_frame.grid_forget()

    def spare_ledger_button_event(self):
        self.select_frame_by_name("spare_ledger")

    def create_home_frame(self):
        self.home_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.home_frame.grid_columnconfigure(0, weight=1)

        # Header Section
        header_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.label_home = ctk.CTkLabel(header_frame, text="Dashboard Overview Here", 
                                     font=ctk.CTkFont(family="Arial", size=28, weight="bold"),
                                     text_color=("gray10", "gray90"))
        self.label_home.pack(side="left")

        # Refresh Button (Modern pill shape)
        self.refresh_btn = ctk.CTkButton(header_frame, text="Refresh Data", 
                                       command=self.refresh_stats,
                                       width=120, height=32,
                                       corner_radius=20,
                                       fg_color=("#3498DB", "#2980B9"),
                                       font=ctk.CTkFont(size=12, weight="bold"))
        self.refresh_btn.pack(side="right")
        
        # Stats Grid Container
        self.stats_grid = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.stats_grid.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.stats_grid.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat_card")

        # Create Cards
        # Row 1
        self.card_stock = self.create_stat_card(self.stats_grid, "In Stock", "0", 
                                              icon="📦", row=0, col=0, color="#27AE60") # Green
        self.card_sold = self.create_stat_card(self.stats_grid, "Total Sold", "0", 
                                             icon="🤝", row=0, col=1, color="#F39C12") # Orange
        self.card_sales = self.create_stat_card(self.stats_grid, "Total Revenue", "PKR 0", 
                                              icon="💰", row=0, col=2, color="#8E44AD") # Purple
        
        # Row 2
        self.card_fbr_success = self.create_stat_card(self.stats_grid, "FBR Success", "0", 
                                            icon="✅", row=1, col=0, color="#27AE60") # Green
        self.card_fbr_failed = self.create_stat_card(self.stats_grid, "FBR Failed", "0", 
                                            icon="❌", row=1, col=1, color="#C0392B") # Red
        self.card_customers = self.create_stat_card(self.stats_grid, "Customers", "0", 
                                                  icon="👥", row=1, col=2, color="#2980B9") # Blue
        
        # Row 3
        self.card_dealers = self.create_stat_card(self.stats_grid, "Dealers", "0", 
                                                icon="🏢", row=2, col=0, color="#16A085") # Teal

        self.auto_refresh_stats()

    def auto_refresh_stats(self):
        """Refreshes stats and schedules the next refresh."""
        try:
            if self.winfo_exists():
                self.refresh_stats()
                # Schedule next refresh in 2000ms (2 seconds)
                self.after(2000, self.auto_refresh_stats)
        except Exception as e:
            print(f"Auto refresh error: {e}")

    def create_stat_card(self, parent, title, value, icon, row, col, color):
        """Creates a stylish stat card."""
        card = ctk.CTkFrame(parent, corner_radius=15, fg_color=("white", "gray20"))
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Left accent bar
        accent = ctk.CTkFrame(card, width=6, corner_radius=10, fg_color=color)
        accent.pack(side="left", fill="y", pady=5, padx=(5, 10))
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=5, pady=10)
        
        # Title
        ctk.CTkLabel(content, text=title.upper(), 
                   font=ctk.CTkFont(size=11, weight="bold"),
                   text_color=("gray50", "gray40"),
                   anchor="w").pack(fill="x")
        
        # Value
        val_label = ctk.CTkLabel(content, text=value, 
                               font=ctk.CTkFont(size=22, weight="bold"),
                               text_color=("gray10", "gray90"),
                               anchor="w")
        val_label.pack(fill="x", pady=(2, 0))
        
        # Icon (Right side)
        icon_label = ctk.CTkLabel(card, text=icon, 
                                font=ctk.CTkFont(size=30),
                                text_color=color)
        icon_label.pack(side="right", padx=15)
        
        return val_label  # Return the value label to update it later

    def refresh_stats(self):
        db = SessionLocal()
        try:
            # Count Motorcycles (In Stock)
            bike_count = db.query(Motorcycle).filter(Motorcycle.status == "IN_STOCK").count()
            self.card_stock.configure(text=f"{bike_count}")
            
            # Count Sold Motorcycles
            sold_count = db.query(Motorcycle).filter(Motorcycle.status == "SOLD").count()
            self.card_sold.configure(text=f"{sold_count}")
            
            # Sum Invoices
            invoices = db.query(Invoice).all()
            total_sales = sum(inv.total_amount for inv in invoices)
            self.card_sales.configure(text=f"PKR {total_sales:,.0f}")
            
            # FBR Success
            fbr_success = db.query(Invoice).filter(Invoice.fbr_invoice_number != None).count()
            self.card_fbr_success.configure(text=f"{fbr_success}")

            # FBR Failed
            fbr_failed = db.query(Invoice).filter(Invoice.sync_status == "FAILED").count()
            self.card_fbr_failed.configure(text=f"{fbr_failed}")
            # Update the stat in invoice form too if it exists
            if hasattr(self, 'fbr_stat_value'):
                self.fbr_stat_value.configure(text=f"{fbr_success}")

            # Customers (Excluding Dealers)
            cust_count = db.query(Customer).filter(Customer.type != CustomerType.DEALER).count()
            self.card_customers.configure(text=f"{cust_count}")

            # Dealers
            dealer_count = db.query(Customer).filter(Customer.type == CustomerType.DEALER).count()
            self.card_dealers.configure(text=f"{dealer_count}")
            
        except Exception as e:
            logger.error(f"Error refreshing stats: {e}", exc_info=True)
            print(f"Error refreshing stats: {e}")
        finally:
            db.close()

    def create_invoice_frame(self):
        self.invoice_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.invoice_frame.grid_columnconfigure(0, weight=1)
        self.invoice_frame.grid_rowconfigure(1, weight=1)
        
        self.current_price_obj = None

        self.label_invoice = ctk.CTkLabel(self.invoice_frame, text="New Invoice", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_invoice.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.form_frame = ctk.CTkScrollableFrame(self.invoice_frame, label_text="Invoice Details")
        self.form_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Configure columns with minsize to prevent squashing
        self.form_frame.grid_columnconfigure(1, weight=1, minsize=200)

        # --- Fields ---
        
        # 1. Invoice Number
        ctk.CTkLabel(self.form_frame, text="Invoice Number").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.inv_num_var = ctk.StringVar()
        self.inv_num_var.trace_add("write", lambda *args: self.check_form_validity())
        self.inv_num_entry = ctk.CTkEntry(self.form_frame, textvariable=self.inv_num_var, state="readonly")
        self.inv_num_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Auto-generate button (optional, but good for manual refresh if needed)
        self.refresh_inv_btn = ctk.CTkButton(self.form_frame, text="↺", width=30, command=self.generate_invoice_number)
        self.refresh_inv_btn.grid(row=0, column=2, padx=5, sticky="w")

        # FBR Submitted Statistic Box
        self.fbr_stat_frame = ctk.CTkFrame(self.form_frame, fg_color=("#C0392B", "#922B21"), corner_radius=10)
        self.fbr_stat_frame.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.fbr_stat_frame, text="FBR Submitted", font=ctk.CTkFont(size=11, weight="bold"), text_color="white").pack(pady=(5,0))
        self.fbr_stat_value = ctk.CTkLabel(self.fbr_stat_frame, text="0", font=ctk.CTkFont(size=20, weight="bold"), text_color="white")
        self.fbr_stat_value.pack(pady=(0,5))

        # QR Code Display Area (Placeholder for Success)
        self.qr_code_label = ctk.CTkLabel(self.form_frame, text="", width=120, height=120)
        self.qr_code_label.grid(row=1, column=3, rowspan=4, padx=10, pady=10, sticky="n")
        
        # FBR Invoice Number Label (Below QR Code)
        self.fbr_inv_label = ctk.CTkLabel(self.form_frame, text="", font=("Arial", 12, "bold"), text_color="blue")
        self.fbr_inv_label.grid(row=5, column=3, padx=10, pady=0, sticky="n")

        # 1.5 ID Card (CNIC)
        ctk.CTkLabel(self.form_frame, text="ID Card (CNIC)").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.buyer_cnic_var = ctk.StringVar()
        self.buyer_cnic_var.trace_add("write", self.validate_cnic_input)
        self.buyer_cnic_entry = ctk.CTkEntry(self.form_frame, textvariable=self.buyer_cnic_var, placeholder_text="33302-1234567-0")
        self.buyer_cnic_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.buyer_cnic_entry.bind("<KeyRelease>", self.auto_fill_cnic)
        
        # Scan ID Card Button
        self.scan_btn = ctk.CTkButton(self.form_frame, text="📷 Scan ID", width=80, command=self.scan_cnic_action, fg_color="#E67E22", hover_color="#D35400")
        self.scan_btn.grid(row=1, column=2, padx=5, sticky="w")
        
        # Disable if OCR not available
        if not ocr_service.is_available():
            self.scan_btn.grid_forget() # Hide if no OCR

        # 2. Buyer Name
        ctk.CTkLabel(self.form_frame, text="Buyer Name").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.buyer_name_var = ctk.StringVar()
        self.buyer_name_var.trace_add("write", self.validate_buyer_name)
        self.buyer_name_entry = ctk.CTkEntry(self.form_frame, textvariable=self.buyer_name_var)
        self.buyer_name_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # 3. Father
        ctk.CTkLabel(self.form_frame, text="Father Name").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.father_name_var = ctk.StringVar()
        self.father_name_var.trace_add("write", self.validate_father_name)
        self.buyer_father_entry = ctk.CTkEntry(self.form_frame, textvariable=self.father_name_var)
        self.buyer_father_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        # 4. Cell
        ctk.CTkLabel(self.form_frame, text="Cell (Phone)").grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.buyer_cell_var = ctk.StringVar()
        self.buyer_cell_var.trace_add("write", self.validate_cell_input)
        self.buyer_cell_entry = ctk.CTkEntry(self.form_frame, textvariable=self.buyer_cell_var, placeholder_text="03XXXXXXXXX")
        self.buyer_cell_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        # 5. Address
        ctk.CTkLabel(self.form_frame, text="Address").grid(row=5, column=0, padx=10, pady=5, sticky="e")
        self.buyer_address_var = ctk.StringVar()
        self.buyer_address_var.trace_add("write", self.validate_address)
        self.buyer_address_entry = ctk.CTkEntry(self.form_frame, textvariable=self.buyer_address_var)
        self.buyer_address_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        # 5.5 Model & Color
        ctk.CTkLabel(self.form_frame, text="Model").grid(row=6, column=0, padx=10, pady=5, sticky="e")
        
        self.model_color_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.model_color_frame.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        # Get active models from DB
        active_prices = price_service.get_all_active_prices()
        model_names = [p.product_model.model_name for p in active_prices if p.product_model] if active_prices else ["CD70", "CG125"]
        
        self.model_combo = ctk.CTkOptionMenu(self.model_color_frame, values=model_names, command=self.on_model_change)
        self.model_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.model_combo.set("") # Start empty
        
        ctk.CTkLabel(self.model_color_frame, text="Color").pack(side="left", padx=5)
        
        self.color_combo = ctk.CTkOptionMenu(self.model_color_frame, values=["Red", "Blue"], command=self.on_color_change)
        self.color_combo.pack(side="left", fill="x", expand=True)
        self.color_combo.set("") # Start empty

        # 6. Payment Mode (New)
        ctk.CTkLabel(self.form_frame, text="Payment Mode").grid(row=7, column=0, padx=10, pady=5, sticky="e")
        self.payment_mode_combo = ctk.CTkOptionMenu(self.form_frame, values=["Cash", "Credit", "Cheque", "Online"])
        self.payment_mode_combo.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

        # 7. Chassis Number
        ctk.CTkLabel(self.form_frame, text="Chassis Number").grid(row=8, column=0, padx=10, pady=5, sticky="e")
        self.chassis_var = ctk.StringVar()
        self.chassis_var.trace_add("write", self.validate_chassis)
        self.chassis_entry = ctk.CTkEntry(self.form_frame, textvariable=self.chassis_var)
        self.chassis_entry.grid(row=8, column=1, padx=10, pady=5, sticky="ew")
        self.chassis_entry.bind("<KeyRelease>", self.on_chassis_key_release)
        self.chassis_entry.bind("<Down>", self.on_suggestion_nav)
        self.chassis_entry.bind("<Up>", self.on_suggestion_nav)
        self.chassis_entry.bind("<Return>", self.on_suggestion_select)
        self.chassis_entry.bind("<FocusOut>", self.on_chassis_focus_out)
        
        # Suggestion Window (Toplevel for floating effect)
        self.suggestion_window = None
        self.suggestion_buttons = []
        self.selected_suggestion_index = -1
        
        # Container for Chassis Tools (Checkbox + Feedback) in Column 2
        self.chassis_tools_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.chassis_tools_frame.grid(row=8, column=2, padx=5, pady=5, sticky="w")

        # Verify Chassis Checkbox (New)
        self.verify_chassis_var = ctk.BooleanVar(value=False)
        self.verify_chassis_chk = ctk.CTkCheckBox(self.chassis_tools_frame, text="", width=24,
                                                variable=self.verify_chassis_var,
                                                command=self.on_verify_chassis_change)
        self.verify_chassis_chk.pack(side="left", padx=(0, 5))

        # Chassis Feedback Label
        self.chassis_feedback_label = ctk.CTkLabel(self.chassis_tools_frame, text="", width=20)
        self.chassis_feedback_label.pack(side="left")

        # Check Stock Button - Moved to Column 3
        self.check_stock_btn = ctk.CTkButton(self.form_frame, text="Check Stock", width=100, command=self.check_stock)
        self.check_stock_btn.grid(row=8, column=3, padx=10, pady=5)

        # 8. Engine Number
        ctk.CTkLabel(self.form_frame, text="Engine Number").grid(row=9, column=0, padx=10, pady=5, sticky="e")
        self.engine_var = ctk.StringVar()
        self.engine_var.trace_add("write", self.validate_engine)
        self.engine_entry = ctk.CTkEntry(self.form_frame, textvariable=self.engine_var)
        self.engine_entry.grid(row=9, column=1, padx=10, pady=5, sticky="ew")

        # 9. Quantity
        ctk.CTkLabel(self.form_frame, text="Quantity").grid(row=10, column=0, padx=10, pady=5, sticky="e")
        
        self.qty_var = ctk.StringVar(value="1")
        self.qty_var.trace_add("write", lambda *args: self.check_form_validity())
        
        # Entry in Column 1 (Main area)
        self.qty_entry = ctk.CTkEntry(self.form_frame, textvariable=self.qty_var, state="disabled")
        self.qty_entry.grid(row=10, column=1, padx=10, pady=5, sticky="ew")
        
        # Checkbox in Column 2 (Right side - Red Dot Position)
        self.manual_qty_var = ctk.BooleanVar(value=False)
        self.manual_qty_chk = ctk.CTkCheckBox(self.form_frame, text="Edit", variable=self.manual_qty_var, width=60, command=self.toggle_quantity_mode)
        self.manual_qty_chk.grid(row=10, column=2, padx=5, pady=5, sticky="w")



        # 10. Amount Excluding Sale Tax
        ctk.CTkLabel(self.form_frame, text="Amount (Excl. Tax)").grid(row=11, column=0, padx=10, pady=5, sticky="e")
        self.amount_var = ctk.StringVar()
        self.amount_var.trace_add("write", lambda *args: self.check_form_validity())
        self.amount_excl_entry = ctk.CTkEntry(self.form_frame, textvariable=self.amount_var)
        self.amount_excl_entry.grid(row=11, column=1, padx=10, pady=5, sticky="ew")
        # Bind event to auto-calc tax
        self.amount_excl_entry.bind("<KeyRelease>", self.calculate_totals)

        # 11. Sale Tax (Read Only or Editable)
        ctk.CTkLabel(self.form_frame, text="Sale Tax").grid(row=12, column=0, padx=10, pady=5, sticky="e")
        self.tax_entry = ctk.CTkEntry(self.form_frame)
        self.tax_entry.grid(row=12, column=1, padx=10, pady=5, sticky="ew")
        self.tax_entry.bind("<KeyRelease>", self.calculate_totals)

        # 12. Further Tax
        ctk.CTkLabel(self.form_frame, text="Further Tax").grid(row=13, column=0, padx=10, pady=5, sticky="e")
        self.further_tax_entry = ctk.CTkEntry(self.form_frame)
        self.further_tax_entry.grid(row=13, column=1, padx=10, pady=5, sticky="ew")
        self.further_tax_entry.bind("<KeyRelease>", self.calculate_totals)

        # 13. Price (Total)
        ctk.CTkLabel(self.form_frame, text="Total Price (Incl. Tax)").grid(row=14, column=0, padx=10, pady=5, sticky="e")
        self.total_price_entry = ctk.CTkEntry(self.form_frame)
        self.total_price_entry.grid(row=14, column=1, padx=10, pady=5, sticky="ew")

        # Button Frame for Submit and Reset
        self.btn_frame = ctk.CTkFrame(self.invoice_frame, fg_color="transparent")
        self.btn_frame.grid(row=2, column=0, padx=20, pady=20)

        self.submit_btn = ctk.CTkButton(self.btn_frame, text="Submit Invoice", command=self.submit_invoice, state="disabled")
        self.submit_btn.grid(row=0, column=0, padx=10)

        self.reset_btn = ctk.CTkButton(self.btn_frame, text="Reset Form", command=self.reset_form, fg_color="gray")
        self.reset_btn.grid(row=0, column=1, padx=10)

        # Initialize Keyboard Navigation
        self.setup_keyboard_navigation()




    def setup_keyboard_navigation(self):
        """Sets up Enter key navigation through form fields in a specific sequence."""
        # Define the sequence of widgets
        # Sequence: ID -> Name -> Father -> Cell -> Address -> Model -> Color -> Payment -> Chassis -> Engine
        self.nav_sequence = [
            self.buyer_cnic_entry,
            self.buyer_name_entry,
            self.buyer_father_entry,
            self.buyer_cell_entry,
            self.buyer_address_entry,
            self.model_combo,
            self.color_combo,
            self.payment_mode_combo,
            self.chassis_entry,
            self.engine_entry
        ]

        # Bind <Return> key for each widget to focus the next one
        for i, widget in enumerate(self.nav_sequence):
            # For the last widget (Engine), bind to Submit
            if i == len(self.nav_sequence) - 1:
                if isinstance(widget, ctk.CTkEntry):
                    widget.bind("<Return>", self.on_last_field_enter)
                else:
                    # Fallback for non-entry widgets if any end up last
                    try:
                        widget.bind("<Return>", self.on_last_field_enter)
                    except:
                        pass
            else:
                next_widget = self.nav_sequence[i + 1]
                
                # Define a closure to capture next_widget
                def focus_next(event, target=next_widget, current_widget=widget):
                    # Special check for CNIC field to trigger lookup on Enter
                    if current_widget == self.buyer_cnic_entry:
                        self.perform_cnic_lookup()
                    
                    target.focus_set()
                    return "break" # Prevent default behavior
                
                if isinstance(widget, ctk.CTkEntry):
                    widget.bind("<Return>", focus_next)
                elif isinstance(widget, ctk.CTkOptionMenu):
                    # CTkOptionMenu is a frame, usually doesn't capture key events easily unless focused.
                    # We try binding to the widget itself.
                    # Note: CTkOptionMenu might need explicit focus_set() to receive keys.
                    widget.bind("<Return>", focus_next) 
        
        # Explicitly bind FocusOut to CNIC for lookup
        self.buyer_cnic_entry.bind("<FocusOut>", lambda e: self.perform_cnic_lookup())

        # Bind Up/Down keys for OptionMenus
        self._bind_option_menu_arrows(self.model_combo, self.on_model_change)
        self._bind_option_menu_arrows(self.color_combo, self.on_color_change)
        self._bind_option_menu_arrows(self.payment_mode_combo, None)

    def _bind_option_menu_arrows(self, widget, callback=None):
        """Binds Up/Down keys to cycle options in a CTkOptionMenu."""
        widget.bind("<Up>", lambda e: self._handle_option_arrow(e, widget, -1, callback))
        widget.bind("<Down>", lambda e: self._handle_option_arrow(e, widget, 1, callback))

    def _handle_option_arrow(self, event, widget, delta, callback=None):
        """Handles arrow key press for OptionMenu."""
        values = widget._values
        if not values:
            return "break"
            
        current_val = widget.get()
        try:
            index = values.index(current_val)
        except ValueError:
            # If current value not in list (e.g. empty), start at -1 so next is 0
            index = -1
            
        new_index = index + delta
        
        # Clamp index
        if new_index < 0:
            new_index = 0
        elif new_index >= len(values):
            new_index = len(values) - 1
            
        if new_index != index:
            new_val = values[new_index]
            widget.set(new_val)
            if callback:
                callback(new_val)
        
        return "break"

    def on_last_field_enter(self, event):
        """Handles Enter key on the last field (Engine Number)."""
        # Validate that all required fields are populated
        if self.validate_all_fields():
            self.submit_invoice()
        else:
             messagebox.showwarning("Validation Error", "Please fill all required fields before submitting.")
             
    def validate_all_fields(self):
        """Checks if all fields in the navigation sequence have values."""
        for widget in self.nav_sequence:
            # Skip disabled widgets
            try:
                if widget.cget("state") == "disabled":
                    continue
            except:
                pass

            value = ""
            if isinstance(widget, ctk.CTkEntry):
                value = widget.get()
            elif isinstance(widget, ctk.CTkOptionMenu):
                value = widget.get()
            
            if not value or value.strip() == "":
                # Focus the first empty widget
                try:
                    widget.focus_set()
                except:
                    pass
                return False
        return True

    def toggle_quantity_mode(self):
        if self.manual_qty_var.get():
            self.qty_entry.configure(state="normal")
        else:
            self.qty_var.set("1")
            self.qty_entry.configure(state="disabled")
        self.calculate_totals()

    def calculate_totals(self, *args):
        try:
            qty = float(self.qty_entry.get() or 0)
            amount_excl = float(self.amount_excl_entry.get() or 0)
            
            # Default values if no price object
            tax_charged = 0.0
            total_further_tax = 0.0
            
            if self.current_price_obj:
                # Use exact values from Price Table as per requirement
                # These are per-unit values from the database
                tax_per_unit = self.current_price_obj.tax_amount
                further_tax_per_unit = self.current_price_obj.levy_amount
                
                # Calculate totals based on quantity
                tax_charged = tax_per_unit * qty
                total_further_tax = further_tax_per_unit * qty
                
                # We trust the user/price table for the base amount. 
                # If the user edited the Amount(Excl), we still use the fixed tax from table 
                # (assuming tax is based on MRP/Table Price, not transactional price, or user didn't edit).
                # But to be perfectly consistent with "Values from price table", 
                # we should probably verify if amount_excl matches base_price.
                # For now, we calculate total based on whatever is in the Amount field + Fixed Taxes.
                
            else:
                # Fallback to Rate-based calculation (Legacy/Manual mode)
                from app.services.settings_service import settings_service
                settings = settings_service.get_active_settings()
                tax_rate = float(settings.get("tax_rate", 18.0))
                
                sale_value = amount_excl * qty
                tax_charged = (sale_value * tax_rate) / 100
                total_further_tax = 0.0 # No further tax in manual mode unless added logic
            
            # Final Calculation
            sale_value_total = amount_excl * qty
            total_amount = sale_value_total + tax_charged + total_further_tax
            
            # Update UI Fields
            self.tax_entry.delete(0, 'end')
            self.tax_entry.insert(0, f"{tax_charged:.2f}")
            
            self.further_tax_entry.delete(0, 'end')
            self.further_tax_entry.insert(0, f"{total_further_tax:.2f}")
            
            self.total_price_entry.delete(0, 'end')
            self.total_price_entry.insert(0, f"{total_amount:.2f}")
            

            
            self.check_form_validity()
            
        except ValueError:
            pass

    def on_model_change(self, choice):
        """Auto-fill price and colors when model is selected."""


        # 1. Get all active prices for this model to find all available colors
        prices = price_service.get_active_prices_for_model(choice)
        
        if not prices:
            self.current_price_obj = None
            return

        # 2. Collect unique colors from ALL price entries for this model
        all_colors = []
        for p in prices:
            if p.optional_features and isinstance(p.optional_features, dict):
                c_str = p.optional_features.get("colors", "")
                if c_str:
                    parts = [c.strip() for c in c_str.split(",")]
                    for part in parts:
                        if part and part not in all_colors:
                            all_colors.append(part)
        
        # 3. Update Color Dropdown
        if all_colors:
            self.color_combo.configure(values=all_colors)
            # Select first color by default
            default_color = all_colors[0]
            self.color_combo.set(default_color)
            
            # 4. Set Price based on Model + Default Color
            self.on_color_change(default_color)
        else:
            # Fallback if no colors defined
            self.color_combo.configure(values=[])
            self.color_combo.set("")
            
            # Use first available price
            price = prices[0]
            self.current_price_obj = price
            self.amount_excl_entry.delete(0, "end")
            self.amount_excl_entry.insert(0, str(price.base_price))
            self.calculate_totals()

    def on_color_change(self, color_choice):
        """Update price based on selected model and color."""


        model = self.model_combo.get()
        price = price_service.get_price_by_model_and_color(model, color_choice)
        
        self.current_price_obj = price
        if price:
            self.amount_excl_entry.delete(0, "end")
            self.amount_excl_entry.insert(0, str(price.base_price))
            self.calculate_totals()

    def validate_buyer_name(self, *args):
        self._validate_name(self.buyer_name_var)
        
        # Auto-populate dealer info if found
        name = self.buyer_name_var.get().strip()
        if name:
            # Check for dealer match
            dealer = dealer_service.get_dealer_by_business_name(name)
            if dealer:
                self.buyer_cnic_var.set(dealer.cnic)
                self.father_name_var.set(dealer.father_name)
                self.buyer_cell_var.set(dealer.phone)
                self.buyer_address_var.set(dealer.address)
                
                # Replace Business Name with Dealer Name
                if dealer.name and name != dealer.name.upper():
                    self.buyer_name_var.set(dealer.name.upper())

    def validate_father_name(self, *args):
        self._validate_name(self.father_name_var)

    def _validate_name(self, var):
        value = var.get()
        if not value:
            self.check_form_validity()
            return

        # Check if value contains only alphabets and spaces
        if not all(x.isalpha() or x.isspace() for x in value):
            # Filter valid characters
            cleaned = ''.join(c for c in value if c.isalpha() or c.isspace())
            var.set(cleaned.upper())
            return
        
        # Ensure uppercase
        if value != value.upper():
            var.set(value.upper())
            return
            
        self.check_form_validity()

    def validate_address(self, *args):
        value = self.buyer_address_var.get()
        if not value:
            self.check_form_validity()
            return
            
        # Ensure uppercase
        if value != value.upper():
            self.buyer_address_var.set(value.upper())
            return
            
        self.check_form_validity()

    def validate_chassis(self, *args):
        value = self.chassis_var.get()
        if not value:
            self.check_form_validity()
            return
            
        # Ensure uppercase
        if value != value.upper():
            self.chassis_var.set(value.upper())
            return
            
        self.check_form_validity()

    def validate_engine(self, *args):
        value = self.engine_var.get()
        if not value:
            self.check_form_validity()
            return
            
        # Ensure uppercase
        if value != value.upper():
            self.engine_var.set(value.upper())
            return
            
        self.check_form_validity()

    def validate_cell_input(self, *args):
        value = self.buyer_cell_var.get()
        # Allow only digits and max 11 chars
        if not value.isdigit() and value != "":
            # Remove non-digits
            cleaned = ''.join(filter(str.isdigit, value))
            if value != cleaned:
                self.buyer_cell_var.set(cleaned)
                return
        
        if len(value) > 11:
            self.buyer_cell_var.set(value[:11])
            return

        self.check_form_validity()

    def check_form_validity(self):
        # List of required fields
        # Ensure all variables are initialized before checking
        if not hasattr(self, 'inv_num_var'):
            return

        required_vars = [
            self.inv_num_var,
            self.buyer_cnic_var,  # Added CNIC
            self.buyer_name_var,
            self.father_name_var,
            self.buyer_cell_var,
            self.buyer_address_var,
            self.chassis_var,
            self.engine_var,
            self.qty_var,
            self.amount_var
        ]

        # Check if all fields have values
        all_filled = all(var.get().strip() for var in required_vars)

        # Specific checks
        cell = self.buyer_cell_var.get()
        cell_valid = len(cell) == 11
        
        cnic = self.buyer_cnic_var.get()
        cnic_valid = len(cnic) == 15 and re.match(r"^\d{5}-\d{7}-\d{1}$", cnic)

        if all_filled and cell_valid and cnic_valid:
            self.submit_btn.configure(state="normal")
        else:
            self.submit_btn.configure(state="disabled")

    def validate_cnic_input(self, *args):
        value = self.buyer_cnic_var.get()
        
        # Remove any non-digit/non-dash characters (though we mainly want to control digits and dashes)
        clean_digits = ''.join(filter(str.isdigit, value))
        
        formatted = clean_digits
        if len(clean_digits) > 5:
             formatted = clean_digits[:5] + '-' + clean_digits[5:]
        if len(clean_digits) > 12:
             formatted = formatted[:13] + '-' + formatted[13:]
             
        # Limit to max chars (13 digits + 2 dashes = 15)
        if len(formatted) > 15:
            formatted = formatted[:15]
            
        if value != formatted:
            self.buyer_cnic_var.set(formatted)
            # If we just reformatted, we can still check if it's complete and valid for lookup
            # But the 'set' will trigger another trace call, so we can let that handle it.
            # HOWEVER, to be robust against race conditions or suppressed events:
            if len(clean_digits) == 13:
                 self.perform_cnic_lookup(formatted)
            return

        # Auto-fill customer details if CNIC is complete (13 digits)
        if len(clean_digits) == 13:
             self.perform_cnic_lookup(formatted)

        self.check_form_validity()

    def perform_cnic_lookup(self, cnic=None):
        """Wrapper to trigger customer lookup."""
        if not cnic:
            cnic = self.buyer_cnic_var.get()
            
        # Ensure it looks like a valid CNIC before querying (13 digits, ignoring dashes)
        clean_digits = ''.join(filter(str.isdigit, cnic))
        if len(clean_digits) == 13:
             self.auto_fill_customer_by_cnic(cnic)

    def auto_fill_customer_by_cnic(self, cnic):
        """Fetches customer details from the last invoice with this CNIC."""
        db = SessionLocal()
        try:
            invoice = invoice_service.get_last_invoice_by_cnic(db, cnic)
            if invoice:
                # Populate fields
                if invoice.buyer_name:
                    self.buyer_name_var.set(invoice.buyer_name)
                if invoice.buyer_father_name:
                    self.father_name_var.set(invoice.buyer_father_name)
                if invoice.buyer_phone:
                    self.buyer_cell_var.set(invoice.buyer_phone)
                if invoice.buyer_address:
                    self.buyer_address_var.set(invoice.buyer_address)
        except Exception as e:
            print(f"Error fetching customer by CNIC: {e}")
        finally:
            db.close()

    def display_qr_code(self, data):
        if not data:
            return
        
        try:
            # Generate QR
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            qr_img_pil = qr.make_image(fill_color="black", back_color="white")
            
            # Resize (PIL Image)
            qr_img_pil = qr_img_pil.resize((150, 150))
            
            # Convert to CTkImage
            self.qr_image = ctk.CTkImage(light_image=qr_img_pil, dark_image=qr_img_pil, size=(150, 150))
            
            self.qr_code_label.configure(image=self.qr_image, text="")
            self.fbr_inv_label.configure(text=data)
        except Exception as e:
            print(f"QR Code Error: {e}")

    def reset_form(self, clear_qr=True):
        self.generate_invoice_number() # Auto-generate next number
        
        # Clear fields (inv_num_entry excluded as it is readonly and set via generate_invoice_number)
        # Note: qty_entry is handled separately below due to state toggle
        for entry in [self.buyer_cnic_entry, self.buyer_name_entry, self.buyer_father_entry,
                     self.buyer_cell_entry, self.buyer_address_entry, self.chassis_entry,
                     self.engine_entry, self.amount_excl_entry,
                     self.tax_entry, self.further_tax_entry, self.total_price_entry]:
            entry.delete(0, 'end')

        # Reset Quantity Logic
        self.manual_qty_var.set(False)
        self.qty_entry.configure(state="normal") # Temporarily enable to clear/set
        self.qty_entry.delete(0, 'end')
        self.qty_entry.insert(0, "1")
        self.qty_entry.configure(state="disabled")
        
        # Clear Dropdowns
        self.model_combo.set("")
        self.color_combo.set("")
        
        # Reset Payment Mode to default (Cash) as it should be populated
        self.payment_mode_combo.set("Cash")
        
        # Reset Chassis Verify Checkbox and Feedback
        self.verify_chassis_var.set(False)
        self.chassis_feedback_label.configure(text="")

        # Reset state
        self.current_levy = 0
        self.current_price_obj = None
        
        # Clear QR Code if requested
        if clear_qr:
             self.qr_code_label.configure(image=None, text="")
             self.qr_image = None
             self.fbr_inv_label.configure(text="")
        # Do not auto-select default model, so fields remain empty
        
        # Focus on ID Card field after reset
        self.after(100, lambda: self.buyer_cnic_entry.focus_set())

    def create_inventory_frame(self):
        self.inventory_frame = InventoryFrame(self, corner_radius=0, fg_color="transparent")
        self.inventory_frame.grid_columnconfigure(0, weight=1)

    def create_reports_frame(self):
        self.reports_frame = ReportsFrame(self, corner_radius=0, fg_color="transparent")
        self.reports_frame.grid_columnconfigure(0, weight=1)

    def create_dealer_frame(self):
        self.dealer_frame = DealerFrame(self, corner_radius=0, fg_color="transparent")
        self.dealer_frame.grid_columnconfigure(0, weight=1)

    def create_print_frame(self):
        self.print_invoice_frame = PrintInvoiceFrame(self, corner_radius=0, fg_color="transparent")
        self.print_invoice_frame.grid_columnconfigure(0, weight=1)

    def create_backup_frame(self):
        self.backup_frame = BackupFrame(self, corner_radius=0, fg_color="transparent")
        self.backup_frame.grid_columnconfigure(0, weight=1)

    def create_captured_data_frame(self):
        self.captured_data_frame = CapturedDataFrame(self, corner_radius=0, fg_color="transparent")
        self.captured_data_frame.grid_columnconfigure(0, weight=1)

    def select_frame_by_name(self, name):
        # Auto-expand menu if the selected item is inside a group
        self.expand_menu_containing(name)

        # set button color for selected button
        if self.home_button: self.home_button.configure(fg_color=("gray75", "gray25") if name == "home" else "transparent")
        if self.inventory_button: self.inventory_button.configure(fg_color=("gray75", "gray25") if name == "inventory" else "transparent")
        if self.invoice_button: self.invoice_button.configure(fg_color=("gray75", "gray25") if name == "invoice" else "transparent")
        if self.reports_button: self.reports_button.configure(fg_color=("gray75", "gray25") if name == "reports" else "transparent")
        if self.dealer_button: self.dealer_button.configure(fg_color=("gray75", "gray25") if name == "dealer" else "transparent")
        if self.backup_button: self.backup_button.configure(fg_color=("gray75", "gray25") if name == "backup" else "transparent")
        if self.print_inv_button: self.print_inv_button.configure(fg_color=("gray75", "gray25") if name == "print_invoice" else "transparent")
        if self.captured_data_button: self.captured_data_button.configure(fg_color=("gray75", "gray25") if name == "captured_data" else "transparent")
        if hasattr(self, "spare_ledger_button") and self.spare_ledger_button:
            self.spare_ledger_button.configure(fg_color=("gray75", "gray25") if name == "spare_ledger" else "transparent")

        # show selected frame
        if name == "home":
            self.home_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.home_frame.grid_forget()
            
        if name == "inventory":
            self.inventory_frame.grid(row=0, column=1, sticky="nsew")
            self.inventory_frame.refresh_inventory()
        else:
            self.inventory_frame.grid_forget()

        if name == "invoice":
            self.invoice_frame.grid(row=0, column=1, sticky="nsew")
            self.generate_invoice_number() # Auto-generate Invoice No
            # Focus on ID Card field when frame is shown
            self.after(100, lambda: self.buyer_cnic_entry.focus_set())
        else:
            self.invoice_frame.grid_forget()

        if name == "reports":
            self.reports_frame.grid(row=0, column=1, sticky="nsew")
            self.reports_frame.load_data()
        else:
            self.reports_frame.grid_forget()

        if name == "dealer":
            self.dealer_frame.grid(row=0, column=1, sticky="nsew")
            self.dealer_frame.load_dealers()
        else:
            self.dealer_frame.grid_forget()

        if name == "backup":
            self.backup_frame.grid(row=0, column=1, sticky="nsew")
            self.backup_frame.refresh_history()
        else:
            self.backup_frame.grid_forget()

        if name == "print_invoice":
            self.print_invoice_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.print_invoice_frame.grid_forget()

        if name == "captured_data":
            self.captured_data_frame.grid(row=0, column=1, sticky="nsew")
            self.captured_data_frame.load_data()
        else:
            self.captured_data_frame.grid_forget()

        if name == "spare_ledger":
            self.spare_ledger_frame.grid(row=0, column=1, sticky="nsew")
            self.spare_ledger_frame.refresh()
        else:
            self.spare_ledger_frame.grid_forget()

    def generate_invoice_number(self):
        """Fetches the next auto-incremented invoice number."""
        db = SessionLocal()
        try:
            next_inv_num = invoice_service.generate_next_invoice_number(db)
            self.inv_num_var.set(next_inv_num)
        except Exception as e:
            print(f"Error generating invoice number: {e}")
            self.inv_num_var.set("ERROR")
        finally:
            db.close()

    def home_button_event(self):
        self.select_frame_by_name("home")

    def inventory_button_event(self):
        self.select_frame_by_name("inventory")

    def invoice_button_event(self):
        self.select_frame_by_name("invoice")

    def reports_button_event(self):
        self.select_frame_by_name("reports")

    def dealer_button_event(self):
        self.select_frame_by_name("dealer")

    def backup_button_event(self):
        self.select_frame_by_name("backup")

    def print_invoice_button_event(self):
        self.select_frame_by_name("print_invoice")



    def captured_data_button_event(self):
        self.select_frame_by_name("captured_data")

    def open_price_list(self):
        PriceListDialog(self)

    def open_fbr_settings(self):
        FBRSettingsDialog(self)

    def form_capture_button_event(self):
        """Launch the Live Form Capture browser"""
        if form_capture_service.is_running:
             messagebox.showinfo("Capture Running", "Form capture is already running.")
             return

        # Default to Atlas Honda Portal as per user request
        target_url = "https://dealers.ahlportal.com/dealersv2/dealers/customer_profile"
        
        # Override if config has specific domains, but prioritize the requested one if empty or default
        if form_capture_service.config.get("target_domains"):
             # Construct URL from domain (assuming https)
             domain = form_capture_service.config["target_domains"][0]
             if not domain.startswith("http"):
                 target_url = f"https://{domain}"
             else:
                 target_url = domain
        
        try:
            form_capture_service.start_capture_session(target_url)
            messagebox.showinfo("Started", "Recording Browser Launched.\n\nInteract with the website as usual.\nData is saved automatically to captured_forms.json.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start capture: {e}")

    def _populate_bike_details(self, bike):
        """Helper to populate form fields from bike object"""
        # Auto-fill Engine
        self.engine_entry.delete(0, "end")
        self.engine_entry.insert(0, bike.engine_number)
        
        # Auto-fill Model & Color
        model_name = bike.product_model.model_name if bike.product_model else None
        if model_name and model_name in self.model_combo._values:
            self.model_combo.set(model_name)
            # Trigger model change logic to update colors and base price
            self.on_model_change(model_name)
        
        # Ensure the bike's color is available in the dropdown
        if bike.color:
            current_colors = self.color_combo._values
            if bike.color not in current_colors:
                 # Add missing color temporarily
                 new_values = list(current_colors) + [bike.color]
                 self.color_combo.configure(values=new_values)
            
            self.color_combo.set(bike.color)
            # Explicitly update price for the specific color
            self.on_color_change(bike.color)
        
        # Handle Price Fallback if no active price found
        if not self.current_price_obj:
            self.amount_excl_entry.delete(0, "end")
            self.amount_excl_entry.insert(0, str(bike.sale_price))
            self.current_levy = 0
            self.calculate_totals() # Trigger tax calc manually since on_model_change didn't do it fully

    def on_verify_chassis_change(self):
        """Trigger re-validation when checkbox state changes."""
        self.auto_fill_chassis()

    def scan_cnic_action(self):
        """Opens file dialog for ID Card Front (and optional Back) and extracts text."""
        if not ocr_service.is_available():
            messagebox.showerror("OCR Unavailable", f"OCR features are disabled.\nReason: {ocr_service.get_error()}")
            return

        try:
            # 1. Ask for Front Image
            front_path = filedialog.askopenfilename(
                title="Select ID Card FRONT Image",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")]
            )
            
            if not front_path:
                return # User cancelled

            # 2. Ask for Back Image (Optional)
            if messagebox.askyesno("Scan Back Side?", "Do you want to scan the BACK side for Address?"):
                back_path = filedialog.askopenfilename(
                    title="Select ID Card BACK Image",
                    filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")]
                )
            else:
                back_path = None
            
            # 3. Show loading indicator (simple)
            original_text = self.scan_btn.cget("text")
            self.scan_btn.configure(text="Scanning...", state="disabled")
            self.update_idletasks()
            
            # 4. Process via Service
            def run_scan():
                try:
                    data = ocr_service.parse_cnic_data(front_path, back_path)
                    
                    # Schedule UI update on main thread
                    def update_ui():
                        if data["cnic"]:
                            self.buyer_cnic_var.set(data["cnic"])
                        if data["name"]:
                            self.buyer_name_var.set(data["name"])
                        if data["father_name"]:
                            self.father_name_var.set(data["father_name"])
                        if data["address"]:
                            self.buyer_address_var.set(data["address"])
                        
                        self.scan_btn.configure(text=original_text, state="normal")
                        messagebox.showinfo("Success", "ID Card scanned successfully!\nPlease verify extracted data.")
                    
                    self.after(0, update_ui)
                    
                except RuntimeError as e:
                    self.after(0, lambda: messagebox.showerror("OCR Error", str(e)))
                    self.after(0, lambda: self.scan_btn.configure(text=original_text, state="normal"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to scan: {str(e)}"))
                    self.after(0, lambda: self.scan_btn.configure(text=original_text, state="normal"))

            # Run in background thread to avoid freezing UI
            threading.Thread(target=run_scan, daemon=True).start()
                
        except Exception as e:
            print(f"Scan Action Error: {e}")
            self.scan_btn.configure(text="📷 Scan ID", state="normal")

    def auto_fill_cnic(self, event=None):
        cnic = self.buyer_cnic_var.get().strip()
        
        # If CNIC is incomplete (assuming 15 chars with dashes), clear fields
        if not cnic or len(cnic) < 15: 
            self.buyer_name_var.set("")
            self.father_name_var.set("")
            self.buyer_cell_var.set("")
            self.buyer_address_var.set("")
            return
            
        db = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.cnic == cnic).first()
            if customer:
                self.buyer_name_var.set(customer.name)
                self.father_name_var.set(customer.father_name or "")
                self.buyer_cell_var.set(customer.phone or "")
                self.buyer_address_var.set(customer.address or "")
        except Exception as e:
            print(f"CNIC Auto-fill error: {e}")
        finally:
            db.close()

    def on_chassis_key_release(self, event=None):
        """Handle key release for suggestion logic"""
        # If special keys (arrows, enter), ignore here as they are handled by separate binds
        if event and event.keysym in ["Down", "Up", "Return", "Escape"]:
            return
            
        self.update_suggestions()
        
        # Check if field was cleared or modified
        self.check_chassis_cleared()
        
        # Restore auto-fill for manual typing
        self.auto_fill_chassis()

    def check_chassis_cleared(self):
        """Clear related fields if chassis is empty or doesn't match a full chassis"""
        chassis = self.chassis_var.get().strip()
        # You can define a minimum length for a valid chassis if needed, e.g. < 5
        if not chassis:
            self.clear_bike_details()
            # self.clear_customer_details() # Keep customer details as per user request

    def clear_bike_details(self):
        """Clear all bike-related fields"""
        self.engine_var.set("")
        self.model_combo.set("")
        self.color_combo.set("")
        self.amount_var.set("")
        self.tax_entry.delete(0, "end")
        self.further_tax_entry.delete(0, "end")
        self.total_price_entry.delete(0, "end")
        self.chassis_feedback_label.configure(text="", text_color="black")

    def clear_customer_details(self):
        self.buyer_cnic_var.set("")
        self.buyer_name_var.set("")
        self.father_name_var.set("")
        self.buyer_cell_var.set("")
        self.buyer_address_var.set("")
        
    def update_suggestions(self):
        query = self.chassis_var.get().strip()
        
        # Hide if empty or too short
        if not query or len(query) < 1:
            self.hide_suggestions()
            return
            
        db = SessionLocal()
        try:
            # Fetch IN_STOCK chassis matching query (limit 10)
            results = db.query(Motorcycle.chassis_number).filter(
                Motorcycle.status == "IN_STOCK",
                Motorcycle.chassis_number.like(f"%{query}%")
            ).limit(10).all()
            
            suggestions = [r[0] for r in results]
            
            if suggestions:
                self.show_suggestions(suggestions)
            else:
                self.hide_suggestions()
                
        except Exception as e:
            print(f"Suggestion error: {e}")
        finally:
            db.close()

    def show_suggestions(self, suggestions):
        # Create Toplevel if not exists
        if self.suggestion_window is None or not self.suggestion_window.winfo_exists():
            self.suggestion_window = ctk.CTkToplevel(self)
            self.suggestion_window.overrideredirect(True)
            self.suggestion_window.attributes("-topmost", True)
            self.suggestion_window.wm_attributes("-topmost", True) # Windows specific
            self.suggestion_window.configure(fg_color=("gray95", "gray20"))
            
            # Create a scrollable frame inside the toplevel
            self.suggestion_frame = ctk.CTkScrollableFrame(self.suggestion_window, corner_radius=0, fg_color="transparent")
            self.suggestion_frame.pack(fill="both", expand=True)
            
        # Clear existing buttons
        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons = []
        
        # Reset selection
        self.selected_suggestion_index = -1
        
        # Populate frame
        for idx, chassis in enumerate(suggestions):
            btn = ctk.CTkButton(
                self.suggestion_frame, 
                text=chassis, 
                anchor="w",
                fg_color="transparent", 
                text_color=("black", "white"),
                hover_color=("gray75", "gray30"),
                corner_radius=0,
                command=lambda c=chassis: self.select_suggestion(c)
            )
            btn.pack(fill="x", padx=0, pady=0)
            self.suggestion_buttons.append(btn)
            
        # Position the window relative to entry (Global Coordinates)
        try:
            root_x = self.chassis_entry.winfo_rootx()
            root_y = self.chassis_entry.winfo_rooty()
            height = self.chassis_entry.winfo_height()
            width = self.chassis_entry.winfo_width()
            
            # Calculate height based on items (max 150)
            req_height = min(len(suggestions) * 30 + 10, 150)
            
            geometry_str = f"{width}x{req_height}+{root_x}+{root_y + height + 2}"
            self.suggestion_window.geometry(geometry_str)
            self.suggestion_window.deiconify() # Ensure visible
            self.suggestion_window.lift() # Ensure on top
        except Exception as e:
            print(f"Error placing suggestion window: {e}")

    def hide_suggestions(self):
        if self.suggestion_window and self.suggestion_window.winfo_exists():
            self.suggestion_window.withdraw()
        self.selected_suggestion_index = -1

    def on_suggestion_nav(self, event):
        if not self.suggestion_window or not self.suggestion_window.winfo_exists() or not self.suggestion_window.winfo_viewable():
            return
            
        count = len(self.suggestion_buttons)
        if count == 0:
            return
            
        if event.keysym == "Down":
            self.selected_suggestion_index = (self.selected_suggestion_index + 1) % count
        elif event.keysym == "Up":
            self.selected_suggestion_index = (self.selected_suggestion_index - 1 + count) % count
            
        self.highlight_suggestion()
        return "break" # Stop default behavior

    def highlight_suggestion(self):
        for i, btn in enumerate(self.suggestion_buttons):
            if i == self.selected_suggestion_index:
                btn.configure(fg_color=("gray70", "gray40"))
                # Try to scroll to item (simple approach)
                # Scrollable frame doesn't support see() easily, but this highlights it
            else:
                btn.configure(fg_color="transparent")

    def on_suggestion_select(self, event=None):
        if self.suggestion_window and self.suggestion_window.winfo_viewable() and self.selected_suggestion_index >= 0:
            text = self.suggestion_buttons[self.selected_suggestion_index].cget("text")
            self.select_suggestion(text)
            return "break"

    def select_suggestion(self, chassis):
        self.chassis_var.set(chassis)
        self.hide_suggestions()
        self.chassis_entry.icursor("end") # Move cursor to end
        # Trigger detail population
        self.auto_fill_chassis()

    def on_chassis_focus_out(self, event):
        # Delay hiding to allow click event on button or scrollbar interaction
        self.after(200, self._check_focus_and_hide)

    def _check_focus_and_hide(self):
        """Check if we should really hide the suggestion window."""
        if not self.suggestion_window or not self.suggestion_window.winfo_exists() or not self.suggestion_window.winfo_viewable():
            return

        # 1. Check if mouse is over the suggestion window
        # This prevents closing while the user is scrolling or hovering
        try:
            x, y = self.suggestion_window.winfo_pointerxy()
            win_x = self.suggestion_window.winfo_rootx()
            win_y = self.suggestion_window.winfo_rooty()
            win_w = self.suggestion_window.winfo_width()
            win_h = self.suggestion_window.winfo_height()
            
            # Add a small buffer/margin
            if (win_x <= x <= win_x + win_w) and (win_y <= y <= win_y + win_h):
                # Mouse is over window, keep checking periodically
                self.after(100, self._check_focus_and_hide)
                return
        except Exception:
            pass

        # 2. Check focus
        # If focus moved to the suggestion window (e.g. scrollbar), keep it open
        focused = self.focus_get()
        if focused:
            # Check if focused widget is part of suggestion window
            if str(focused).startswith(str(self.suggestion_window)):
                self.after(100, self._check_focus_and_hide)
                return
            
            # If focus returned to chassis entry, stop checking (FocusOut will trigger again later)
            if focused == self.chassis_entry:
                return 

        # If neither mouse is over nor focus is inside, hide it
        self.hide_suggestions()

    def auto_fill_chassis(self, event=None):
        """Auto-fill details when chassis is typed"""
        chassis = self.chassis_entry.get()
        if not chassis:
            self.chassis_feedback_label.configure(text="", text_color="black")
            return

        if len(chassis) < 5: # Optimization: don't query for very short strings
            self.chassis_feedback_label.configure(text="", text_color="black")
            return
            
        bypass_verification = self.verify_chassis_var.get()
        
        db = SessionLocal()
        try:
            bike = db.query(Motorcycle).filter(Motorcycle.chassis_number == chassis).first()
            if bike:
                if bike.status == "IN_STOCK":
                    self._populate_bike_details(bike)
                    self.chassis_feedback_label.configure(text="✔", text_color="green")
                else:
                    if bike.status == "SOLD":
                        messagebox.showinfo("Invoice Submitted", "You have allready submitted the invoice")
                        self.clear_customer_details()
                        if bypass_verification:
                            self.chassis_feedback_label.configure(text="⚠️ SOLD", text_color="orange")
                        else:
                            self.chassis_feedback_label.configure(text="Not In Stock", text_color="red")
                        return
                    
                    if bypass_verification:
                        self.chassis_feedback_label.configure(text="⚠️ " + bike.status, text_color="orange")
                    else:
                        self.chassis_feedback_label.configure(text="Not In Stock", text_color="red")
            else:
                if bypass_verification:
                    self.chassis_feedback_label.configure(text="⚠️ Not Found", text_color="orange")
                else:
                    self.chassis_feedback_label.configure(text="Not Found", text_color="red")

            # Populate customer info from captured_data if exists
            try:
                cap = db.query(CapturedData).filter(CapturedData.chassis_number == chassis).first()
                if cap:
                    if cap.cnic:
                        self.buyer_cnic_var.set(cap.cnic)
                    if cap.name:
                        self.buyer_name_var.set(cap.name)
                    if cap.father:
                        self.father_name_var.set(cap.father)
                    if cap.cell:
                        self.buyer_cell_var.set(cap.cell)
                    if cap.address:
                        self.buyer_address_var.set(cap.address)
                    if cap.engine_number and not self.engine_var.get().strip():
                        self.engine_var.set(cap.engine_number)
            except Exception as ce:
                print(f"Captured data lookup error: {ce}")
        except Exception as e:
            print(f"Auto-fill error: {e}")
            self.chassis_feedback_label.configure(text="Error", text_color="red")
        finally:
            db.close()

    def check_stock(self):
        chassis = self.chassis_entry.get()
        if not chassis:
            messagebox.showwarning("Input Required", "Please enter a Chassis Number")
            return
            
        db = SessionLocal()
        try:
            bike = db.query(Motorcycle).filter(Motorcycle.chassis_number == chassis).first()
            if bike:
                status = bike.status
                if status == "IN_STOCK":
                    make = bike.product_model.make if bike.product_model else "Unknown"
                    model = bike.product_model.model_name if bike.product_model else "Unknown"
                    msg = f"Available!\nMake: {make}\nModel: {model}\nColor: {bike.color}\nPrice: {bike.sale_price}"
                    messagebox.showinfo("Stock Check", msg)
                    
                    self._populate_bike_details(bike)
                    
                else:
                    messagebox.showwarning("Stock Check", f"Bike Found but Status is: {status}")
            else:
                messagebox.showerror("Stock Check", "Chassis Number NOT found in Inventory.")
        except Exception as e:
            messagebox.showerror("Error", f"Database error: {e}")
        finally:
            db.close()

    def submit_invoice(self):
        # Visual indication for loading state
        self.submit_btn.configure(state="disabled", text="Submitting...")
        self.update_idletasks()
        try:
            self._process_invoice_submission()
        finally:
            self.submit_btn.configure(state="normal", text="Submit Invoice")

    def _process_invoice_submission(self):
        inv_num = self.inv_num_entry.get()
        buyer_cnic = self.buyer_cnic_entry.get()
        buyer_name = self.buyer_name_entry.get()
        buyer_father = self.buyer_father_entry.get()
        buyer_cell = self.buyer_cell_entry.get()
        buyer_address = self.buyer_address_entry.get()
        payment_mode = self.payment_mode_combo.get()
        
        chassis = self.chassis_entry.get()
        engine = self.engine_entry.get()
        
        try:
            qty = float(self.qty_entry.get().replace(',', '') or 0)
            amount_excl = float(self.amount_excl_entry.get().replace(',', '') or 0)
            # Use calculated or entered tax/total
            tax = float(self.tax_entry.get().replace(',', '') or 0)
            further_tax = float(self.further_tax_entry.get().replace(',', '') or 0)
            total = float(self.total_price_entry.get().replace(',', '') or 0)
        except ValueError:
            messagebox.showerror("Error", "Invalid Number Fields")
            return

        if not inv_num:
            messagebox.showerror("Error", "Invoice Number required")
            return
        if not buyer_name:
            messagebox.showerror("Error", "Buyer Name required")
            return
            
        # Validate CNIC
        if buyer_cnic and not re.match(r"^\d{5}-\d{7}-\d{1}$", buyer_cnic):
             messagebox.showerror("Error", "Invalid CNIC Format.\nMust be: 33302-1234567-0")
             return

        # Validate Cell Number Format (03XXXXXXXXX)
        if buyer_cell and not re.match(r"^03\d{9}$", buyer_cell):
            messagebox.showerror("Error", "Invalid Cell Number.\nFormat must be: 03021523127 (11 digits starting with 03)")
            return

        # --- Chassis Validation Logic ---
        if chassis:
            bypass_verification = self.verify_chassis_var.get()
            
            db_check = SessionLocal()
            try:
                bike = db_check.query(Motorcycle).filter(Motorcycle.chassis_number == chassis).first()
                
                if not bypass_verification:
                    # Case 1: Unchecked (Strict Validation)
                    if not bike:
                        messagebox.showerror("Validation Error", "Chassis number not found in inventory.\nPlease verify or check the box to proceed.")
                        return
                    if bike.status != "IN_STOCK":
                        messagebox.showerror("Validation Error", f"Chassis found but status is {bike.status} (Not IN_STOCK).")
                        return
                else:
                    # Case 2: Checked (Warning Only)
                    if not bike:
                        messagebox.showwarning("Warning", "Proceeding without chassis number verification (Not in DB).")
                    elif bike.status != "IN_STOCK":
                        messagebox.showwarning("Warning", f"Proceeding with chassis status: {bike.status}")
                        
            except Exception as e:
                messagebox.showerror("Database Error", f"Could not validate chassis: {e}")
                return
            finally:
                db_check.close()
        # --------------------------------

        # Create dummy item for simplicity in this UI demo
        model = self.model_combo.get()
        color = self.color_combo.get()
        
        # Calculate standard sales tax rate (just for record)
        # tax (Sales Tax) and further_tax (Levy) are separate now
        # sales_tax_rate = (tax / amount_excl * 100) if amount_excl > 0 else 0
        
        # Fetch dynamic settings
        from app.services.settings_service import settings_service
        settings = settings_service.get_active_settings()
        
        sales_tax_rate = settings.get("tax_rate", 18.0)
        
        # Construct Item Name and Code based on FBR Settings
        # Format: {FBR_SETTING} {MODEL} {COLOR}
        fbr_item_name_base = settings.get("item_name", "Motorcycle") or "Motorcycle"
        fbr_item_code_base = settings.get("item_code", "MOTO") or "MOTO"
        fbr_pct_code = settings.get("pct_code", "8711.2010") or "8711.2010"

        final_item_name = f"{fbr_item_name_base} {model} {color}"
        final_item_code = f"{fbr_item_code_base}-{model}-{color}"

        item = InvoiceItemCreate(
            item_code=final_item_code,
            item_name=final_item_name,
            quantity=qty,
            tax_rate=sales_tax_rate, 
            sale_value=amount_excl, 
            tax_charged=tax,
            further_tax=further_tax,
            pct_code=fbr_pct_code,
            chassis_number=chassis,
            engine_number=engine,
            model_name=model,
            color=color
        )
        
        inv = InvoiceCreate(
            invoice_number=inv_num,
            buyer_cnic=buyer_cnic,
            buyer_name=buyer_name,
            buyer_father_name=buyer_father,
            buyer_phone=buyer_cell,
            buyer_address=buyer_address,
            payment_mode=payment_mode,
            items=[item]
        )

        db = SessionLocal()
        try:
            invoice = invoice_service.create_invoice(db, inv)
            fbr_id = invoice.fbr_invoice_number or "N/A"
            messagebox.showinfo("Success", f"Invoice Created and Queued for Sync\nFBR ID: {fbr_id}")
            
            self.reset_form(clear_qr=False)
            
            if invoice.fbr_invoice_number:
                self.display_qr_code(invoice.fbr_invoice_number)
            
            # Stay on the same screen (reset done above)
        except RetryError as e:
            # Handle FBR Connection/Retry errors
            try:
                last_exception = e.last_attempt.exception()
                if isinstance(last_exception, requests.exceptions.ConnectionError):
                    msg = "Could not connect to FBR Server.\nPlease check your internet connection or FBR URL settings."
                elif isinstance(last_exception, requests.exceptions.Timeout):
                    msg = "Connection to FBR Server timed out."
                else:
                    msg = f"FBR Submission Failed: {str(last_exception)}"
            except:
                msg = f"FBR Submission Error: {str(e)}"
            
            messagebox.showerror("FBR Connection Error", msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            db.close()

if __name__ == "__main__":
    app = App()
    app.mainloop()
