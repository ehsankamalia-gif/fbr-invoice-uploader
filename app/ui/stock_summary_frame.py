import customtkinter as ctk
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
        
        # Load Data
        self.load_data()

    def force_refresh(self):
        """Forces a refresh by resetting the cache hash."""
        self._last_data_hash = None
        self.load_data()

    def load_data(self):
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
            if self._last_data_hash == current_data_hash:
                return
            
            self._last_data_hash = current_data_hash
            
            # Clear existing rows (skip header row 0)
            for widget in self.table_frame.grid_slaves():
                if int(widget.grid_info()["row"]) > 0:
                    widget.destroy()

            total_qty = 0
            row_idx = 1
            
            for i, (model_name, qty) in enumerate(results, 1):
                # S#
                self.create_cell(row_idx, 0, str(i))
                
                # Model
                self.create_cell(row_idx, 1, model_name, anchor="w")
                
                # Qty
                self.create_cell(row_idx, 2, str(qty))
                
                total_qty += qty
                row_idx += 1
                
            # Total Row
            # Add a separator or just a distinct row
            sep = ctk.CTkFrame(self.table_frame, height=2, fg_color="black")
            sep.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=(5, 5))
            row_idx += 1
            
            self.create_cell(row_idx, 0, "")
            self.create_cell(row_idx, 1, "Total", font=("Arial", 14, "bold"))
            self.create_cell(row_idx, 2, str(total_qty), font=("Arial", 14, "bold"))
            
        except Exception as e:
            print(f"Error loading stock summary: {e}")
        finally:
            session.close()

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
