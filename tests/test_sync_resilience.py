import unittest
from unittest.mock import MagicMock, patch
import threading
import time
import requests
from tenacity import RetryError, Future

# Mock dependencies before importing service
# We need to mock SessionLocal and Invoice
mock_db = MagicMock()
mock_invoice = MagicMock()
mock_invoice.invoice_number = "INV-TEST-001"
mock_invoice.sync_status = "PENDING"

class TestSyncResilience(unittest.TestCase):
    
    @patch('app.services.sync_service.requests.get')
    @patch('app.services.sync_service.SessionLocal')
    @patch('app.services.invoice_service.invoice_service.sync_invoice')
    def test_sync_resume_after_outage(self, mock_sync_invoice, mock_session_cls, mock_get):
        """
        Simulate:
        1. Offline state (Connectivity check fails)
        2. Connection restored
        3. Sync triggered and succeeds
        """
        from app.services.sync_service import SyncService
        
        # Setup DB Mock
        mock_session = mock_session_cls.return_value
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_invoice]
        mock_session.query.return_value.filter.return_value.count.return_value = 1
        
        service = SyncService()
        
        # 1. Simulate Offline
        mock_get.side_effect = requests.RequestException("No Internet")
        service._single_cycle()
        
        self.assertFalse(service.is_online)
        mock_sync_invoice.assert_not_called()
        
        # 2. Simulate Connection Restored
        mock_get.side_effect = None # Success
        mock_get.return_value.status_code = 200
        
        service._single_cycle()
        
        self.assertTrue(service.is_online)
        # Should attempt to sync
        mock_sync_invoice.assert_called_with(mock_session, mock_invoice)

    @patch('app.services.invoice_service.fbr_client.post_invoice')
    def test_sync_invoice_max_retries_network_error(self, mock_post_invoice):
        """
        Verify that if tenacity raises RetryError caused by network issues,
        the invoice stays PENDING (not FAILED).
        """
        from app.services.invoice_service import invoice_service
        
        # Setup mocks
        mock_db = MagicMock()
        mock_inv = MagicMock()
        mock_inv.invoice_number = "INV-NET-FAIL"
        
        # Create a RetryError wrapping a RequestException
        # Tenacity internals are tricky to mock perfectly, so we construct a fake RetryError
        # RetryError(last_attempt)
        mock_future = MagicMock(spec=Future)
        mock_future.exception.return_value = requests.RequestException("Connection timed out")
        retry_error = RetryError(mock_future)
        
        mock_post_invoice.side_effect = retry_error
        
        # Run sync
        invoice_service.sync_invoice(mock_db, mock_inv)
        
        # Verify status is PENDING, not FAILED
        self.assertEqual(mock_inv.sync_status, "PENDING")
        self.assertIn("Network Error", mock_inv.fbr_response_message)

    @patch('app.services.invoice_service.fbr_client.post_invoice')
    def test_sync_invoice_max_retries_logic_error(self, mock_post_invoice):
        """
        Verify that if tenacity raises RetryError caused by Logic Error (e.g. ValueError),
        the invoice becomes FAILED.
        """
        from app.services.invoice_service import invoice_service
        
        mock_db = MagicMock()
        mock_inv = MagicMock()
        mock_inv.invoice_number = "INV-LOGIC-FAIL"
        
        mock_future = MagicMock(spec=Future)
        mock_future.exception.return_value = ValueError("Invalid Data")
        retry_error = RetryError(mock_future)
        
        mock_post_invoice.side_effect = retry_error
        
        invoice_service.sync_invoice(mock_db, mock_inv)
        
        self.assertEqual(mock_inv.sync_status, "FAILED")
        self.assertIn("Failed after retries", mock_inv.fbr_response_message)

if __name__ == '__main__':
    unittest.main()
