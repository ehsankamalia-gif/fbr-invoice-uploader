import unittest
from unittest.mock import MagicMock, patch, ANY
import threading
from app.db.models import Invoice, Customer
from datetime import datetime
import customtkinter

# Dummy class to replace CTkFrame for inheritance
class DummyCTkFrame:
    def __init__(self, master=None, **kwargs):
        self.master = master
    
    def grid_columnconfigure(self, *args, **kwargs): pass
    def grid_rowconfigure(self, *args, **kwargs): pass
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def pack_forget(self, *args, **kwargs): pass
    def grid_forget(self, *args, **kwargs): pass
    def after(self, ms, func, *args): pass
    def bind(self, *args, **kwargs): pass
    def configure(self, *args, **kwargs): pass
    def update_idletasks(self, *args, **kwargs): pass
    def destroy(self): pass

class TestReportsInteraction(unittest.TestCase):
    def setUp(self):
        # Mock customtkinter classes globally to prevent GUI creation
        self.frame_patcher = patch('customtkinter.CTkFrame', new=DummyCTkFrame)
        self.frame_patcher.start()
        
        self.tabview_patcher = patch('customtkinter.CTkTabview')
        self.tabview_patcher.start()
        
        self.button_patcher = patch('customtkinter.CTkButton')
        self.button_patcher.start()

        self.entry_patcher = patch('customtkinter.CTkEntry')
        self.entry_patcher.start()
        
        self.label_patcher = patch('customtkinter.CTkLabel')
        self.label_patcher.start()
        
        self.combo_patcher = patch('customtkinter.CTkComboBox')
        self.combo_patcher.start()

        self.font_patcher = patch('customtkinter.CTkFont')
        self.font_patcher.start()
        
        self.stringvar_patcher = patch('customtkinter.StringVar')
        self.stringvar_patcher.start()
        
        self.scrollable_frame_patcher = patch('customtkinter.CTkScrollableFrame')
        self.scrollable_frame_patcher.start()
        
        self.ttk_patcher = patch('app.ui.reports_frame.ttk')
        self.ttk_patcher.start()

        # Import after patching
        from app.ui.reports_frame import ReportsFrame
        self.ReportsFrame = ReportsFrame

    def tearDown(self):
        patch.stopall()

    @patch('app.ui.reports_frame.SessionLocal')
    @patch('customtkinter.CTkToplevel')
    @patch('app.ui.reports_frame.messagebox')
    def test_show_sales_detail_fetches_and_displays(self, mock_msgbox, mock_toplevel, mock_session_local):
        # Setup ReportsFrame
        mock_master = MagicMock()
        frame = self.ReportsFrame(mock_master)
        
        # Mock Treeview
        frame.sales_tree = MagicMock()
        frame.sales_tree.selection.return_value = ["item1"]
        # Ensure values matches what the code expects (date, inv_num, ...)
        frame.sales_tree.item.return_value = {
            'values': ["2023-01-01", "INV-001", "Buyer", "Chassis", "Engine", "1000", "Failed"]
        }
        
        # Mock DB
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.invoice_number = "INV-001"
        mock_invoice.datetime = datetime.now()
        mock_invoice.sync_status = "FAILED"
        mock_invoice.is_fiscalized = False
        mock_invoice.fbr_response_message = "Invalid NTN"
        mock_invoice.items = []
        # Add required fields for dialog
        mock_invoice.customer = None
        mock_invoice.pos_id = 123
        mock_invoice.usin = "USIN123"
        mock_invoice.payment_mode = "Cash"
        mock_invoice.status_updated_at = datetime.now()
        mock_invoice.total_sale_value = 100
        mock_invoice.total_tax_charged = 10
        mock_invoice.total_further_tax = 0
        mock_invoice.discount = 0
        mock_invoice.total_amount = 110
        mock_invoice.fbr_invoice_number = None
        mock_invoice.fbr_response_code = None

        # Fix Query Mocking - simpler approach
        # The code chains: query().options().filter().first()
        # We make sure the chain returns the invoice
        mock_query = MagicMock(name="mock_query")
        mock_db.query.return_value = mock_query
        
        mock_options = MagicMock(name="mock_options")
        mock_query.options.return_value = mock_options
        
        mock_filter = MagicMock(name="mock_filter")
        mock_options.filter.return_value = mock_filter
        
        mock_filter.first.return_value = mock_invoice
        
        # Call the method
        frame.show_sales_detail(None)
        
        # Verify DB interactions
        mock_db.query.assert_called()
        
        # Verify Loading State (cursor change)
        # We can't easily verify 'wait' vs '' sequence on DummyCTkFrame without mocking it better,
        # but we can assume it didn't crash.
        
        # Verify Toplevel creation
        mock_toplevel.assert_called_with(frame)
        dialog_instance = mock_toplevel.return_value
        # Check title includes status (FAILED)
        args, _ = dialog_instance.title.call_args
        self.assertIn("INV-001", args[0])
        self.assertIn("FAILED", args[0])

    @patch('app.ui.reports_frame.SessionLocal')
    @patch('customtkinter.CTkToplevel')
    @patch('app.ui.reports_frame.messagebox')
    def test_show_sales_detail_pending_status(self, mock_msgbox, mock_toplevel, mock_session_local):
        # Setup ReportsFrame
        mock_master = MagicMock()
        frame = self.ReportsFrame(mock_master)
        
        # Mock Treeview
        frame.sales_tree = MagicMock()
        frame.sales_tree.selection.return_value = ["item1"]
        frame.sales_tree.item.return_value = {
            'values': ["2023-01-02", "INV-002", "Buyer", "500", "Pending"]
        }
        
        # Mock DB
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.invoice_number = "INV-002"
        mock_invoice.sync_status = "PENDING" # or whatever logic for pending
        mock_invoice.is_fiscalized = False
        mock_invoice.fbr_response_message = None
        mock_invoice.items = []
        mock_invoice.customer = None
        mock_invoice.total_sale_value = 500
        mock_invoice.total_tax_charged = 50
        mock_invoice.total_further_tax = 0
        mock_invoice.discount = 0
        mock_invoice.total_amount = 550
        
        # Query Chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_options = MagicMock()
        mock_query.options.return_value = mock_options
        mock_filter = MagicMock()
        mock_options.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_invoice
        
        # Call
        frame.show_sales_detail(None)
        
        # Verify
        mock_toplevel.assert_called()
        dialog_instance = mock_toplevel.return_value
        args, _ = dialog_instance.title.call_args
        self.assertIn("INV-002", args[0])
        self.assertIn("PENDING", args[0])

    @patch('app.ui.reports_frame.SessionLocal')
    @patch('customtkinter.CTkToplevel')
    @patch('app.ui.reports_frame.messagebox')
    def test_show_sales_detail_db_error(self, mock_msgbox, mock_toplevel, mock_session_local):
        # Setup ReportsFrame
        mock_master = MagicMock()
        frame = self.ReportsFrame(mock_master)
        
        # Mock Treeview
        frame.sales_tree = MagicMock()
        frame.sales_tree.selection.return_value = ["item1"]
        frame.sales_tree.item.return_value = {
            'values': ["2023-01-03", "INV-003", "Buyer", "500", "Failed"]
        }
        
        # Mock DB Exception
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.side_effect = Exception("DB Connection Failed")
        
        # Call
        frame.show_sales_detail(None)
        
        # Verify Error Message
        mock_msgbox.showerror.assert_called_with("Error", "Failed to fetch invoice details: DB Connection Failed")
        mock_toplevel.assert_not_called()

if __name__ == "__main__":
    unittest.main()
