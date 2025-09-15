#!/usr/bin/env python3
"""
Test script to verify JOE scraper functionality.
Tests both Selenium and direct HTTP approaches.
"""

import os
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

print("=" * 70)
print("JOE Scraper Test Suite")
print("=" * 70)

# Test 1: Check if we have the Excel files locally
print("\n[Test 1] Checking for existing Excel files...")
joe_data_dir = Path("joe_data")
if joe_data_dir.exists():
    excel_files = list(joe_data_dir.glob("*.xlsx")) + list(joe_data_dir.glob("*.xls"))
    if excel_files:
        print(f"✓ Found {len(excel_files)} existing Excel files:")
        for f in excel_files[:3]:
            print(f"  - {f.name}")
            # Try reading one
            try:
                df = pd.read_excel(f)
                print(f"    Rows: {len(df)}, Columns: {len(df.columns)}")
                if 'Date_Active' in df.columns:
                    print("    ✓ Has Date_Active column")
                if 'jp_section' in df.columns:
                    print("    ✓ Has jp_section column")
            except Exception as e:
                print(f"    ✗ Error reading: {e}")
    else:
        print("✗ No Excel files found in joe_data directory")
else:
    print("✗ joe_data directory doesn't exist")

# Test 2: Try direct HTTP scraper (simpler, no browser needed)
print("\n[Test 2] Testing Direct HTTP Scraper...")
try:
    from joe_direct_scraper import JOEDirectScraper
    
    scraper = JOEDirectScraper()
    print("Attempting to download JOE listings via direct HTTP...")
    
    # Try to get current issue first
    issue = scraper.get_current_issue()
    if issue:
        print(f"✓ Detected current issue: {issue}")
    
    # Try downloading
    file_path = scraper.download_listings(format='native_xls')
    if file_path and Path(file_path).exists():
        print(f"✓ Successfully downloaded to: {file_path}")
        # Try reading it
        try:
            df = pd.read_excel(file_path)
            print(f"  File contains {len(df)} listings")
        except:
            print("  Note: File downloaded but may need Excel to open")
    else:
        print("✗ Direct HTTP download failed")
        print("  This might be because the site requires browser interaction")
        
except ImportError:
    print("✗ Direct scraper not available")
except Exception as e:
    print(f"✗ Direct scraper error: {e}")

# Test 3: Check Selenium dependencies
print("\n[Test 3] Checking Selenium Dependencies...")
selenium_ready = True

try:
    import selenium
    print(f"✓ Selenium installed (version {selenium.__version__})")
except ImportError:
    print("✗ Selenium not installed - run: pip install selenium")
    selenium_ready = False

# Check for Chrome
import subprocess
chrome_installed = False
try:
    result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Google Chrome found")
        chrome_installed = True
    else:
        # Try alternative Chrome paths
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS
            '/usr/bin/google-chrome',  # Linux
            '/usr/bin/google-chrome-stable',  # Linux alternative
        ]
        for path in chrome_paths:
            if Path(path).exists():
                print(f"✓ Google Chrome found at: {path}")
                chrome_installed = True
                break
        
        if not chrome_installed:
            print("✗ Google Chrome not found")
            print("  Install Chrome or update the PATH")
except:
    print("⚠ Could not check for Chrome")

# Check for ChromeDriver
chromedriver_installed = False
try:
    result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ ChromeDriver found")
        chromedriver_installed = True
    else:
        print("✗ ChromeDriver not found")
        print("  Install with: brew install --cask chromedriver (macOS)")
        print("  Or download from: https://chromedriver.chromium.org/")
except:
    print("⚠ Could not check for ChromeDriver")

# Test 4: Try Selenium scraper if dependencies are met
if selenium_ready and chrome_installed:
    print("\n[Test 4] Testing Selenium Scraper...")
    try:
        from joe_selenium_scraper import JOEScraper
        
        # Use headless=False for testing to see what's happening
        scraper = JOEScraper(headless=False)
        print("Attempting to download JOE listings via Selenium...")
        print("(Browser window will open - this is normal for testing)")
        
        file_path = scraper.scrape_listings()
        if file_path and Path(file_path).exists():
            print(f"✓ Successfully downloaded to: {file_path}")
            # Try reading it
            try:
                df = pd.read_excel(file_path)
                print(f"  File contains {len(df)} listings")
            except:
                print("  File downloaded but may need processing")
        else:
            print("✗ Selenium download failed")
            
    except Exception as e:
        print(f"✗ Selenium scraper error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n[Test 4] Skipping Selenium test - dependencies not met")

# Summary
print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)

if joe_data_dir.exists() and excel_files:
    print("✓ Existing data found - can proceed with visualization")
    print(f"  Run: python process_xls_with_openings.py")
else:
    print("⚠ No existing data found")
    if selenium_ready and chrome_installed and chromedriver_installed:
        print("✓ Selenium scraper ready to use")
        print("  Run: python joe_selenium_scraper.py")
    else:
        print("✗ Selenium scraper not ready - install dependencies")
        
print("\nTo run the web app:")
print("  streamlit run joe_web_app.py")