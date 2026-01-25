from datetime import datetime
from app.services.spare_ledger_service import spare_ledger_service

def test_summary_calculation_basic():
    # Create fresh transactions
    txn1 = spare_ledger_service.add_credit(1000.0, reference="DEP01")
    txn2 = spare_ledger_service.add_debit(300.0, reference="ORD01")
    mk = txn1.month_key
    summary = spare_ledger_service.calculate_month_summary(mk)
    assert summary["total_credits"] >= 1000.0
    assert summary["total_debits"] >= 300.0
    assert abs(summary["closing_balance"] - (summary["opening_balance"] + summary["total_credits"] - summary["total_debits"])) < 0.0001

