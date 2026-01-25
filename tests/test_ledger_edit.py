
import sys
import os
from datetime import datetime, timedelta
import unittest

# Add project root to path
# We need to go up from tests/ -> fbr_invoice_uploader/ -> root
# Actually, the app package is inside fbr_invoice_uploader.
# So we need to add fbr_invoice_uploader to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.spare_ledger_service import spare_ledger_service
from app.db.session import SessionLocal
from app.db.models import SpareLedgerTransaction, SpareLedgerMonthlyClose, SpareLedgerAudit

class TestSpareLedgerEdit(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Clean up test data
        self.db.query(SpareLedgerAudit).delete()
        self.db.query(SpareLedgerTransaction).delete()
        self.db.query(SpareLedgerMonthlyClose).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_update_transaction(self):
        # Create a transaction
        txn = spare_ledger_service.add_credit(100.0, "REF001", "Test Credit")
        txn_id = txn.id
        
        # Update it
        updated_txn = spare_ledger_service.update_transaction(
            txn_id=txn_id,
            amount=150.0,
            reference="REF001-UPD",
            description="Updated Credit"
        )
        
        self.assertEqual(updated_txn.amount, 150.0)
        self.assertEqual(updated_txn.reference_number, "REF001-UPD")
        self.assertEqual(updated_txn.description, "Updated Credit")
        
        # Verify Audit
        audit = self.db.query(SpareLedgerAudit).filter(SpareLedgerAudit.transaction_id == txn_id, SpareLedgerAudit.action == "UPDATE_TXN").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details['old']['amount'], 100.0)
        self.assertEqual(audit.details['new_amount'], 150.0)

    def test_delete_transaction(self):
        txn = spare_ledger_service.add_debit(50.0, "REF002", "Test Debit")
        txn_id = txn.id
        
        spare_ledger_service.delete_transaction(txn_id)
        
        # Verify deletion
        deleted_txn = self.db.query(SpareLedgerTransaction).filter(SpareLedgerTransaction.id == txn_id).first()
        self.assertIsNone(deleted_txn)
        
        # Verify Audit
        # Note: delete_transaction logs the ID in details now, transaction_id is None
        audit = self.db.query(SpareLedgerAudit).filter(SpareLedgerAudit.action == "DELETE_TXN").first()
        self.assertIsNotNone(audit)
        self.assertIsNone(audit.transaction_id)
        self.assertEqual(audit.details['deleted_transaction_id'], txn_id)
        self.assertEqual(audit.details['amount'], 50.0)

    def test_closed_month_restriction(self):
        # 1. Create a transaction in a past month (e.g. 2024-01-10 -> Month Key 2024-01)
        ts = datetime(2024, 1, 10)
        txn = spare_ledger_service.add_credit(100.0, "OLD001", "Old Txn", timestamp=ts)
        
        # 2. Close that month
        spare_ledger_service.close_month("2024-01", user_role="admin")
        
        # 3. Try to update -> Should fail
        with self.assertRaises(ValueError) as cm:
            spare_ledger_service.update_transaction(txn.id, amount=200.0)
        self.assertIn("closed month", str(cm.exception))
        
        # 4. Try to delete -> Should fail
        with self.assertRaises(ValueError) as cm:
            spare_ledger_service.delete_transaction(txn.id)
        self.assertIn("closed month", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
