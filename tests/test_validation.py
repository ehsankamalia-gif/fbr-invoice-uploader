import pytest
from unittest.mock import MagicMock
from app.services.dealer_service import dealer_service
from app.db.models import Customer, CustomerType

def test_check_duplicate_dealer():
    # Setup mock
    mock_db = MagicMock()
    dealer_service.db = mock_db
    
    # 1. Test No Duplicate
    # Mock query returning None
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.filter.return_value.first.return_value = None # For exclude_id case
    mock_filter.first.return_value = None
    
    assert dealer_service.check_duplicate_dealer("New Biz", "12345") is False
    
    # 2. Test Duplicate Found
    # Mock query returning a customer
    mock_existing = Customer(id=1, business_name="EXISTING BIZ", cnic="12345")
    mock_filter.first.return_value = mock_existing
    
    assert dealer_service.check_duplicate_dealer("Existing Biz", "12345") is True
    
    # 3. Test Exclude ID (Update scenario)
    # If we update ID=1 with same info, it should NOT be a duplicate
    mock_filter.first.return_value = mock_existing
    # Logic in service: query.filter(...).filter(id != exclude_id).first()
    # We need to mock the chain properly
    
    # Reset mocks for cleaner chain
    mock_db.reset_mock()
    mock_query = mock_db.query.return_value
    mock_filter1 = mock_query.filter.return_value # filter(business, cnic)
    mock_filter2 = mock_filter1.filter.return_value # filter(id != exclude)
    
    # Case A: Update self (not duplicate)
    mock_filter2.first.return_value = None
    assert dealer_service.check_duplicate_dealer("Existing Biz", "12345", exclude_id=1) is False
    
    # Case B: Update to conflict with another (duplicate)
    mock_other = Customer(id=2, business_name="Existing Biz", cnic="12345")
    mock_filter2.first.return_value = mock_other
    assert dealer_service.check_duplicate_dealer("Existing Biz", "12345", exclude_id=1) is True

def test_create_dealer_duplicate_validation():
    # Setup mock
    mock_db = MagicMock()
    dealer_service.db = mock_db
    
    # Mock check_duplicate_dealer to return True
    # We can patch the method on the instance or class, or just mock the DB behavior it relies on.
    # Patching is safer to isolate the create logic.
    
    with pytest.raises(ValueError) as excinfo:
        # Force duplicate check to fail
        # We'll rely on the fact that we can mock the internal call if we patch it
        # But since we are testing integration of logic, let's mock the DB query to return a result
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = Customer(id=1)
        
        dealer_service.create_dealer("12345", "Name", "Father", "Biz", "0300", "Addr")
    
    assert "already exists" in str(excinfo.value)

if __name__ == "__main__":
    # Manually run if executed as script
    try:
        test_check_duplicate_dealer()
        test_create_dealer_duplicate_validation()
        print("All validation tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
