import unittest
import sys
import os
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.server import app
from app.db.session import init_db, SessionLocal
from app.db.models import Price, ProductModel

class TestPriceAPI(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = TestClient(app)
        self.db = SessionLocal()
        # Clean up test data
        self.db.query(Price).filter(
            Price.product_model_id.in_(
                self.db.query(ProductModel.id).filter(ProductModel.model_name.like("API-TEST%"))
            )
        ).delete(synchronize_session=False)
        self.db.commit()

    def tearDown(self):
        self.db.query(Price).filter(
            Price.product_model_id.in_(
                self.db.query(ProductModel.id).filter(ProductModel.model_name.like("API-TEST%"))
            )
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_create_and_get_price(self):
        model = "API-TEST-MODEL"
        payload = {
            "model": model,
            "base_price": 1000.0,
            "tax_amount": 180.0,
            "levy_amount": 20.0,
            "total_price": 1200.0,
            "currency": "Rs",
            "optional_features": {"colors": "Black"}
        }
        
        # Create
        response = self.client.post("/prices", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["model"], model)
        self.assertIsNotNone(data["id"])
        
        # Get Active
        response = self.client.get(f"/prices/{model}/active")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_price"], 1200.0)

    def test_history(self):
        import time
        model = "API-TEST-HISTORY"
        # V1
        self.client.post("/prices", json={
            "model": model, "base_price": 100, "tax_amount": 10, "levy_amount": 0, "total_price": 110
        })
        time.sleep(1) # Ensure timestamp difference for ordering test
        # V2
        self.client.post("/prices", json={
            "model": model, "base_price": 200, "tax_amount": 20, "levy_amount": 0, "total_price": 220
        })
        
        response = self.client.get(f"/prices/{model}/history")
        self.assertEqual(response.status_code, 200)
        history = response.json()
        self.assertTrue(len(history) >= 2)
        self.assertEqual(history[0]["base_price"], 200.0) # Most recent first due to desc order

if __name__ == "__main__":
    unittest.main()
