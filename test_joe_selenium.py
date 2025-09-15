#!/usr/bin/env python3
"""
Simple test script to debug JOE website interaction with Selenium.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def test_joe_interaction():
    """Test basic interaction with JOE website."""
    
    # Set up Chrome (not headless for debugging)
    options = Options()
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("1. Navigating to JOE listings...")
        driver.get("https://www.aeaweb.org/joe/listings")
        time.sleep(3)
        
        # Take screenshot
        driver.save_screenshot("joe_page_1.png")
        print("   Screenshot saved: joe_page_1.png")
        
        # Try to find date period links
        print("\n2. Looking for date period links...")
        date_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'August')]")
        print(f"   Found {len(date_links)} date period links")
        
        if date_links:
            # Click the first one (current period)
            print(f"   Clicking: {date_links[0].text}")
            date_links[0].click()
            time.sleep(3)
            driver.save_screenshot("joe_page_2_after_date.png")
            print("   Screenshot saved: joe_page_2_after_date.png")
        
        # Look for Section/Type filter
        print("\n3. Looking for Section/Type filter...")
        
        # Try different selectors
        selectors = [
            "//h3[contains(text(), 'Section/Type')]",
            "//button[contains(text(), 'Section/Type')]",
            "//div[contains(text(), 'Section/Type')]",
            "//span[contains(text(), 'Section/Type')]",
            "//a[contains(text(), 'Section/Type')]",
            "//*[contains(@class, 'section')]",
            "//*[contains(@id, 'section')]"
        ]
        
        for selector in selectors:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                print(f"   Found with selector: {selector}")
                print(f"   Element text: {elements[0].text}")
                print(f"   Element tag: {elements[0].tag_name}")
                
                # Try to click it
                try:
                    elements[0].click()
                    time.sleep(2)
                    driver.save_screenshot("joe_page_3_section_clicked.png")
                    print("   Screenshot saved: joe_page_3_section_clicked.png")
                    break
                except Exception as e:
                    print(f"   Could not click: {e}")
        
        # Look for checkboxes
        print("\n4. Looking for section checkboxes...")
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        print(f"   Found {len(checkboxes)} checkboxes")
        
        # Look for results per page
        print("\n5. Looking for results per page dropdown...")
        selects = driver.find_elements(By.TAG_NAME, "select")
        print(f"   Found {len(selects)} select elements")
        for select in selects:
            try:
                print(f"   Select ID: {select.get_attribute('id')}, Name: {select.get_attribute('name')}")
            except:
                pass
        
        # Look for download options
        print("\n6. Looking for download options...")
        download_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Download')]")
        print(f"   Found {len(download_elements)} elements with 'Download'")
        
        # Print all links for debugging
        print("\n7. All links on page:")
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links[:20]:  # First 20 links
            href = link.get_attribute('href')
            text = link.text.strip()
            if text:
                print(f"   - {text}: {href}")
        
        # Check page source for key elements
        print("\n8. Checking page source for key terms...")
        page_source = driver.page_source
        
        if "Native XLS" in page_source:
            print("   ✓ Found 'Native XLS' in page")
        if "Section/Type" in page_source:
            print("   ✓ Found 'Section/Type' in page")
        if "Results Per Page" in page_source:
            print("   ✓ Found 'Results Per Page' in page")
        
        print("\n9. Waiting for user to manually interact...")
        print("   Please manually click through the filters and download")
        print("   Press Ctrl+C when done")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPress Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    test_joe_interaction()