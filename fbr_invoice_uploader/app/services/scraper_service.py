import logging
import sys
import subprocess
import threading
from tkinter import messagebox
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class HondaScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    def start_browser(self, headless=False):
        """Starts the browser instance."""
        # Check if browser is already running and valid
        if self.browser and self.browser.is_connected() and self.page and not self.page.is_closed():
            return

        if not self.playwright:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                # Attempt to auto-install
                try:
                    self._install_dependencies()
                    from playwright.sync_api import sync_playwright
                except Exception as e:
                    logger.error(f"Failed to install dependencies: {e}")
                    raise ImportError(f"Playwright missing and auto-install failed: {e}. Please run 'pip install playwright' and 'playwright install chromium' manually.")

            self.playwright = sync_playwright().start()

        # Launch with a large viewport if needed
        if not self.browser or not self.browser.is_connected():
            self.browser = self.playwright.chromium.launch(headless=headless, args=["--start-maximized"])
            self.context = self.browser.new_context(viewport={"width": 1280, "height": 720})
            self.page = self.context.new_page()
        elif not self.page or self.page.is_closed():
             # Browser exists but page is closed - refresh context and page
             if self.context:
                 try: self.context.close()
                 except: pass
             self.context = self.browser.new_context(viewport={"width": 1280, "height": 720})
             self.page = self.context.new_page()

    def login(self, url: str, username: str = None, password: str = None):
        """Navigates to the URL and performs auto-login with robust handling."""
        from app.core.config import settings

        max_retries = 2
        for attempt in range(max_retries):
            # Ensure we have a valid page and browser connection
            if self.page:
                try:
                    if self.page.is_closed() or (self.browser and not self.browser.is_connected()):
                        self.page = None
                except:
                    self.page = None

            if not self.page:
                self.start_browser()

            try:
                logger.info(f"Navigating to {url} (Attempt {attempt+1}/{max_retries})...")
                # Navigate with extended timeout for potential network delays
                self.page.goto(url, timeout=30000)
                break # Navigation successful, proceed to login
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Navigation error on attempt {attempt+1}: {error_msg}")
                
                # Check for closed browser/context errors
                if "closed" in error_msg.lower() or "context" in error_msg.lower() or "crash" in error_msg.lower():
                    logger.warning("Browser appears closed or crashed. Restarting...")
                    self.close() # Force full cleanup
                    self.page = None
                    if attempt == max_retries - 1:
                        # If this was the last retry, re-raise the exception
                        # But wait, maybe we should just catch it and let the user know?
                        # The original code caught everything in the outer try block.
                        # We will re-raise here to be caught by the outer try/except if we want, 
                        # but actually we are inside the 'try' that covers login logic too.
                        # Let's just raise to break the loop and go to the outer exception handler.
                        raise e
                    continue # Try again
                else:
                    raise e # Other errors (network, etc) might not be fixed by restart, but let's re-raise

        try:
            # 1. Identify correct login form fields
            
            # 1. Identify correct login form fields
            # Strategies: specific placeholders (Best for this site), names, IDs, or generic types
            # We use get_by_placeholder for better reliability with Playwright
            
            # Wait for the page to be stable
            try:
                self.page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass # Continue even if network is busy
                
            found_user_selector = None
            found_pass_selector = None
            
            # Strategy A: Precise Placeholders (Most likely to work for this site)
            try:
                if self.page.get_by_placeholder("Enter Dealer Code").is_visible():
                    logger.info("Found 'Enter Dealer Code' field.")
                    self.page.get_by_placeholder("Enter Dealer Code").fill(username)
                    found_user_selector = "placeholder='Enter Dealer Code'"
                
                if self.page.get_by_placeholder("Enter Password").is_visible():
                    logger.info("Found 'Enter Password' field.")
                    self.page.get_by_placeholder("Enter Password").fill(password)
                    found_pass_selector = "placeholder='Enter Password'"
            except Exception as e:
                logger.warning(f"Placeholder strategy failed: {e}")

            # Strategy B: CSS Selectors (Fallback)
            if not found_user_selector:
                user_selectors = [
                    "input[name='username']", "input[name*='user']", "#username", "#user",
                    "input[type='text']" # Fallback to first text input
                ]
                for sel in user_selectors:
                    if self.page.is_visible(sel):
                        self.page.fill(sel, username)
                        found_user_selector = sel
                        break
            
            if not found_pass_selector:
                pass_selectors = [
                    "input[name='password']", "input[name*='pass']", "#password", "#pass",
                    "input[type='password']" # Fallback to first password input
                ]
                for sel in pass_selectors:
                    if self.page.is_visible(sel):
                        self.page.fill(sel, password)
                        found_pass_selector = sel
                        break

            if not found_user_selector or not found_pass_selector:
                logger.warning(f"Could not identify all login fields. User: {found_user_selector}, Pass: {found_pass_selector}")
                return

            # 4. Programmatically enter credentials (already done in strategies above)
            # Just verify now
            
            # 8. Visual Verification (Programmatic check)
            # Skip strict verification if we used placeholder strategy as .input_value() might need selector
            # But we can try if we have a selector, or just trust the fill() which throws if it fails.
            
            # Focus CAPTCHA
            captcha_selectors = ["input[placeholder='Type the Confirm Text']", "input[name*='captcha']", "input[name*='code']"]
            for cap in captcha_selectors:
                 try:
                    if self.page.is_visible(cap):
                        logger.info("CAPTCHA detected. Focusing field for user...")
                        self.page.focus(cap)
                        break
                 except: continue

            logger.info("Login fields populated.")

        except Exception as e:
            # 5. Error handling
            logger.error(f"Auto-login process failed: {e}")
            # We do not raise here to avoid crashing the UI thread, just log and let user manually intervene
            messagebox.showwarning("Login Warning", f"Auto-login could not complete: {e}\nPlease login manually.")

    def _install_dependencies(self):
        """Auto-installs playwright and chromium using the current interpreter."""
        logger.info("Attempting to auto-install Playwright and Chromium...")
        
        # Notify user (since this runs in a GUI thread usually, this blocks, but it's better than silence)
        # Using a separate thread for the message box to not block the install? 
        # No, we want to warn them before we freeze for a bit, or just do it.
        # Since we are likely in the main thread (triggered by button), this will freeze the UI.
        # Let's show a message first.
        messagebox.showinfo("Installing Components", "First-time setup: Installing browser automation components.\nThis may take 1-2 minutes. Please wait...")
        
        try:
            # 1. Install playwright package
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            
            # 2. Install chromium browser
            # We use --with-deps if on Linux, but on Windows usually just install is enough.
            # Adding shell=True can help on Windows sometimes, but list args is safer.
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            
            messagebox.showinfo("Success", "Components installed successfully! Launching browser...")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Installation command failed: {e}")

    def navigate(self, url: str):
        """Navigates to the specified URL."""
        if not self.page:
            self.start_browser()
        try:
            self.page.goto(url)
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise

    def trigger_bookmark_dialog(self):
        """Simulates Ctrl+D to open the browser's bookmark dialog."""
        if not self.page:
            raise Exception("Browser not connected")
        
        self.page.bring_to_front()
        # Windows/Linux use Control+d, Mac uses Meta+d
        modifier = "Meta" if sys.platform == "darwin" else "Control"
        self.page.keyboard.press(f"{modifier}+d")

    def scrape_current_page(self, page_num: int = 1) -> List[Dict]:
        """
        Scrapes the inventory table from the current page.
        Matches the structure shown in user screenshot.
        """
        if not self.page:
            raise Exception("Browser not connected")

        # Wait for any table to be present
        try:
            self.page.wait_for_selector("table", timeout=5000)
        except:
            pass # Proceed anyway, maybe it's already loaded

        data = []
        # Query all rows in the body of the table
        rows = self.page.query_selector_all("tbody tr")
        
        # If no tbody, try just tr (some tables don't use tbody)
        if not rows:
            rows = self.page.query_selector_all("tr")
            # Skip header usually the first one if we select all tr
            if rows:
                rows = rows[1:]

        for row in rows:
            cells = row.query_selector_all("td")
            # Screenshot shows ~9 columns (Sr, PO, Date, Model, Color, Eng, Chas, Status, Action)
            if len(cells) < 7:
                continue 
            
            try:
                # Extract text safely
                p_order = cells[1].inner_text().strip()
                # recv_date = cells[2].inner_text().strip() # Not stored in DB yet, but extracted
                model = cells[3].inner_text().strip()
                color = cells[4].inner_text().strip()
                engine = cells[5].inner_text().strip()
                chassis = cells[6].inner_text().strip()
                status_text = cells[7].inner_text().strip()

                # Normalize Status
                status = "IN_STOCK"
                if "sold" in status_text.lower():
                    status = "SOLD"
                
                item = {
                    "purchase_order": p_order,
                    "model": model,
                    "color": color,
                    "engine_number": engine,
                    "chassis_number": chassis,
                    "status": status,
                    "make": "Honda", # Default
                    "page_number": page_num
                }
                
                # Basic validation
                if engine and chassis:
                    data.append(item)
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue
            
        return data

    def scrape_all_pages(self, max_pages=10, status_callback=None) -> List[Dict]:
        """
        Scrapes multiple pages by following 'Next' buttons.
        accumulates data in a list (Appends, does not overwrite).
        """
        accumulated_data = []
        
        for page_num in range(1, max_pages + 1):
            if status_callback:
                status_callback(f"Scraping page {page_num}... (Collected so far: {len(accumulated_data)})")
                
            logger.info(f"Starting scrape for page {page_num}")
            
            # 1. Capture state before scraping (for change detection)
            first_cell_text = self._get_first_cell_text()
            
            try:
                # 2. Scrape current page
                page_data = self.scrape_current_page(page_num=page_num)
                
                # 3. Append to main list (Cumulative storage)
                if page_data:
                    accumulated_data.extend(page_data)
                    logger.info(f"Page {page_num} finished. Added {len(page_data)} items. Total: {len(accumulated_data)}")
                    
                    if status_callback:
                        status_callback(f"Page {page_num} Done. Total: {len(accumulated_data)}")
                else:
                    logger.warning(f"Page {page_num} yielded no data.")
                    if status_callback:
                        status_callback(f"Page {page_num} Empty. Retrying navigation...")
                    
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                if status_callback:
                    status_callback(f"Error on page {page_num}: {e}")
            
            # 4. Check if we need to stop
            if page_num >= max_pages:
                logger.info("Max pages reached.")
                break
                
            # 5. Navigate to Next Page
            if not self.go_to_next_page():
                logger.info("No next page found or reached end.")
                break
                
            # 6. Smart Wait for Page Load (AJAX/Reload)
            self._wait_for_table_update(old_text=first_cell_text)
                
        return accumulated_data

    def _get_first_cell_text(self) -> str:
        """Helper to get text of the first data cell to detect page changes."""
        try:
            # Try to get the first PO or Model cell
            cell = self.page.query_selector("tbody tr:first-child td:nth-child(2)") 
            if cell:
                return cell.inner_text().strip()
        except:
            pass
        return ""

    def _wait_for_table_update(self, old_text: str):
        """
        Waits for the table content to change after clicking Next.
        Equivalent to Selenium's WebDriverWait until text changes.
        """
        logger.info("Waiting for table update...")
        try:
            # Wait until the first cell text is DIFFERENT from old_text
            # This handles AJAX loading where URL might not change
            self.page.wait_for_function(
                f"""() => {{
                    const cell = document.querySelector('tbody tr:first-child td:nth-child(2)');
                    return cell && cell.innerText.trim() !== '{old_text}';
                }}""",
                timeout=10000 # 10 seconds timeout
            )
            # Small buffer for rest of table to render
            self.page.wait_for_timeout(500) 
        except Exception as e:
            logger.warning(f"Wait for table update timed out or failed: {e}")
            # Fallback to simple sleep
            self.page.wait_for_timeout(2000)

    def go_to_next_page(self) -> bool:
        """
        Attempts to find and click the 'Next' button.
        Returns True if successful, False otherwise.
        """
        if not self.page:
            return False
        
        logger.info("Attempting to find Next button...")
        
        # List of potential selectors for "Next" button
        selectors = [
            # 1. Text-based (Playwright pseudoselector)
            "text=/Next|next|Next >|Next »|>|»/",
            
            # 2. Common Frameworks
            ".paginate_button.next",        # DataTables
            "li.next a",                    # Bootstrap
            "li.page-item.next a",          # Bootstrap 4+
            ".k-pager-nav.k-pager-last",    # Kendo UI
            ".k-i-arrow-e",                 # Kendo UI Icon
            
            # 3. Attributes
            "a[title='Go to the next page']",
            "a[title='Next Page']", 
            "button[title='Next Page']",
            "a[aria-label='Next']",
            "button[aria-label='Next']",
            
            # 4. Generic Classes
            ".next-page",
            ".btn-next",
            
            # 5. Icons
            ".fa-chevron-right",
            ".fa-angle-right",
            ".glyphicon-chevron-right"
        ]

        for selector in selectors:
            try:
                # Get all matching elements
                elements = self.page.query_selector_all(selector)
                for btn in elements:
                    if not btn.is_visible():
                        continue
                        
                    # Check for disabled state (class or attribute) on button or parent
                    class_attr = (btn.get_attribute("class") or "").lower()
                    disabled_attr = btn.get_attribute("disabled")
                    
                    parent = btn.query_selector("..")
                    parent_class = (parent.get_attribute("class") or "").lower() if parent else ""
                    
                    if "disabled" in class_attr or disabled_attr is not None or "disabled" in parent_class:
                        continue
                        
                    logger.info(f"Found Next button via selector: {selector}")
                    btn.click(force=True)
                    return True
            except Exception as e:
                # Ignore individual selector errors
                continue

        # JS Fallback (last resort)
        try:
            logger.info("Trying generic JS text match for 'Next'...")
            clicked = self.page.evaluate("""() => {
                function isVisible(elem) {
                    return !!( elem.offsetWidth || elem.offsetHeight || elem.getClientRects().length );
                }
                
                // Find all potential clickable elements
                const elements = Array.from(document.querySelectorAll('a, button, li, span, div.page-link, input[type="button"], input[type="submit"]'));
                
                for (const el of elements) {
                    const text = el.textContent.trim().toLowerCase();
                    const val = (el.value || '').trim().toLowerCase();
                    
                    // Match text or value
                    if (['next', '>', '»', 'next >'].includes(text) || ['next', '>', '»'].includes(val)) {
                        
                        // Check disabled
                        if (el.classList.contains('disabled') || el.hasAttribute('disabled')) {
                            continue;
                        }
                        
                        // Check parent disabled (common in pagination li)
                        if (el.parentElement && el.parentElement.classList.contains('disabled')) {
                            continue;
                        }

                        if (isVisible(el)) {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
            }""")
            
            if clicked:
                logger.info("Clicked Next button via JS fallback.")
                return True
        except Exception as e:
            logger.warning(f"JS Fallback failed: {e}")

        return False


    def close(self):
        """Closes the browser and playwright."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
