import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.db.models import Price, ProductModel
from app.services.price_service import price_service
from app.db.session import init_db, SessionLocal

class TestPriceService(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        # Clean up prices for test isolation
        # First delete prices associated with test models
        self.db.query(Price).filter(
            Price.product_model_id.in_(
                self.db.query(ProductModel.id).filter(ProductModel.model_name.like("TEST%"))
            )
        ).delete(synchronize_session=False)
        # Then delete the product models themselves if needed, but Price delete is main concern
        # Actually, let's just delete Prices for now.
        self.db.commit()

    def tearDown(self):
        self.db.query(Price).filter(
            Price.product_model_id.in_(
                self.db.query(ProductModel.id).filter(ProductModel.model_name.like("TEST%"))
            )
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_add_and_get_price(self):
        model = "TEST-MODEL-A"
        p = price_service.add_price(model, 100, 18, 2, 120, {"colors": "Red"}, db=self.db)
        
        self.assertIsNotNone(p.id)
        self.assertEqual(p.model, model)
        self.assertEqual(p.base_price, 100)
        self.assertIsNone(p.expiration_date)
        
        # Fetch active
        fetched = price_service.get_active_price(model, db=self.db)
        self.assertEqual(fetched.id, p.id)

    def test_versioning(self):
        model = "TEST-MODEL-B"
        # Version 1
        p1 = price_service.add_price(model, 100, 18, 2, 120, db=self.db)
        
        # Version 2
        p2 = price_service.add_price(model, 200, 36, 4, 240, db=self.db)
        
        # Check p1 expired
        p1_refreshed = self.db.query(Price).get(p1.id)
        self.assertIsNotNone(p1_refreshed.expiration_date)
        
        # Check p2 active
        p2_refreshed = self.db.query(Price).get(p2.id)
        self.assertIsNone(p2_refreshed.expiration_date)
        
        # Check get_active returns p2
        active = price_service.get_active_price(model, db=self.db)
        self.assertEqual(active.id, p2.id)

    def test_historical_lookup(self):
        import time
        model = "TEST-HISTORY-LOOKUP"
        
        # T0: Start
        p1 = price_service.add_price(model, 100, 10, 0, 110, db=self.db)
        time.sleep(1) # Ensure measurable time gap
        
        # T1: Update price
        p2 = price_service.add_price(model, 200, 20, 0, 220, db=self.db)
        
        # Query at p1 effective time (should be p1)
        found_p1 = price_service.get_price_at_date(model, p1.effective_date, db=self.db)
        self.assertEqual(found_p1.id, p1.id)
        
        # Query at p2 effective time (should be p2)
        found_p2 = price_service.get_price_at_date(model, p2.effective_date, db=self.db)
        self.assertEqual(found_p2.id, p2.id)
        
        # Query in between (should be p1)
        # p1 is effective until p2.effective_date
        # So check midpoint
        midpoint = p1.effective_date + (p2.effective_date - p1.effective_date) / 2
        found_mid = price_service.get_price_at_date(model, midpoint, db=self.db)
        self.assertEqual(found_mid.id, p1.id)
        
        # Query before T0 (should be None)
        found_none = price_service.get_price_at_date(model, p1.effective_date - timedelta(days=1), db=self.db)
        self.assertIsNone(found_none)

    def test_validation(self):
        with self.assertRaises(ValueError):
            price_service.add_price("TEST-BAD", -100, 0, 0, 0, db=self.db)

    def test_bulk_performance(self):
        import time
        start_time = time.time()
        
        data = []
        for i in range(100):
            data.append({
                "model": f"TEST-BULK-{i}",
                "base_price": 100,
                "tax": 10,
                "levy": 0,
                "total": 110
            })
            
        # Naive bulk insert (could be optimized but testing service logic)
        for item in data:
            price_service.add_price(**item, db=self.db)
            
        end_time = time.time()
        duration = end_time - start_time
        print(f"\nBulk insert of 100 prices took {duration:.2f}s")
        
        # Verify
        count = self.db.query(Price).join(ProductModel).filter(ProductModel.model_name.like("TEST-BULK-%")).count()
        self.assertEqual(count, 100)

if __name__ == "__main__":
    unittest.main()
