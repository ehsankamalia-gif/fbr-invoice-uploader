import unittest
from unittest.mock import MagicMock, patch
from app.services.sync_service import SyncService
from app.db.models import Invoice

class TestSyncRetry(unittest.TestCase):
    def setUp(self):
        self.sync_service = SyncService()
        self.sync_service._stop_event = MagicMock()
        self.sync_service._stop_event.is_set.return_value = False

    @patch("app.services.sync_service.SessionLocal")
    @patch("app.services.sync_service.invoice_service")
    def test_process_queue_commits_changes(self, mock_invoice_service, mock_session_local):
        # Setup mock DB session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Setup pending invoice
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.invoice_number = "INV-001"
        mock_invoice.sync_status = "PENDING"
        
        # Mock query results
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.all.return_value = [mock_invoice]
        
        # Run _process_queue
        self.sync_service._process_queue()
        
        # Verify sync_invoice was called
        mock_invoice_service.sync_invoice.assert_called_once_with(mock_db, mock_invoice)
        
        # Verify commit was called (THIS IS THE KEY FIX)
        mock_db.commit.assert_called_once()
        
        # Verify close was called
        mock_db.close.assert_called_once()

    @patch("app.services.sync_service.SessionLocal")
    @patch("app.services.sync_service.invoice_service")
    def test_process_queue_handles_exception_and_rollbacks(self, mock_invoice_service, mock_session_local):
        # Setup mock DB session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Setup pending invoice
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.invoice_number = "INV-ERR"
        mock_invoice.sync_status = "PENDING"
        
        # Mock query results
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.all.return_value = [mock_invoice]
        
        # Make sync_invoice raise exception
        mock_invoice_service.sync_invoice.side_effect = Exception("Unexpected Error")
        
        # Run _process_queue
        self.sync_service._process_queue()
        
        # Verify commit was NOT called
        mock_db.commit.assert_not_called()
        
        # Verify rollback WAS called
        mock_db.rollback.assert_called_once()
        
        # Verify close was called
        mock_db.close.assert_called_once()

if __name__ == "__main__":
    unittest.main()
