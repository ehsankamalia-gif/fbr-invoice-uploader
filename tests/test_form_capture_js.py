import pytest
from playwright.sync_api import sync_playwright
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the service class
# We need to mock dependencies that might cause side effects on import or init
with patch('app.services.captured_form_processor.CapturedFormProcessor'):
    from app.services.form_capture_service import FormCaptureService

def test_form_capture_td_extraction():
    """
    Verifies that the injection script correctly captures data from both
    Input fields and Table Data (TD) cells, including handling whitespace and mixed content.
    """
    # 1. Setup Service and Script
    # We use a fresh instance or the singleton. 
    # Since it's a singleton, we modify the existing instance's config.
    service = FormCaptureService()
    
    # Mock config to include our test selectors
    # We want to capture:
    # 1. An input field (backward compatibility)
    # 2. A TD with ID (new feature)
    # 3. A TD with Class (new feature)
    service.config = {
        "debounce_ms": 100,
        "include_selectors": ["#name_input", "#father_td", ".mixed-cell"],
        "exclude_selectors": [],
        "submit_selector": "#submit_btn",
        "login_config": {}
    }
    
    script = service._get_injection_script()
    
    # 2. HTML Content
    # - name_input: Standard input
    # - father_td: TD with ID and whitespace
    # - mixed-cell: TD with class, containing text and children
    html_content = """
    <html>
        <body>
            <form>
                <input id="name_input" value="John Doe">
                <table>
                    <tbody>
                        <tr>
                            <td>Father Name:</td>
                            <td id="father_td">
                                Michael Doe   
                            </td>
                        </tr>
                        <tr>
                            <td class="mixed-cell">
                                 <span>Start</span>
                                 <b>Middle</b>
                                 End
                            </td>
                        </tr>
                    </tbody>
                </table>
                <button id="submit_btn" type="button">Submit</button>
            </form>
        </body>
    </html>
    """

    # 3. Playwright Execution
    captured_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Expose python binding
        def py_capture(data):
            captured_data.append(data)
            
        page.expose_function("py_capture", py_capture)
        
        page.set_content(html_content)
        
        # Inject script
        page.evaluate(script)
        
        # Wait for initial capture (setTimeout 1000ms in script)
        page.wait_for_timeout(2000)
        
        # 4. Simulate a change in TD (MutationObserver test)
        # Change father name text
        page.evaluate("""
            document.getElementById('father_td').innerText = "Updated Father";
        """)
        
        # Wait for debounce/mutation observer
        page.wait_for_timeout(1000)
        
        browser.close()
        
    # 5. Assertions
    print("Captured Data:", json.dumps(captured_data, indent=2))
    
    # A. Check Input Field (Backward Compatibility)
    name_captures = [d for d in captured_data if '#name_input' in d['selector']]
    assert len(name_captures) > 0, "Failed to capture input field"
    assert name_captures[0]['value'] == "John Doe"
    
    # B. Check TD with ID (Initial Load)
    father_captures = [d for d in captured_data if '#father_td' in d['selector']]
    assert len(father_captures) > 0, "Failed to capture TD field"
    # Should capture initial value (trimmed)
    initial_father = next(d for d in father_captures if "Michael Doe" in d['value'])
    assert initial_father['value'] == "Michael Doe", f"Expected 'Michael Doe', got '{initial_father['value']}'"
    
    # C. Check TD Mutation
    updated_father = next((d for d in father_captures if "Updated Father" in d['value']), None)
    assert updated_father is not None, "Failed to capture TD mutation update"
    assert updated_father['value'] == "Updated Father"
    
    # D. Check Mixed Cell (Class Selector)
    # Since .mixed-cell doesn't have an ID, getCssSelector will generate a path.
    # But the capture logic triggers because matches('.mixed-cell') is true.
    # We verify that we got data for that element.
    # The text content should be "Start Middle End" (approx)
    mixed_captures = [d for d in captured_data if "Start" in d['value'] and "End" in d['value']]
    assert len(mixed_captures) > 0, "Failed to capture mixed content TD"
    
    # E. Check Label-Based Extraction (Simulating Read-Only View)
    # We expect the script to find "Full Name :" and capture "MUSAA"
    # masquerading as #txt_full_name (which is missing in the HTML)
    label_captures = [d for d in captured_data if d['selector'] == '#txt_full_name']
    # Filter out the one from the input if both exist? 
    # In our HTML, we have input id="name_input". We don't have #txt_full_name.
    # Wait, the config above used #name_input. 
    # Let's add a test case for a MISSING input but PRESENT label.
    
    print("All tests passed!")

def test_label_based_extraction():
    """
    Verifies that the script captures data based on text labels when the configured ID is missing.
    """
    service = FormCaptureService()
    service.config = {
        "debounce_ms": 100,
        "include_selectors": ["#txt_full_name", "#txt_father_name"], 
        "exclude_selectors": [],
        "submit_selector": "#submit_btn",
        "login_config": {}
    }
    
    script = service._get_injection_script()
    
    # HTML with NO inputs for these fields, just text in table
    html_content = """
    <html>
        <body>
            <table>
                <tbody>
                    <tr>
                        <td>Full Name :</td>
                        <td>MUSAA</td>
                    </tr>
                    <tr>
                        <td>Father / Husband Name :</td>
                        <td>M BAKHSH</td>
                    </tr>
                </tbody>
            </table>
        </body>
    </html>
    """

    captured_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        def py_capture(data):
            captured_data.append(data)
            
        page.expose_function("py_capture", py_capture)
        page.set_content(html_content)
        page.evaluate(script)
        page.wait_for_timeout(2000)
        browser.close()
        
    print("Captured Data (Label Test):", json.dumps(captured_data, indent=2))
    
    # Verify Full Name
    full_name = next((d for d in captured_data if d['selector'] == '#txt_full_name'), None)
    assert full_name is not None, "Failed to capture Full Name via label"
    assert full_name['value'] == "MUSAA"
    
    # Verify Father Name
    father_name = next((d for d in captured_data if d['selector'] == '#txt_father_name'), None)
    assert father_name is not None, "Failed to capture Father Name via label"
    assert father_name['value'] == "M BAKHSH"

def test_complex_layouts():
    """
    Verifies label-based extraction in complex scenarios:
    1. Nested tables (Label in TD -> Table -> TR -> TD)
    2. Mixed layouts (Label in TD, Value in Input in next TD)
    3. Colon separation and cleanup
    4. Edge cases
    """
    service = FormCaptureService()
    service.config = {
        "debounce_ms": 100,
        "include_selectors": ["#txt_full_name", "#txt_father_name"], 
        "exclude_selectors": [],
        "submit_selector": "#submit_btn",
        "login_config": {}
    }
    
    script = service._get_injection_script()
    
    html_content = """
    <html>
        <body>
            <div id="main-container">
                <!-- Case 1: Nested Table Structure -->
                <table>
                    <tr>
                        <td>
                            <table>
                                <tr>
                                    <td>
                                        <span>Full Name :</span>
                                    </td>
                                    <td>
                                        <strong>NESTED NAME</strong>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <!-- Case 2: Mixed Layout (Label in TD, Value is Input) -->
                <!-- The label strategy should find the input's value if it's the next element -->
                <table>
                    <tr>
                        <td>Father / Husband Name</td>
                        <td>
                            <input type="text" value="MIXED FATHER" readonly>
                        </td>
                    </tr>
                </table>
            </div>
        </body>
    </html>
    """

    captured_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        def py_capture(data):
            captured_data.append(data)
            
        page.expose_function("py_capture", py_capture)
        page.set_content(html_content)
        page.evaluate(script)
        page.wait_for_timeout(2000)
        browser.close()
        
    print("Captured Data (Complex Test):", json.dumps(captured_data, indent=2))
    
    # 1. Verify Nested Table Extraction (Full Name)
    full_name = next((d for d in captured_data if d['selector'] == '#txt_full_name'), None)
    assert full_name is not None, "Failed to capture Nested Full Name"
    assert full_name['value'] == "NESTED NAME"
    assert full_name.get('label_found') == "Full Name", "Incorrect label match"

    # 2. Verify Mixed Layout Extraction (Father Name)
    father_name = next((d for d in captured_data if d['selector'] == '#txt_father_name'), None)
    assert father_name is not None, "Failed to capture Mixed Layout Father Name"
    assert father_name['value'] == "MIXED FATHER"

if __name__ == "__main__":
    test_form_capture_td_extraction()
    test_label_based_extraction()
    test_complex_layouts()
