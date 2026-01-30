import unittest
from unittest.mock import MagicMock, patch
import datetime
import requests
from app.db.models import Invoice

class TestInvoiceState(unittest.TestCase):
    
    @patch('app.services.invoice_service.fbr_client.post_invoice')
    def test_sync_success_state(self, mock_post_invoice):
        """Test transition from PENDING to SYNCED"""
        from app.services.invoice_service import invoice_service
        
        mock_db = MagicMock()
        mock_inv = Invoice(
            invoice_number="INV-SUCCESS",
            sync_status="PENDING",
            is_fiscalized=False,
            status_updated_at=None
        )
        
        # Simulate Success
        mock_post_invoice.return_value = {
            "InvoiceNumber": "FBR-123",
            "Code": "100",
            "Response": "Success"
        }
        
        invoice_service.sync_invoice(mock_db, mock_inv)
        
        self.assertEqual(mock_inv.sync_status, "SYNCED")
        self.assertTrue(mock_inv.is_fiscalized)
        self.assertIsNotNone(mock_inv.status_updated_at)
        
        # Verify timestamp is recent (within 5 seconds to be safe)
        time_diff = (datetime.datetime.utcnow() - mock_inv.status_updated_at).total_seconds()
        self.assertTrue(time_diff < 5, f"Timestamp too old: {time_diff}s")

    @patch('app.services.invoice_service.fbr_client.post_invoice')
    def test_sync_fail_logic_state(self, mock_post_invoice):
        """Test transition from PENDING to FAILED (Logic Error)"""
        from app.services.invoice_service import invoice_service
        
        mock_db = MagicMock()
        mock_inv = Invoice(
            invoice_number="INV-FAIL",
            sync_status="PENDING",
            is_fiscalized=False,
            status_updated_at=None
        )
        
        # Simulate Logic Failure (API returns but with error)
        mock_post_invoice.return_value = {
            "Code": "400",
            "Response": "Invalid NTN"
        }
        
        invoice_service.sync_invoice(mock_db, mock_inv)
        
        self.assertEqual(mock_inv.sync_status, "FAILED")
        self.assertFalse(mock_inv.is_fiscalized)
        self.assertIsNotNone(mock_inv.status_updated_at)
        self.assertEqual(mock_inv.fbr_response_message, "Invalid NTN")

    @patch('app.services.invoice_service.fbr_client.post_invoice')
    def test_sync_network_error_state(self, mock_post_invoice):
        """Test transition PENDING -> PENDING (Network Error)"""
        from app.services.invoice_service import invoice_service
        
        mock_db = MagicMock()
        mock_inv = Invoice(
            invoice_number="INV-NET",
            sync_status="PENDING",
            is_fiscalized=False,
            status_updated_at=None
        )
        
        # Simulate Network Error
        mock_post_invoice.side_effect = requests.RequestException("No Connection")
        
        invoice_service.sync_invoice(mock_db, mock_inv)
        
        self.assertEqual(mock_inv.sync_status, "PENDING")
        self.assertFalse(mock_inv.is_fiscalized)
        self.assertIsNotNone(mock_inv.status_updated_at)
        self.assertIn("Network Error", mock_inv.fbr_response_message)

if __name__ == '__main__':
    unittest.main()
