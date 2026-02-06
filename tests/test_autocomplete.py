import pytest
from unittest.mock import MagicMock, patch
from app.services.dealer_service import dealer_service
from app.db.models import Customer, CustomerType

def test_dealer_search():
    # Mock session
    mock_db = MagicMock()
    dealer_service.db = mock_db
    
    # Mock query result
    mock_customer1 = Customer(business_name="HONDA CENTER", type=CustomerType.DEALER)
    mock_customer2 = Customer(business_name="HONDA CITY", type=CustomerType.DEALER)
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_limit = mock_filter.limit.return_value
    mock_limit.all.return_value = [mock_customer1, mock_customer2]
    
    results = dealer_service.search_dealers_by_business_name("HONDA")
    
    assert len(results) == 2
    assert results[0].business_name == "HONDA CENTER"
    
    # Verify filter call
    # Note: Checking actual filter args with SQLAlchemy mocks is complex, 
    # but we can check if filter was called.
    assert mock_query.filter.called

if __name__ == "__main__":
    test_dealer_search()
    print("Test passed!")
