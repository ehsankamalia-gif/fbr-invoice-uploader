import logging
import sys
import subprocess
import threading
import time
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
            self.context = self.browser.new_context(no_viewport=True)
            self.page = self.context.new_page()
        elif not self.page or self.page.is_closed():
             # Browser exists but page is closed - refresh context and page
             if self.context:
                 try: self.context.close()
                 except: pass
             self.context = self.browser.new_context(no_viewport=True)
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
            
            # Apply layout fixes immediately after navigation
            self._apply_layout_fixes()
            
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
            # Helper to run commands without console window
            def run_hidden(cmd):
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True, # Capture output to prevent printing to console
                    startupinfo=startupinfo
                )

            # 1. Install playwright package
            run_hidden([sys.executable, "-m", "pip", "install", "playwright"])
            
            # 2. Install chromium browser
            # We use --with-deps if on Linux, but on Windows usually just install is enough.
            run_hidden([sys.executable, "-m", "playwright", "install", "chromium"])
            
            messagebox.showinfo("Success", "Components installed successfully! Launching browser...")
        except subprocess.CalledProcessError as e:
            # Try to decode stderr if available
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise Exception(f"Installation command failed: {error_msg}")

    def navigate(self, url: str):
        """Navigates to the specified URL."""
        if not self.page:
            self.start_browser()
        try:
            self.page.goto(url)
            self._apply_layout_fixes()
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise

    def _apply_layout_fixes(self):
        """
        No-op: Layout fixes removed as per user request to restore default CSS.
        """
        pass

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

    def detect_total_pages(self) -> Optional[int]:
        """Attempts to detect total number of pages from the UI."""
        if not self.page: return None
        try:
            # Look for "out of X" pattern common in Kendo UI and other grids
            result = self.page.evaluate(r"""() => {
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    // Check for "out of X" text (e.g., "1-50 out of 500" or "Page 1 of 10")
                // Use innerText to catch text even if not in leaf node, but filter by length to avoid large blocks
                if (el.innerText && el.innerText.length < 50 && el.innerText.match(/of\s+(\d+)/i)) {
                     const match = el.innerText.match(/of\s+(\d+)/i);
                     if (match) {
                             const num = parseInt(match[1]);
                             const text = el.textContent.toLowerCase();
                             
                             // Log potential matches for debugging
                             // console.log("Found potential page text:", text, "Num:", num);
                             
                             // 1. Explicit "Page X of Y"
                             if (text.includes('page')) {
                                 return num;
                             }
                             
                             // 2. "out of X" (Strong indicator for pages or items)
                             // If it says "items" or "records", it's likely total items, NOT pages.
                             if (text.includes('item') || text.includes('record') || text.includes('entry')) {
                                 // Unless we can calculate pages from items? No, too risky.
                                 continue; 
                             }

                             // 3. Heuristic: if number is small (< 100), assume pages.
                             // "out of 3" fits here.
                             if (num < 100) return num;
                         }
                    }
                }
                return null;
            }""")
            
            if result:
                logger.info(f"Detected total pages from UI: {result}")
            return result
        except:
            return None

    def scrape_all_pages(self, max_pages=10, status_callback=None, retry_count=3, delay=1.0) -> List[Dict]:
        """
        Scrapes multiple pages by following 'Next' buttons.
        accumulates data in a list (Appends, does not overwrite).
        Includes retry logic, deduplication, and configurable delays.
        """
        accumulated_data = []
        seen_keys = set()
        
        # Try to estimate total pages for progress tracking
        total_pages = self.detect_total_pages()
        total_str = f"/{total_pages}" if total_pages else ""
        
        for page_num in range(1, max_pages + 1):
            if status_callback:
                status_callback(f"Scraping Page {page_num}{total_str}... (Items: {len(accumulated_data)})")
                
            logger.info(f"Starting scrape for page {page_num}")
            
            # 1. Capture state before scraping (for change detection)
            first_cell_text = self._get_first_cell_text()
            old_row_count = 0
            try:
                old_row_count = len(self.page.query_selector_all("tbody tr"))
            except:
                pass
            
            # 2. Scrape current page with Retry Logic
            page_data = []
            for attempt in range(retry_count):
                try:
                    page_data = self.scrape_current_page(page_num=page_num)
                    if page_data:
                        break # Success
                    else:
                        logger.warning(f"Page {page_num} yielded no data (Attempt {attempt+1}/{retry_count}).")
                        if status_callback:
                             status_callback(f"Page {page_num}{total_str}: Retrying ({attempt+1}/{retry_count})...")
                        if attempt < retry_count - 1:
                            time.sleep(2) # Wait a bit before retry
                except Exception as e:
                    logger.error(f"Error scraping page {page_num} (Attempt {attempt+1}/{retry_count}): {e}")
                    if status_callback:
                        status_callback(f"Page {page_num}{total_str}: Error, Retrying ({attempt+1}/{retry_count})...")
                    if attempt < retry_count - 1:
                        time.sleep(2)
            
            # 3. Append to main list with Deduplication
            if page_data:
                new_items = 0
                for item in page_data:
                    # Create a unique key for deduplication
                    # Using tuple of key fields: (purchase_order, chassis_number, engine_number)
                    key = (
                        item.get("purchase_order", ""), 
                        item.get("chassis_number", ""), 
                        item.get("engine_number", "")
                    )
                    
                    if key not in seen_keys:
                        seen_keys.add(key)
                        accumulated_data.append(item)
                        new_items += 1
                
                logger.info(f"Page {page_num} finished. Added {new_items} new items. Total: {len(accumulated_data)}")
                
                if status_callback:
                    status_callback(f"Page {page_num}{total_str} Done. Added {new_items}. Total: {len(accumulated_data)}")

                # STOP CONDITION: If page had data but ALL were duplicates, we are likely looping
                if new_items == 0 and len(page_data) > 0:
                    logger.warning(f"Page {page_num} yielded only duplicate data. Stopping to prevent infinite loop.")
                    if status_callback:
                        status_callback(f"Stopping: No new data on Page {page_num}.")
                    return accumulated_data # Return immediately to stop the entire scraping process

            else:
                logger.warning(f"Page {page_num} failed after {retry_count} attempts.")
                if status_callback:
                    status_callback(f"Page {page_num}{total_str} Failed/Empty. Continuing...")
                
                # STOP CONDITION: If page is empty, we likely reached the end (if retry failed)
                # But sometimes it's just a glitch. Let's assume empty page = end of list?
                # Usually empty page means end.
                logger.info(f"Page {page_num} is empty. Assuming end of list.")
                break
            
            # 4. Check if we need to stop
            if page_num >= max_pages:
                logger.info("Max pages reached.")
                break
            
            # We used to stop here if page_num >= total_pages, but auto-detection 
            # might be wrong. Better to rely on the "Next" button existence.
            if total_pages and page_num >= total_pages:
                 logger.info(f"Reached detected total pages ({total_pages}). Stopping scraping as per 'out of X' indicator.")
                 break
        
            # 5. Navigate to Next Page
            if status_callback:
                status_callback(f"Page {page_num}{total_str}: Navigating to next...")
                
            if not self.go_to_next_page(current_page_num=page_num):
                logger.info("No next page found or reached end.")
                break
            
            # 6. Configurable Delay
            if delay > 0:
                time.sleep(delay)
                
            # 7. Smart Wait for Page Load (AJAX/Reload)
            if status_callback:
                status_callback(f"Page {page_num + 1}{total_str}: Waiting for load...")
            
            changed = self._wait_for_table_update(old_text=first_cell_text, old_row_count=old_row_count)
            if not changed:
                logger.warning(f"Page content did not change after navigation attempt (Page {page_num} -> {page_num+1}).")
                # We do NOT break here anymore. We let the loop continue and check for duplicate data.
                # If we really are stuck, the next scrape will yield 0 new items and the duplicate check will stop it.
                pass

                
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

    def _wait_for_table_update(self, old_text: str, old_row_count: int = 0) -> bool:
        """
        Waits for the table content to change after clicking Next.
        Checks for first cell text change OR row count increase.
        Returns True if changed, False if timed out.
        """
        logger.info("Waiting for table update...")
        try:
            # Escape quotes safely
            old_text_safe = old_text.replace("'", "\\'")
            
            # Wait until the first cell text is DIFFERENT from old_text
            # OR row count is DIFFERENT (greater)
            # Updated to handle tables without tbody
            self.page.wait_for_function(
                f"""() => {{
                    let firstRow = document.querySelector('tbody tr');
                    if (!firstRow) {{
                        // Fallback for tables without tbody
                        const rows = document.querySelectorAll('tr');
                        if (rows.length > 1) firstRow = rows[1]; // Skip header
                    }}
                    
                    if (!firstRow) return false;
                    
                    const cell = firstRow.querySelector('td:nth-child(2)');
                    const currentText = cell ? cell.innerText.trim() : '';
                    
                    // Count rows (tbody tr or just tr excluding header)
                    let rowCount = document.querySelectorAll('tbody tr').length;
                    if (rowCount === 0) {{
                        rowCount = Math.max(0, document.querySelectorAll('tr').length - 1);
                    }}
                    
                    return (currentText !== '{old_text_safe}') || (rowCount > {old_row_count});
                }}""",
                timeout=10000 
            )
            # Small buffer for rest of table to render
            self.page.wait_for_timeout(500) 
            return True
        except Exception as e:
            logger.warning(f"Wait for table update timed out (No change detected): {e}")
            # Fallback to simple sleep
            self.page.wait_for_timeout(2000)
            return False

    def go_to_next_page(self, current_page_num: int = None) -> bool:
        """
        Attempts to find and click the 'Next' button or handle infinite scroll.
        Returns True if successful (clicked or scrolled), False otherwise.
        """
        if not self.page:
            return False
        
        next_page = current_page_num + 1 if current_page_num else 2
        logger.info(f"Attempting to go to next page (Current: {current_page_num} -> {next_page})...")

        # --- Diagnostic Log (Optional, helps debug invisible structures) ---
        try:
            # Log the HTML of potential pagination containers to debug invisible structures
            # We look for "pagination", "pager", "out of"
            debug_html = self.page.evaluate(r"""() => {
                const els = Array.from(document.querySelectorAll('.pagination, .pager, .k-pager-wrap, .mat-paginator'));
                return els.map(el => el.outerHTML).join('\n---\n');
            }""")
            if debug_html:
                logger.debug(f"Pagination HTML Dump:\n{debug_html}")
        except: pass
        # ----------------------------------------------------------------

        # 1. STRATEGY: Input Field (Playwright Native)
        # Look for an input field that currently has the value of the current page number
        try:
            # Find all visible inputs
            inputs = self.page.query_selector_all('input[type="text"], input[type="number"], input:not([type])')
            for inp in inputs:
                if not inp.is_visible(): continue
                
                # Check value
                val = inp.input_value()
                if val and val.strip() == str(current_page_num):
                    # Check context: usually small width (avoid search boxes etc)
                    box = inp.bounding_box()
                    if box and box['width'] > 150: continue 

                    logger.info(f"Found pagination input with value {val}. Trying to set to {next_page}")
                    try:
                        inp.click() # Focus
                        inp.fill(str(next_page))
                        inp.press("Enter")
                        # Some frameworks need 'Tab' to trigger change
                        self.page.wait_for_timeout(200)
                        inp.press("Tab") 
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to interact with input: {e}")
        except Exception as e:
            logger.warning(f"Input strategy error: {e}")

        # 2. STRATEGY: Dropdown (Playwright Native)
        try:
            selects = self.page.query_selector_all('select')
            for select in selects:
                if not select.is_visible(): continue
                val = select.input_value() # Get selected value
                
                # Check if current value matches current page
                if val == str(current_page_num):
                    logger.info(f"Found pagination dropdown with value {val}. Selecting {next_page}")
                    try:
                        # Try selecting by value first
                        select.select_option(value=str(next_page))
                        return True
                    except:
                        try:
                            # Try selecting by label
                            select.select_option(label=str(next_page))
                            return True
                        except:
                            pass
        except Exception as e:
            logger.warning(f"Dropdown strategy error: {e}")

        # 3. STRATEGY: Kendo/Custom Dropdown (Visible Span + Hidden Select)
        # Look for "out of X" text, then find preceding sibling that looks clickable
        try:
            found_kendo = self.page.evaluate(f"""() => {{
                const currentNum = {current_page_num};
                const nextNum = currentNum + 1;
                
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {{
                    // Check text content "out of X"
                    if (el.children.length === 0 && el.textContent && /out\\s+of\\s+\\d+/i.test(el.textContent)) {{
                         
                         // Look for the dropdown to the LEFT.
                         let sibling = el.previousElementSibling;
                         let attempts = 0;
                         while (sibling && attempts < 5) {{
                             if (sibling.offsetWidth > 0) {{
                                 // Check for Kendo Dropdown
                                 if (sibling.classList.contains('k-dropdown') || sibling.classList.contains('k-widget')) {{
                                     // It's likely a Kendo Dropdown. We need to click the arrow/span to open it.
                                     const arrow = sibling.querySelector('.k-select') || sibling.querySelector('.k-i-arrow-s') || sibling;
                                     if (arrow) {{
                                         arrow.click();
                                         // Now we need to wait for the popup list
                                         // Return true to indicate we clicked it, Python side should handle the rest? 
                                         // No, let's try to handle it in JS or just assume Python handles standard selects.
                                         // Actually Kendo often has a hidden select.
                                     }}
                                 }}
                             }}
                             sibling = sibling.previousElementSibling;
                             attempts++;
                         }}
                    }}
                }}
                return false;
            }}""")
            # Implementing robust Kendo interaction is hard blindly. 
            # If standard Select failed, maybe we rely on "Next Button".
        except: pass

        # 4. STRATEGY: Next Page Number Link (e.g. "2")
        try:
            # Look for exact text match "2" in a clickable element
            # Using XPath to ensure exact text match and exclude random numbers in table
            xpath = f"//a[normalize-space(text())='{next_page}'] | //button[normalize-space(text())='{next_page}'] | //li[normalize-space(text())='{next_page}']"
            elements = self.page.query_selector_all(xpath)
            for el in elements:
                if el.is_visible():
                    logger.info(f"Found link with text '{next_page}'")
                    el.click()
                    return True
        except Exception as e:
            logger.warning(f"Numeric link strategy error: {e}")

        # 5. STRATEGY: "Next" Button (Standard Selectors)
        # List of potential selectors for "Next" button
        selectors = [
            # 1. Text-based (Stricter to avoid headers like "Next Action")
            r"text=/^Next$|^Next\s?>$|^Next\s?»$|^>$|^»$/i",
            r"text=/^Load More$/i", r"text=/^Show More$/i",
            
            # 2. Common Frameworks
            ".paginate_button.next",        # DataTables
            "li.next a",                    # Bootstrap
            "li.page-item.next a",          # Bootstrap 4+
            "ul.pagination li:last-child a", # Generic Bootstrap last item
            ".k-pager-nav.k-pager-last",    # Kendo UI
            ".k-i-arrow-e",                 # Kendo UI Icon
            ".k-icon.k-i-arrow-60-right",   # Kendo UI Newer
            ".mat-paginator-navigation-next", # Angular Material
            ".ui-paginator-next",           # PrimeNG/jQuery UI
            ".pagination-next",             # Bulma/Generic
            
            # 3. Attributes (Loose matching but restricted to interactive elements)
            "a[title*='Next']", "button[title*='Next']", "input[title*='Next']",
            "a[title*='next']", "button[title*='next']", "input[title*='next']", # Lowercase
            "a[aria-label*='Next']", "button[aria-label*='Next']",
            "a[aria-label*='next']", "button[aria-label*='next']",
            
            # Kendo UI Specifics (common in corporate apps)
            "a.k-pager-nav[title='Go to the next page']",
            ".k-pager-nav:not(.k-state-disabled) .k-i-arrow-e",
            ".k-pager-nav:not(.k-state-disabled) .k-i-arrow-60-right",
            
            # 4. Generic Classes
            ".next-page",
            ".btn-next",
            ".next",
            ".load-more",
            
            # 5. Icons
            ".fa-chevron-right",
            ".fa-angle-right",
            ".glyphicon-chevron-right",
            
            # 6. Fallback Text (Broad)
            "text=Next",
            "text=>",
            
            # 7. EXTREMELY BROAD SYMBOL MATCH (New)
            # Looks for any element containing just ">" or "»" or "Next"
            # We filter for short text to avoid clicking paragraphs.
            ":text-matches('^\\s*>\\s*$')", 
            ":text-matches('^\\s*»\\s*$')",
            ":text-matches('^\\s*Next\\s*$')",
            
            # 8. INPUT IMAGE (New)
            "input[type='image'][src*='next']",
            "input[type='image'][src*='arrow']",
            "img[src*='next'][onclick]",
            "img[src*='arrow'][onclick]"
        ]

        for selector in selectors:
            try:
                # Get all matching elements
                elements = self.page.query_selector_all(selector)
                
                # Reverse to prefer bottom pagination (usually more interactive/visible)
                for btn in reversed(elements):
                    if not btn.is_visible():
                        continue
                        
                    # Check for disabled state (class or attribute) on button or parent
                    class_attr = (btn.get_attribute("class") or "").lower()
                    disabled_attr = btn.get_attribute("disabled")
                    aria_disabled = btn.get_attribute("aria-disabled")
                    
                    parent = btn.query_selector("..")
                    parent_class = (parent.get_attribute("class") or "").lower() if parent else ""
                    
                    if ("disabled" in class_attr or 
                        disabled_attr is not None or 
                        (aria_disabled and aria_disabled.lower() == "true") or
                        "disabled" in parent_class):
                        continue
                        
                    logger.info(f"Found Next button via selector: {selector}")
                    try:
                        btn.scroll_into_view_if_needed()
                        btn.click(force=True, timeout=2000)
                        return True
                    except:
                        continue # Try next element if click fails
            except Exception as e:
                # Ignore individual selector errors
                continue

        # 6. STRATEGY: JS Fallback (last resort)
        try:
            logger.info("Trying generic JS text match for 'Next'...")
            clicked = self.page.evaluate(r"""() => {
                function isVisible(elem) {
                    return !!( elem.offsetWidth || elem.offsetHeight || elem.getClientRects().length );
                }
                
                // Find all potential clickable elements
                const elements = Array.from(document.querySelectorAll('a, button, li, span, div.page-link, input[type="button"], input[type="submit"], div[role="button"]'));
                
                // Reverse to try bottom first
                for (const el of elements.reverse()) {
                    const text = el.textContent.trim().toLowerCase();
                    const val = (el.value || '').trim().toLowerCase();
                    const title = (el.title || '').trim().toLowerCase();
                    
                    // Match text or value or title
                    if (['next', '>', '»', 'next >', 'load more', 'show more'].includes(text) || 
                        ['next', '>', '»'].includes(val) || 
                        title.includes('next')) {
                        
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
                
                // SUPER FALLBACK 1: Look for "Page X of Y" dropdowns (Kendo/Generic)
                // Looks for "out of 17" or similar text, finds preceding select/input
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    // Check for "out of X" text
                    if (el.children.length === 0 && el.textContent && el.textContent.match(/out\s+of\s+\d+/i)) {
                         const match = el.textContent.match(/out\s+of\s+(\d+)/i);
                         if (match) {
                             const totalPages = parseInt(match[1]);
                             
                             // Look for previous sibling input or select
                             let sibling = el.previousElementSibling;
                             while (sibling) {
                                 if (sibling.tagName === 'SELECT') {
                                     // It's a dropdown!
                                     const currentVal = parseInt(sibling.value);
                                     if (currentVal < totalPages) {
                                         // Select next value
                                         sibling.value = (currentVal + 1).toString();
                                         sibling.dispatchEvent(new Event('change', { bubbles: true }));
                                         sibling.dispatchEvent(new Event('input', { bubbles: true })); // Added input event
                                         return true;
                                     }
                                     break; 
                                 }
                                 if (sibling.tagName === 'INPUT' && sibling.type === 'text') {
                                      // It's an input box!
                                      const currentVal = parseInt(sibling.value);
                                      if (currentVal < totalPages) {
                                          sibling.value = (currentVal + 1).toString();
                                          sibling.dispatchEvent(new Event('input', { bubbles: true })); // Added input event
                                          sibling.dispatchEvent(new Event('change', { bubbles: true }));
                                          // Also try Enter key
                                          sibling.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
                                          sibling.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', bubbles: true }));
                                          sibling.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', bubbles: true }));
                                          return true;
                                      }
                                      break;
                                 }
                                 sibling = sibling.previousElementSibling;
                             }
                         }
                    }
                }

                // SUPER FALLBACK 2: Look for the last link in a pagination container
                const paginationLinks = document.querySelectorAll('ul.pagination li a, .pagination a, .pager a');
                if (paginationLinks.length > 0) {
                     const lastLink = paginationLinks[paginationLinks.length - 1];
                     if (isVisible(lastLink) && !lastLink.classList.contains('disabled')) {
                         // Check if it looks like a number (if so, it might not be Next)
                         if (isNaN(parseInt(lastLink.textContent.trim()))) {
                             lastLink.click();
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

        # Infinite Scroll Fallback
        try:
            logger.info("Checking for infinite scroll...")
            previous_height = self.page.evaluate("document.body.scrollHeight")
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(2000) # Wait for potential load
            new_height = self.page.evaluate("document.body.scrollHeight")
            
            if new_height > previous_height:
                logger.info("Infinite scroll detected (height increased).")
                return True
        except Exception as e:
             logger.warning(f"Infinite scroll check failed: {e}")

        # Last Resort: Keyboard Navigation (Right Arrow)
        # This is risky as it might not actually move the page but return success, causing infinite loops.
        # We only use it if we really want to try everything, but we MUST return False if we aren't sure.
        try:
            logger.info("Trying Keyboard ArrowRight as last resort...")
            self.page.keyboard.press("ArrowRight")
            # We don't return True here because we can't verify if it worked.
            # If it worked, the next loop iteration's data check will handle it.
            # If it didn't, we want to stop.
            # Actually, if we return False, the loop stops.
            # If we return True, the loop continues and checks for new data.
            # Given we have the "No New Data" stop condition now, we can tentatively return True,
            # BUT: if ArrowRight does nothing, we just waste one loop cycle.
            # Let's return False to be safe and avoid infinite "ArrowRight" loops if the page ignores it.
            # User reported infinite loop, so let's be conservative.
            pass 
        except:
            pass
            
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
