import customtkinter as ctk
import threading
from app.db.session import SessionLocal
from app.db.models import Motorcycle, ProductModel
from sqlalchemy import func

class StockSummaryFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Title / Header
        self.header_label = ctk.CTkLabel(
            self, 
            text="Bike Stock Summary", 
            font=("Arial", 18, "bold")
        )
        self.header_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Refresh Button
        self.refresh_btn = ctk.CTkButton(
            self,
            text="⟳",
            width=30,
            height=30,
            font=("Arial", 16, "bold"),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray30"),
            command=self.force_refresh
        )
        self.refresh_btn.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="e")
        
        # Table Frame
        self.table_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.table_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # Define columns: (Name, Width, Weight)
        self.columns = [
            ("S#", 40, 0),
            ("Model", 150, 1),
            ("Qty", 60, 0)
        ]
        
        # Create Headers
        for i, (col_name, width, weight) in enumerate(self.columns):
            self.table_frame.grid_columnconfigure(i, weight=weight)
            header = ctk.CTkLabel(
                self.table_frame, 
                text=col_name, 
                font=("Arial", 14, "bold"),
                fg_color="#34495E",  # Dark header background
                text_color="white",
                corner_radius=4,
                height=30
            )
            header.grid(row=0, column=i, padx=1, pady=1, sticky="ew")
            if width:
                header.configure(width=width)

        # State for caching to prevent flickering
        self._last_data_hash = None
        
        # UI Cache
        self.data_rows = [] # List of [lbl_s, lbl_model, lbl_qty]
        self.total_widgets = None # Will hold (sep, lbl_empty, lbl_title, lbl_val)
        
        # Load Data
        self.load_data()

    def force_refresh(self):
        """Forces a refresh by resetting the cache hash."""
        self._last_data_hash = None
        self.load_data()

    def load_data(self):
        """Starts background thread to load data."""
        threading.Thread(target=self._load_data_thread, daemon=True).start()

    def _load_data_thread(self):
        session = SessionLocal()
        try:
            # Query to get stock count per model
            # Filter by status='IN_STOCK' and join with ProductModel
            results = session.query(
                ProductModel.model_name, 
                func.count(Motorcycle.id)
            ).join(Motorcycle).filter(
                Motorcycle.status == 'IN_STOCK'
            ).group_by(
                ProductModel.model_name
            ).order_by(
                ProductModel.model_name
            ).all()
            
            # Check if data has changed to avoid unnecessary UI rebuilds (prevents flickering)
            current_data_hash = hash(tuple(results))
            
            # Optimization: Check hash here to avoid scheduling UI update if not needed
            if self._last_data_hash == current_data_hash:
                return
            
            if self.winfo_exists():
                self.after(0, lambda: self._update_ui(results, current_data_hash))
            
        except Exception as e:
            print(f"Error loading stock summary: {e}")
        finally:
            session.close()

    def _update_ui(self, results, current_data_hash):
        """Updates the table UI on main thread with widget reuse to prevent flickering."""
        if not self.winfo_exists(): return
        
        # Double check hash in case it changed in between
        if self._last_data_hash == current_data_hash:
            return
            
        self._last_data_hash = current_data_hash
        
        total_qty = 0
        
        # Iterate through data and update/create rows
        for i, (model_name, qty) in enumerate(results):
            row_idx = i
            grid_row = row_idx + 1 # Header is 0
            
            # Check if we have widgets for this row
            if row_idx < len(self.data_rows):
                # Update existing widgets
                widgets = self.data_rows[row_idx]
                
                # Update text only if changed
                if widgets[0].cget("text") != str(i + 1):
                    widgets[0].configure(text=str(i + 1))
                
                if widgets[1].cget("text") != str(model_name):
                    widgets[1].configure(text=str(model_name))
                    
                if widgets[2].cget("text") != str(qty):
                    widgets[2].configure(text=str(qty))
                    
                # Ensure they are visible and in correct position
                if not widgets[0].winfo_viewable() or int(widgets[0].grid_info().get("row", -1)) != grid_row:
                    widgets[0].grid(row=grid_row, column=0, padx=1, pady=1, sticky="ew")
                    widgets[1].grid(row=grid_row, column=1, padx=1, pady=1, sticky="ew")
                    widgets[2].grid(row=grid_row, column=2, padx=1, pady=1, sticky="ew")
            else:
                # Create new widgets
                lbl_s = self.create_cell(grid_row, 0, str(i + 1))
                lbl_model = self.create_cell(grid_row, 1, str(model_name), anchor="w")
                lbl_qty = self.create_cell(grid_row, 2, str(qty))
                self.data_rows.append([lbl_s, lbl_model, lbl_qty])
            
            total_qty += qty

        # Hide excess rows
        for j in range(len(results), len(self.data_rows)):
            widgets = self.data_rows[j]
            for w in widgets:
                w.grid_forget()

        # Update Total Row
        total_row_idx = len(results) + 1
        
        if self.total_widgets is None:
            # Create total widgets once
            sep = ctk.CTkFrame(self.table_frame, height=2, fg_color="black")
            lbl_empty = self.create_cell(total_row_idx + 1, 0, "") # Temp row
            lbl_title = self.create_cell(total_row_idx + 1, 1, "Total", font=("Arial", 14, "bold"))
            lbl_val = self.create_cell(total_row_idx + 1, 2, str(total_qty), font=("Arial", 14, "bold"))
            self.total_widgets = (sep, lbl_empty, lbl_title, lbl_val)
        
        # Unpack
        sep, lbl_empty, lbl_title, lbl_val = self.total_widgets
        
        # Update Total Value
        if lbl_val.cget("text") != str(total_qty):
            lbl_val.configure(text=str(total_qty))
            
        # Place Total Row
        sep.grid(row=total_row_idx, column=0, columnspan=3, sticky="ew", pady=(5, 5))
        lbl_empty.grid(row=total_row_idx + 1, column=0, padx=1, pady=1, sticky="ew")
        lbl_title.grid(row=total_row_idx + 1, column=1, padx=1, pady=1, sticky="ew")
        lbl_val.grid(row=total_row_idx + 1, column=2, padx=1, pady=1, sticky="ew")

    def create_cell(self, row, col, text, font=("Arial", 12), anchor="center"):
        label = ctk.CTkLabel(
            self.table_frame,
            text=text,
            font=font,
            fg_color=("white", "#2b2b2b"), # Adaptive background
            corner_radius=0,
            height=25,
            anchor=anchor
        )
        # Add a subtle border effect by using padding on the frame if we want, 
        # or just simple labels. The user image shows grid lines.
        # To simulate grid lines in customtkinter, we can put a frame with background color 
        # behind the cells, and give cells a margin.
        # Here I'll stick to simple layout first.
        label.grid(row=row, column=col, padx=1, pady=1, sticky="ew")
        return label
