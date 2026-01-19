from app.services.captured_form_processor import CapturedFormProcessor
import json

def test_mapping():
    config = {
        "field_mapping": {
            "#txt_chassis_no": "chassis_number",
            "#txt_engine_no": "engine_number",
            "#txt_color": "color",
            "#txt_model": "model_name",
            "#nic1": "buyer_cnic_part1",
            "#nic2": "buyer_cnic_part2",
            "#nic3": "buyer_cnic_part3",
            "#txt_full_name": "buyer_name",
            "#txt_father_name": "buyer_father_name",
            "#txt_address": "buyer_address",
            "#txt_cell_no": "buyer_phone"
        }
    }
    
    processor = CapturedFormProcessor(config)
    
    # Data structure mimicking captured_forms.json
    session_data = {
      "pages": {
        "https://dealers.ahlportal.com/dealersv2/dealers/customer_profile": {
          "fields": {
            "input#txt_chassis_no": {
              "value": "ED185341"
            },
            "input#txt_full_name": {
              "value": "shabir ali"
            },
            "input#txt_father_name": {
              "value": "sabir khan"
            }
          }
        }
      }
    }
    
    # Simulate step 1: Flatten
    flat_data = {}
    pages = session_data.get("pages", {})
    for url, page_data in pages.items():
        fields = page_data.get("fields", {})
        for selector, field_info in fields.items():
            val = field_info.get("value", "")
            flat_data[selector] = val
            
    # Simulate Diagnostic Data (Fallback)
    flat_data["_debug_all_inputs"] = {
        "txt_full_name": "FALLBACK NAME",
        "txt_father_name": "FALLBACK FATHER",
        "txt_address": "FALLBACK ADDRESS"
    }
        
    print("Flat Data:", flat_data)
    
    # Simulate step 2: Map
    mapped = processor._map_data(flat_data)
    print("Mapped Data:", mapped)

if __name__ == "__main__":
    test_mapping()
