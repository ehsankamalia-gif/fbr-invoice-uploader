import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SpareLedgerService:
    def auto_close_daily_check(self):
        logger.info("Auto close daily check triggered")

    def delete_transaction(self, txn_id):
        logger.info(f"Deleting transaction {txn_id}")
        return True

    def update_transaction(self, txn_id, amount, description, reference, date, type):
        logger.info(f"Updating transaction {txn_id}")
        return True

    def add_credit(self, amount, reference, description, timestamp=None):
        logger.info(f"Adding credit: {amount}")
        return True

    def add_debit(self, amount, reference, description, timestamp=None):
        logger.info(f"Adding debit: {amount}")
        return True

    def calculate_month_summary(self, month_key):
        return {
            "opening_balance": 0.0,
            "total_credits": 0.0,
            "total_debits": 0.0,
            "closing_balance": 0.0
        }

    def get_running_balance(self, month_key):
        return []

    def get_all_months_summary(self):
        return []

    def export_month_csv(self, month_key, path):
        return True

    def export_month_html(self, month_key, path):
        return True

    def close_month(self, month_key):
        logger.info(f"Closing month {month_key}")
        return True

spare_ledger_service = SpareLedgerService()
