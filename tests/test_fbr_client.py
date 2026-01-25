import pytest
from unittest.mock import MagicMock, patch
from app.api.fbr_client import FBRClient
from app.api.schemas import InvoiceCreate, InvoiceItemCreate

@pytest.fixture
def invoice_data():
    return {
        "invoice_number": "INV-001",
        "datetime": None,
        "buyer_name": "John Doe",
        "items": [
            {
                "item_code": "1",
                "item_name": "Test Item",
                "quantity": 1,
                "tax_rate": 17.0,
                "sale_value": 100.0,
                "total_amount": 117.0
            }
        ]
    }

def test_transform_to_fbr_format(invoice_data):
    client = FBRClient()
    fbr_data = client._transform_to_fbr_format(invoice_data)
    
    assert fbr_data["InvoiceNumber"] == "INV-001"
    assert len(fbr_data["Items"]) == 1
    assert fbr_data["Items"][0]["ItemCode"] == "1"

@patch("requests.post")
def test_post_invoice_success(mock_post, invoice_data):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"InvoiceNumber": "FBR-123456", "Response": "Success"}
    mock_post.return_value = mock_response

    client = FBRClient()
    response = client.post_invoice(invoice_data)
    
    assert response["InvoiceNumber"] == "FBR-123456"
    mock_post.assert_called_once()
