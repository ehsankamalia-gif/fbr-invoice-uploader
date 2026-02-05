
import pytest
from app.api.fbr_client import FBRClient

def test_fbr_cnic_format():
    client = FBRClient()
    
    # Input data with dashes (15 chars)
    data = {
        "invoice_number": "INV-001",
        "buyer_cnic": "33303-1234567-1", # 13 digits + 2 dashes
        "items": []
    }
    settings = {}
    
    # Transform
    payload = client._transform_to_fbr_format(data, settings)
    
    # Check what is currently being sent
    cnic_sent = payload["BuyerCNIC"]
    print(f"Sent CNIC: {cnic_sent}")
    
    # Current behavior (Bug): It sends with dashes
    # If FBR truncates to 13 chars, it becomes "33303-1234567" (12 digits)
    
    # Desired behavior: It should be "3330312345671" (13 digits)
    assert len(cnic_sent) == 13, f"CNIC length is {len(cnic_sent)}, expected 13"
    assert cnic_sent.isdigit(), "CNIC should be digits only"
