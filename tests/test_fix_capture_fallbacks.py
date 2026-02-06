import pytest
from playwright.sync_api import sync_playwright
from unittest.mock import patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with patch('app.services.captured_form_processor.CapturedFormProcessor'):
    from app.services.form_capture_service import FormCaptureService

def test_fallback_strategies_for_missing_fields():
    """
    Verifies that the injection script recovers Engine, Color, and Model
    from text labels when input fields are missing or empty.
    """
    service = FormCaptureService()
    # Ensure include_selectors are what we expect (though fallback runs regardless)
    service.config = {
        "debounce_ms": 100,
        "include_selectors": ["#txt_engine_no", "#txt_model", "#txt_color"], 
        "exclude_selectors": [],
        "submit_selector": "#submit_btn",
        "login_config": {}
    }
    
    script = service._get_injection_script()
    
    # HTML where input IDs don't match or are missing, but labels exist
    # This simulates the "defect" scenario
    html_content = """
    <html>
        <body>
            <div id="form-container">
                <!-- Engine Number: Label + Value in next element -->
                <div class="row">
                    <label>Engine Number</label>
                    <span class="value">ENG-12345</span>
                </div>
                
                <!-- Model: Table structure -->
                <table>
                    <tr>
                        <td>Vehicle Model:</td>
                        <td>Honda CD70</td>
                    </tr>
                </table>
                
                <!-- Color: Label and Value in same text (colon sep) -->
                <p>Vehicle Color: Red</p>
                
                <!-- Hidden inputs that might be empty or missing -->
                <input type="hidden" id="txt_engine_no" value="">
                <!-- txt_model and txt_color are completely missing -->
            </div>
            
            <button id="submit_btn">Submit</button>
        </body>
    </html>
    """
    
    captured_events = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture console logs
        page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))

        def py_capture(data):
            if data.get("type") == "form_submission":
                captured_events.append(data)
            
        page.expose_function("py_capture", py_capture)
        page.set_content(html_content)
        page.evaluate(script)
        
        # Trigger submit to force the full capture + fallback logic
        page.click("#submit_btn")
        
        page.wait_for_timeout(2000)
        browser.close()
        
    assert len(captured_events) > 0
    submission = captured_events[-1]["forced_capture"]
    
    # Verify Fallbacks
    # Note: The keys might be normalized or exact depending on logic. 
    # In form_capture_service.py we assign to #txt_engine_no etc.
    print(f"Captured Submission: {submission}")
    
    assert submission.get("#txt_engine_no") == "ENG-12345", f"Engine number mismatch: {submission.get('#txt_engine_no')}"
    assert submission.get("#txt_model") == "Honda CD70", f"Model mismatch: {submission.get('#txt_model')}"
    assert submission.get("#txt_color") == "Red", f"Color mismatch: {submission.get('#txt_color')}"
