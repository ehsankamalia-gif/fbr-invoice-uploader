import pytest
from unittest.mock import MagicMock
from app.services.dealer_service import dealer_service
from app.services.customer_service import customer_service
from app.db.models import Customer, CustomerType

def test_cnic_duplication_check_dealer():
    # Setup mock
    mock_db = MagicMock()
    dealer_service.db = mock_db
    
    # Mock CNIC duplicate found
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = Customer(id=1, cnic="33302-1234567-1")
    
    # Check check_duplicate_dealer with CNIC
    result = dealer_service.check_duplicate_dealer("", "33302-1234567-1")
    assert result == "CNIC '33302-1234567-1' already exists."
    
    # Mock No Match
    mock_filter.first.return_value = None
    result = dealer_service.check_duplicate_dealer("", "33302-9999999-9")
    assert result is None

def test_create_dealer_cnic_validation():
    mock_db = MagicMock()
    dealer_service.db = mock_db
    
    # Mock duplicate check returning error
    original_check = dealer_service.check_duplicate_dealer
    dealer_service.check_duplicate_dealer = MagicMock(return_value="CNIC '33302-1234567-1' already exists.")
    
    with pytest.raises(ValueError) as excinfo:
        dealer_service.create_dealer("33302-1234567-1", "Name", "Father", "Business", "0300", "Addr")
    
    assert "CNIC '33302-1234567-1' already exists." in str(excinfo.value)
    
    # Restore
    dealer_service.check_duplicate_dealer = original_check

def test_create_customer_cnic_validation():
    mock_db = MagicMock()
    customer_service.db = mock_db
    
    # Mock duplicate check returning True
    customer_service.check_duplicate_cnic = MagicMock(return_value=True)
    
    with pytest.raises(ValueError) as excinfo:
        customer_service.create_customer("33302-1234567-1", "Name", "Father", "0300", "Addr")
    
    assert "CNIC '33302-1234567-1' already exists." in str(excinfo.value)

if __name__ == "__main__":
    try:
        test_cnic_duplication_check_dealer()
        test_create_dealer_cnic_validation()
        test_create_customer_cnic_validation()
        print("All CNIC validation tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
