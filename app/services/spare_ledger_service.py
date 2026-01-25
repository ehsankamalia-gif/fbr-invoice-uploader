from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.db.session import SessionLocal
from app.db.models import (
    SpareLedgerTransaction,
    SpareLedgerMonthlyClose,
    SpareLedgerAudit,
)

class SpareLedgerService:
    def __init__(self):
        self._db_factory = SessionLocal

    # --- Helpers ---
    def _month_key_for_timestamp(self, ts: datetime) -> str:
        """
        Ledger month cycle: starts on 6th 00:00 and ends on 5th 23:59.
        For a given timestamp, determine the cycle's YYYY-MM using the end month.
        """
        if ts.day <= 5:
            # This belongs to previous month's cycle end
            prev_month = (ts.replace(day=1) - timedelta(days=1))
            return prev_month.strftime("%Y-%m")
        return ts.strftime("%Y-%m")

    def _validate_amount(self, amount: float):
        if amount is None or amount <= 0:
            raise ValueError("Amount must be a positive number")

    def _audit(self, db: Session, action: str, user_id: Optional[int], transaction_id: Optional[int], details: Dict):
        audit = SpareLedgerAudit(
            action=action,
            user_id=user_id,
            transaction_id=transaction_id,
            details=details,
        )
        db.add(audit)

    # --- Transactions ---
    def add_credit(self, amount: float, reference: str = "", description: str = "", user_id: Optional[int] = None, timestamp: Optional[datetime] = None) -> SpareLedgerTransaction:
        self._validate_amount(amount)
        db = self._db_factory()
        try:
            now = timestamp if timestamp else datetime.now()
            txn = SpareLedgerTransaction(
                timestamp=now,
                trans_type="CREDIT",
                amount=amount,
                reference_number=(reference or "").strip(),
                description=(description or "").strip(),
                created_by_user_id=user_id,
                month_key=self._month_key_for_timestamp(now)
            )
            db.add(txn)
            self._audit(db, "CREATE_TXN", user_id, None, {"type": "CREDIT", "amount": amount, "reference": reference, "timestamp": now.isoformat()})
            db.commit()
            db.refresh(txn)
            return txn
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def add_debit(self, amount: float, reference: str = "", description: str = "", user_id: Optional[int] = None, timestamp: Optional[datetime] = None) -> SpareLedgerTransaction:
        self._validate_amount(amount)
        db = self._db_factory()
        try:
            now = timestamp if timestamp else datetime.now()
            txn = SpareLedgerTransaction(
                timestamp=now,
                trans_type="DEBIT",
                amount=amount,
                reference_number=(reference or "").strip(),
                description=(description or "").strip(),
                created_by_user_id=user_id,
                month_key=self._month_key_for_timestamp(now)
            )
            db.add(txn)
            self._audit(db, "CREATE_TXN", user_id, None, {"type": "DEBIT", "amount": amount, "reference": reference, "timestamp": now.isoformat()})
            db.commit()
            db.refresh(txn)
            return txn
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # --- Modification & Deletion ---
    def is_month_closed(self, month_key: str, db: Session = None) -> bool:
        close_db = False
        if db is None:
            db = self._db_factory()
            close_db = True
        try:
            return db.query(SpareLedgerMonthlyClose).filter(SpareLedgerMonthlyClose.month_key == month_key).count() > 0
        finally:
            if close_db:
                db.close()

    def update_transaction(self, txn_id: int, amount: float = None, reference: str = None, description: str = None, trans_type: str = None, timestamp: datetime = None, user_id: Optional[int] = None) -> SpareLedgerTransaction:
        db = self._db_factory()
        try:
            txn = db.query(SpareLedgerTransaction).filter(SpareLedgerTransaction.id == txn_id).first()
            if not txn:
                raise ValueError("Transaction not found")

            # Check if month is closed
            if self.is_month_closed(txn.month_key, db):
                raise ValueError(f"Cannot modify transaction in a closed month ({txn.month_key}). Reopen month first.")
            
            # If timestamp is changing, check new month too
            if timestamp:
                new_month_key = self._month_key_for_timestamp(timestamp)
                if new_month_key != txn.month_key and self.is_month_closed(new_month_key, db):
                    raise ValueError(f"Cannot move transaction to a closed month ({new_month_key}).")

            # Capture old state for audit
            old_state = {
                "amount": txn.amount,
                "reference": txn.reference_number,
                "description": txn.description,
                "type": txn.trans_type,
                "timestamp": txn.timestamp.isoformat(),
                "month_key": txn.month_key
            }

            # Update fields
            if amount is not None:
                self._validate_amount(amount)
                txn.amount = amount
            if reference is not None:
                txn.reference_number = reference.strip()
            if description is not None:
                txn.description = description.strip()
            if trans_type is not None:
                txn.trans_type = trans_type
            if timestamp is not None:
                txn.timestamp = timestamp
                txn.month_key = self._month_key_for_timestamp(timestamp)

            self._audit(db, "UPDATE_TXN", user_id, txn.id, {"old": old_state, "new_amount": amount, "new_ref": reference})
            db.commit()
            db.refresh(txn)
            return txn
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_transaction(self, txn_id: int, user_id: Optional[int] = None):
        db = self._db_factory()
        try:
            txn = db.query(SpareLedgerTransaction).filter(SpareLedgerTransaction.id == txn_id).first()
            if not txn:
                raise ValueError("Transaction not found")

            if self.is_month_closed(txn.month_key, db):
                raise ValueError(f"Cannot delete transaction in a closed month ({txn.month_key}). Reopen month first.")

            # Audit before delete (since ID might be lost effectively, though we store it in audit)
            details = {
                "deleted_transaction_id": txn.id,
                "amount": txn.amount,
                "reference": txn.reference_number,
                "description": txn.description,
                "type": txn.trans_type,
                "month_key": txn.month_key,
                "timestamp": txn.timestamp.isoformat()
            }
            # Unlink any existing audit logs to avoid FK constraint failure
            db.query(SpareLedgerAudit).filter(SpareLedgerAudit.transaction_id == txn_id).update({SpareLedgerAudit.transaction_id: None})
            
            # Log deletion with transaction_id=None
            self._audit(db, "DELETE_TXN", user_id, None, details)
            
            db.delete(txn)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # --- Query & Reporting ---
    def get_month_transactions(self, month_key: str, db: Session = None) -> List[SpareLedgerTransaction]:
        close_db = False
        if db is None:
            db = self._db_factory()
            close_db = True
        try:
            return db.query(SpareLedgerTransaction).filter(SpareLedgerTransaction.month_key == month_key).order_by(SpareLedgerTransaction.timestamp.asc()).all()
        finally:
            if close_db:
                db.close()

    def calculate_month_summary(self, month_key: str, db: Session = None) -> Dict:
        close_db = False
        if db is None:
            db = self._db_factory()
            close_db = True
        try:
            txns = self.get_month_transactions(month_key, db)
            total_credits = sum(t.amount for t in txns if t.trans_type == "CREDIT")
            total_debits = sum(t.amount for t in txns if t.trans_type == "DEBIT")
            # Opening balance is carried_forward from previous close
            prev_close = db.query(SpareLedgerMonthlyClose).filter(SpareLedgerMonthlyClose.month_key == self._previous_month_key(month_key)).first()
            opening = prev_close.closing_balance if prev_close else 0.0
            closing = opening + total_credits - total_debits
            return {
                "opening_balance": opening,
                "total_credits": total_credits,
                "total_debits": total_debits,
                "closing_balance": closing,
            }
        finally:
            if close_db:
                db.close()

    def _previous_month_key(self, month_key: str) -> str:
        dt = datetime.strptime(month_key + "-01", "%Y-%m-%d")
        prev = dt.replace(day=1) - timedelta(days=1)
        return prev.strftime("%Y-%m")

    def get_running_balance(self, month_key: str, db: Session = None) -> List[Tuple[SpareLedgerTransaction, float]]:
        close_db = False
        if db is None:
            db = self._db_factory()
            close_db = True
        try:
            summary = self.calculate_month_summary(self._previous_month_key(month_key), db)
            balance = summary.get("closing_balance", 0.0)
            rows = []
            txns = self.get_month_transactions(month_key, db)
            for t in txns:
                if t.trans_type == "CREDIT":
                    balance += t.amount
                else:
                    balance -= t.amount
                rows.append((t, balance))
            return rows
        finally:
            if close_db:
                db.close()

    def get_all_months_summary(self) -> List[Dict]:
        """
        Returns a list of summaries for all months with activity, calculated dynamically.
        """
        db = self._db_factory()
        try:
            # Get all distinct month keys
            months = db.query(SpareLedgerTransaction.month_key).distinct().order_by(SpareLedgerTransaction.month_key).all()
            if not months:
                return []
            
            month_keys = sorted([m[0] for m in months])
            
            # Fill gaps between min and max month
            start_str = month_keys[0]
            end_str = month_keys[-1]
            
            # Ensure we cover up to current month if max is in past?
            # User might want to see current month even if empty? 
            # Let's stick to transaction range for now to avoid clutter, 
            # or maybe up to today. Let's stick to data range + current if desired.
            # But strictly data range is safer.
            
            start_dt = datetime.strptime(start_str + "-01", "%Y-%m-%d")
            end_dt = datetime.strptime(end_str + "-01", "%Y-%m-%d")
            
            all_months = []
            curr = start_dt
            while curr <= end_dt:
                all_months.append(curr.strftime("%Y-%m"))
                # Next month
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)
            
            results = []
            running_balance = 0.0
            
            for mk in all_months:
                txns = db.query(SpareLedgerTransaction).filter(SpareLedgerTransaction.month_key == mk).all()
                credits = sum(t.amount for t in txns if t.trans_type == "CREDIT")
                debits = sum(t.amount for t in txns if t.trans_type == "DEBIT")
                
                opening = running_balance
                closing = opening + credits - debits
                running_balance = closing
                
                # Calculate Closing Date Label (5th of next month)
                y, m = map(int, mk.split('-'))
                if m == 12:
                    y += 1
                    m = 1
                else:
                    m += 1
                
                # Format: "5, Jan, 2025"
                # using %b for abbreviated month name (Jan, Feb, etc.)
                close_dt = datetime(y, m, 5)
                month_label = close_dt.strftime("5, %b, %Y")
                
                results.append({
                    "month_key": mk,
                    "month_label": month_label,
                    "total_credits": credits,
                    "total_debits": debits,
                    "balance": closing, 
                    "status": "Carried Forward"
                })
            
            return results
        finally:
            db.close()

    # --- Monthly Closing ---
    def close_month(self, month_key: Optional[str] = None, user_id: Optional[int] = None, user_role: str = "admin") -> SpareLedgerMonthlyClose:
        db = self._db_factory()
        try:
            # Basic role-based access control
            if user_role.lower() not in ("admin", "accountant"):
                raise PermissionError("You do not have permission to close the ledger month.")
            if not month_key:
                month_key = self._month_key_for_timestamp(datetime.now())
            # Prevent duplicate closing
            existing = db.query(SpareLedgerMonthlyClose).filter(SpareLedgerMonthlyClose.month_key == month_key).first()
            if existing:
                return existing

            summary = self.calculate_month_summary(month_key, db)
            close_rec = SpareLedgerMonthlyClose(
                month_key=month_key,
                closed_at=datetime.now(),
                opening_balance=summary["opening_balance"],
                total_credits=summary["total_credits"],
                total_debits=summary["total_debits"],
                closing_balance=summary["closing_balance"],
                carried_forward=summary["closing_balance"],
                status="CLOSED",
            )
            db.add(close_rec)
            self._audit(db, "CLOSE_MONTH", user_id, None, {"month_key": month_key, "summary": summary, "user_role": user_role})
            db.commit()
            db.refresh(close_rec)
            return close_rec
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # --- Export ---
    def export_month_csv(self, month_key: str, filepath: str) -> bool:
        import csv
        db = self._db_factory()
        try:
            rows = self.get_running_balance(month_key, db)
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Type", "Amount", "Reference", "Description", "Running Balance"])
                for t, bal in rows:
                    writer.writerow([
                        t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        t.trans_type,
                        f"{t.amount:.2f}",
                        t.reference_number or "",
                        t.description or "",
                        f"{bal:.2f}",
                    ])
            return True
        finally:
            db.close()

    def export_month_html(self, month_key: str, filepath: str) -> bool:
        rows = self.get_running_balance(month_key)
        summary = self.calculate_month_summary(month_key)
        html = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Spare Ledger</title>",
            "<style>body{font-family:Arial} table{border-collapse:collapse;width:100%} th,td{border:1px solid #ddd;padding:8px} th{background:#f5f5f5} .credit{color:green} .debit{color:#c0392b}</style>",
            "</head><body>",
            f"<h2>Spare Parts Ledger - {month_key}</h2>",
            f"<p>Opening: {summary['opening_balance']:.2f} | Total Credits: {summary['total_credits']:.2f} | Total Debits: {summary['total_debits']:.2f} | Closing: {summary['closing_balance']:.2f}</p>",
            "<table><thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Reference</th><th>Description</th><th>Running Balance</th></tr></thead><tbody>"
        ]
        for t, bal in rows:
            cls = "credit" if t.trans_type == "CREDIT" else "debit"
            html.append(f"<tr class='{cls}'><td>{t.timestamp.strftime('%Y-%m-%d %H:%M')}</td><td>{t.trans_type}</td><td>{t.amount:.2f}</td><td>{t.reference_number or ''}</td><td>{t.description or ''}</td><td>{bal:.2f}</td></tr>")
        html.append("</tbody></table></body></html>")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
        return True

    # --- Scheduling ---
    def should_close_now(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now()
        return now.day == 5 and now.hour == 23 and now.minute >= 59

    def auto_close_daily_check(self):
        """
        Call this from a daily timer. If it's 5th 23:59+, perform closing.
        """
        if self.should_close_now():
            self.close_month()


spare_ledger_service = SpareLedgerService()
