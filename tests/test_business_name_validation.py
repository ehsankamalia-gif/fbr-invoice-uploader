import pytest
from unittest.mock import MagicMock
from app.services.dealer_service import dealer_service
from app.db.models import Customer
from app.utils.string_utils import normalize_business_name

def test_normalization_logic():
    assert normalize_business_name("Honda Center") == "hondacenter"
    assert normalize_business_name("  Honda   Center  ") == "hondacenter"
    assert normalize_business_name("Honda-Center!") == "hondacenter"
    assert normalize_business_name("HÓNDA CÉÑTER") == "hondacenter"
    assert normalize_business_name("Honda&Center") == "hondacenter"
    assert normalize_business_name("") == ""

def test_duplicate_check_logic():
    # Setup mock
    mock_db = MagicMock()
    dealer_service.db = mock_db
    
    # Mock behavior for check_duplicate_dealer
    # It queries: filter(normalized_business_name == norm_name)
    
    # 1. Test Exact Match (Normalized)
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = Customer(id=1, business_name="Honda Center", normalized_business_name="hondacenter")
    
    # Even if input is "HONDA-CENTER", normalization matches "hondacenter"
    assert dealer_service.check_duplicate_dealer("HONDA-CENTER", "123") is True
    
    # 2. Test No Match
    mock_filter.first.return_value = None
    assert dealer_service.check_duplicate_dealer("New Biz", "123") is False

def test_create_dealer_validation():
    mock_db = MagicMock()
    dealer_service.db = mock_db
    
    # Mock duplicate found
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = Customer(id=1)
    
    with pytest.raises(ValueError) as excinfo:
        dealer_service.create_dealer("123", "Name", "Father", "Honda Center", "0300", "Addr")
    
    assert "already exists" in str(excinfo.value)
    
    # Mock no duplicate (Success)
    mock_filter.first.return_value = None
    mock_db.add.return_value = None
    
    result = dealer_service.create_dealer("123", "Name", "Father", "New Biz", "0300", "Addr")
    assert result.normalized_business_name == "newbiz"

if __name__ == "__main__":
    try:
        test_normalization_logic()
        test_duplicate_check_logic()
        test_create_dealer_validation()
        print("All business name validation tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
