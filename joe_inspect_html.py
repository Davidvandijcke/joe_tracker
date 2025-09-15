#!/usr/bin/env python3
"""
Inspect JOE website HTML to understand the exact structure.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def inspect_joe_html():
    """Inspect the JOE website to understand its structure."""
    
    options = Options()
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("="*70)
        print("JOE WEBSITE HTML INSPECTION")
        print("="*70)
        
        # Go to the main listings page
        driver.get("https://www.aeaweb.org/joe/listings")
        time.sleep(3)
        
        # Save the page source for analysis
        with open("joe_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\n✓ Saved page source to joe_page_source.html")
        
        # 1. Find all date period links
        print("\n1. DATE PERIOD LINKS:")
        print("-" * 40)
        date_links = driver.find_elements(By.XPATH, "//div[@class='joe-listings-menu']//a | //div[@id='joe-listings-menu']//a | //aside//a | //nav//a")
        
        for link in date_links:
            text = link.text.strip()
            if "August" in text or "February" in text:
                href = link.get_attribute("href")
                onclick = link.get_attribute("onclick")
                classes = link.get_attribute("class")
                print(f"   Text: {text}")
                print(f"   Href: {href}")
                print(f"   Classes: {classes}")
                print(f"   Onclick: {onclick}")
                print()
        
        # 2. Look for filter elements
        print("\n2. FILTER ELEMENTS:")
        print("-" * 40)
        
        # Find all elements with text containing "Section"
        section_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Section')]")
        for elem in section_elements[:5]:
            print(f"   Tag: {elem.tag_name}")
            print(f"   Text: {elem.text[:100]}")
            print(f"   ID: {elem.get_attribute('id')}")
            print(f"   Class: {elem.get_attribute('class')}")
            print()
        
        # 3. Find all buttons
        print("\n3. BUTTONS ON PAGE:")
        print("-" * 40)
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            text = btn.text.strip()
            if text:
                print(f"   Button: {text}")
                print(f"   ID: {btn.get_attribute('id')}")
                print(f"   Class: {btn.get_attribute('class')}")
                print()
        
        # 4. Find all select dropdowns
        print("\n4. SELECT DROPDOWNS:")
        print("-" * 40)
        selects = driver.find_elements(By.TAG_NAME, "select")
        for select in selects:
            print(f"   Select ID: {select.get_attribute('id')}")
            print(f"   Select Name: {select.get_attribute('name')}")
            print(f"   Select Class: {select.get_attribute('class')}")
            
            # Get options
            options_elements = select.find_elements(By.TAG_NAME, "option")
            print(f"   Options: {[opt.text for opt in options_elements[:5]]}")
            print()
        
        # 5. Look for download-related elements
        print("\n5. DOWNLOAD-RELATED ELEMENTS:")
        print("-" * 40)
        
        # Search for various download-related text
        download_patterns = [
            "//*[contains(text(), 'Download')]",
            "//*[contains(text(), 'download')]",
            "//*[contains(text(), 'Export')]",
            "//*[contains(text(), 'export')]",
            "//*[contains(text(), 'Output')]",
            "//*[contains(text(), 'XLS')]",
            "//*[contains(text(), 'Excel')]"
        ]
        
        for pattern in download_patterns:
            elements = driver.find_elements(By.XPATH, pattern)
            if elements:
                print(f"\n   Pattern: {pattern}")
                for elem in elements[:3]:
                    print(f"      Tag: {elem.tag_name}")
                    print(f"      Text: {elem.text[:100] if elem.text else 'No text'}")
                    print(f"      Href: {elem.get_attribute('href')}")
                    print()
        
        # 6. Find all links that might be for download
        print("\n6. POTENTIAL DOWNLOAD LINKS:")
        print("-" * 40)
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            href = link.get_attribute("href")
            if href and any(term in href.lower() for term in ["download", "export", "output", "xls", "excel"]):
                print(f"   Text: {link.text}")
                print(f"   Href: {href}")
                print()
        
        # 7. Check for JavaScript functions
        print("\n7. JAVASCRIPT ANALYSIS:")
        print("-" * 40)
        
        # Execute JavaScript to find global functions
        js_code = """
        var funcs = [];
        for (var prop in window) {
            if (typeof window[prop] === 'function') {
                if (prop.toLowerCase().includes('download') || 
                    prop.toLowerCase().includes('export') ||
                    prop.toLowerCase().includes('output')) {
                    funcs.push(prop);
                }
            }
        }
        return funcs;
        """
        
        js_functions = driver.execute_script(js_code)
        if js_functions:
            print(f"   Found JS functions: {js_functions}")
        
        # 8. Try clicking on a date period and see what changes
        print("\n8. TESTING DATE PERIOD CLICK:")
        print("-" * 40)
        
        # Find and click a date period
        try:
            date_link = driver.find_element(By.LINK_TEXT, "August 1, 2025 - January 31, 2026")
            print(f"   Found date link, clicking...")
            date_link.click()
            time.sleep(3)
            
            # Check what changed in the URL
            new_url = driver.current_url
            print(f"   New URL: {new_url}")
            
            # Look for new elements that appeared
            print("\n   Looking for elements that might have appeared after click...")
            
            # Check for filter elements again
            section_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'filter')]")
            print(f"   Found {len(section_elements)} elements with 'filter' in class")
            
            # Look for checkboxes
            checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            print(f"   Found {len(checkboxes)} checkboxes")
            if checkboxes:
                for cb in checkboxes[:3]:
                    label = driver.find_element(By.XPATH, f"//label[@for='{cb.get_attribute('id')}']") if cb.get_attribute('id') else None
                    print(f"      Checkbox ID: {cb.get_attribute('id')}")
                    print(f"      Label: {label.text if label else 'No label found'}")
            
        except Exception as e:
            print(f"   Error clicking date: {e}")
        
        print("\n" + "="*70)
        print("INSPECTION COMPLETE")
        print("="*70)
        print("\nThe browser will stay open for manual inspection.")
        print("You can interact with the page to see the actual workflow.")
        print("Press Ctrl+C to close.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nClosing browser...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    inspect_joe_html()