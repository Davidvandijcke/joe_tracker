#!/usr/bin/env python3
"""
Working JOE scraper based on actual HTML structure analysis.
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import json
from typing import Optional, Dict, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JOEWorkingScraper:
    """Working scraper based on actual HTML structure."""
    
    # Date periods for scraping
    DATE_PERIODS = [
        "August 1, 2025 - January 31, 2026",
        "August 1, 2024 – January 31, 2025",
        "August 1, 2023 – January 31, 2024",
        "August 1, 2022 – January 31, 2023",
        "August 1, 2021 – January 31, 2022",
        "August 1, 2020 – January 31, 2021",
        "August 1, 2019 – January 31, 2020",
    ]
    
    # Section mappings (value attribute -> text)
    SECTIONS = {
        "1": "US: Full-Time Academic",
        "5": "International: Full-Time Academic",
        "9": "Full-Time Nonacademic",
    }
    
    def __init__(self, download_dir: str = None, headless: bool = False):
        """Initialize the scraper."""
        if download_dir is None:
            # Use scraped subfolder to keep downloads organized
            download_dir = os.path.join(os.path.dirname(__file__), 'joe_data', 'scraped')
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temp download folder for browser
        self.temp_download_dir = self.download_dir / 'temp'
        self.temp_download_dir.mkdir(parents=True, exist_ok=True)
        
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Set up Chrome driver."""
        options = Options()
        
        # Download settings - use temp directory
        prefs = {
            "download.default_directory": str(self.temp_download_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        if self.headless:
            options.add_argument("--headless=new")
            
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        
    def wait_for_download(self, timeout: int = 30) -> Optional[str]:
        """Wait for a file to be downloaded."""
        start_time = time.time()
        
        # Check existing files first
        existing_files = set(self.temp_download_dir.glob("*.xls*"))
        
        while time.time() - start_time < timeout:
            # Look in temp directory for downloads
            current_files = set(self.temp_download_dir.glob("*.xls*"))
            
            # Check for new files (not in existing set)
            new_files = current_files - existing_files
            
            for file in new_files:
                if not file.name.startswith('.') and not file.name.endswith('.crdownload'):
                    logger.info(f"Download complete: {file}")
                    return str(file)
            
            # Also check if existing files grew in size (were being downloaded)
            for file in current_files:
                if file.stat().st_mtime > start_time and not file.name.startswith('.'):
                    if not file.name.endswith('.crdownload'):
                        logger.info(f"Download complete: {file}")
                        return str(file)
            
            time.sleep(1)
        
        logger.warning("Download timeout")
        return None
    
    def download_data(self, period: str, section_value: str = None) -> Optional[str]:
        """
        Download data for a specific period and optional section.
        
        Args:
            period: Date period text (e.g., "August 1, 2025 - January 31, 2026")
            section_value: Section checkbox value (e.g., "1" for US Academic)
            
        Returns:
            Path to downloaded file or None
        """
        try:
            # Clean temp directory before starting
            for temp_file in self.temp_download_dir.glob("*"):
                try:
                    temp_file.unlink()
                except:
                    pass
            
            # Navigate to JOE listings
            logger.info(f"Navigating to JOE listings...")
            self.driver.get("https://www.aeaweb.org/joe/listings")
            time.sleep(3)
            
            # Handle cookie banner immediately
            try:
                logger.info("Checking for cookie banner...")
                # Look for cookie accept button or close button
                cookie_buttons = self.driver.find_elements(By.XPATH, 
                    "//button[contains(text(), 'Accept')] | " +
                    "//button[contains(text(), 'OK')] | " +
                    "//button[contains(text(), 'I agree')] | " +
                    "//a[contains(@class, 'cookie') and contains(text(), 'Accept')] | " +
                    "//button[contains(@class, 'cookie')]")
                
                if cookie_buttons:
                    logger.info(f"Found cookie button, clicking...")
                    cookie_buttons[0].click()
                    time.sleep(1)
                else:
                    # Try to hide cookie banner with JavaScript
                    self.driver.execute_script("""
                        var cookieBanner = document.querySelector('.cookie-legal-banner');
                        if (cookieBanner) {
                            cookieBanner.style.display = 'none';
                        }
                        var cookieOverlay = document.querySelector('.cookie-overlay');
                        if (cookieOverlay) {
                            cookieOverlay.style.display = 'none';
                        }
                    """)
            except Exception as e:
                logger.warning(f"Could not handle cookie banner: {e}")
            
            # Step 1: Click the date period link
            logger.info(f"Clicking date period: {period}")
            try:
                date_link = self.driver.find_element(By.LINK_TEXT, period)
                date_link.click()
                time.sleep(3)
            except:
                logger.warning(f"Could not find exact date link, trying partial match...")
                # Try partial match
                date_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, period.split("-")[0].strip())
                if date_links:
                    date_links[0].click()
                    time.sleep(3)
                else:
                    logger.error(f"Could not find date period: {period}")
                    return None
            
            # Step 2: Apply section filter if specified
            if section_value:
                logger.info(f"Applying section filter: {section_value}")
                
                # Click Section/Type to expand options
                section_button = self.driver.find_element(By.XPATH, "//div[@class='options-button' and contains(text(), 'Section/Type')]")
                section_button.click()
                time.sleep(1)
                
                # Uncheck "Show All" first if it's checked
                try:
                    show_all = self.driver.find_element(By.XPATH, "//input[@type='checkbox' and @value='0']")
                    if show_all.is_selected():
                        show_all.click()
                        time.sleep(0.5)
                except:
                    pass
                
                # Check the specific section
                section_checkbox = self.driver.find_element(By.XPATH, f"//input[@type='checkbox' and @value='{section_value}']")
                if not section_checkbox.is_selected():
                    section_checkbox.click()
                    logger.info(f"Selected section: {section_value}")
                
                # Need to click Apply Filter button for it to take effect
                try:
                    apply_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Apply Filter')]")
                    apply_button.click()
                    logger.info("Clicked Apply Filter button")
                except:
                    # Fallback: click outside
                    self.driver.find_element(By.TAG_NAME, "body").click()
                    
                time.sleep(3)  # Wait for filter to apply
            
            # Step 3: Set Results Per Page to All
            try:
                logger.info("Setting results per page to All...")
                # Look for the select element
                results_select = self.driver.find_element(By.XPATH, "//select[contains(@class, 'results-per-page') or contains(@name, 'results')]")
                select = Select(results_select)
                
                # Try to select "All" or the highest value
                try:
                    select.select_by_visible_text("All")
                except:
                    # If "All" doesn't exist, select the last option (usually the highest)
                    options = select.options
                    if options:
                        select.select_by_index(len(options) - 1)
                
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Could not set results to All: {e}")
            
            # Step 4: Click Download Options and then Native XLS
            logger.info("Opening download options...")
            
            # Click the Download Options div
            download_div = self.driver.find_element(By.XPATH, "//div[contains(@class, 'extra-button-wrapper') and contains(text(), 'Download Options')]")
            download_div.click()
            time.sleep(1)
            
            # Now click Native XLS link
            logger.info("Clicking Native XLS...")
            native_xls_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'resultset_xls_output.php')]")
            
            # Handle cookie banner or other overlays
            try:
                # Try to close cookie banner if it exists
                cookie_close = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'cookie') and contains(text(), 'Accept')] | //button[contains(@class, 'cookie-close')] | //a[contains(@class, 'cookie') and contains(text(), 'Accept')]")
                if cookie_close:
                    cookie_close[0].click()
                    time.sleep(1)
            except:
                pass
            
            # Use JavaScript to click if regular click is intercepted
            try:
                native_xls_link.click()
            except ElementClickInterceptedException:
                logger.info("Click intercepted, using JavaScript click...")
                self.driver.execute_script("arguments[0].click();", native_xls_link)
            
            # Wait for download
            downloaded_file = self.wait_for_download(timeout=60)
            
            if downloaded_file:
                # Rename with metadata
                year = period.split(",")[1].strip().split("-")[0].strip()
                section_name = self.SECTIONS.get(section_value, "all") if section_value else "all"
                section_name = section_name.replace(":", "").replace(" ", "_")
                new_name = f"joe_{year}_{section_name}.xlsx"
                final_path = self.download_dir / new_name
                
                # Move from temp to final location, overwriting if exists
                if final_path.exists():
                    logger.info(f"Overwriting existing file: {final_path}")
                    final_path.unlink()
                
                Path(downloaded_file).rename(final_path)
                logger.info(f"✓ Saved as: {final_path}")
                
                # Clean temp directory
                for temp_file in self.temp_download_dir.glob("*"):
                    try:
                        temp_file.unlink()
                    except:
                        pass
                
                return str(final_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error downloading {period}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Take screenshot for debugging
            try:
                screenshot_path = self.download_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(str(screenshot_path))
                logger.info(f"Screenshot saved: {screenshot_path}")
            except:
                pass
            
            return None
    
    def download_all(self, years: int = 5, sections: List[str] = None):
        """
        Download data for multiple years and sections.
        
        Args:
            years: Number of years to download
            sections: List of section values to download (default: ["1", "5"])
        """
        if sections is None:
            sections = ["1", "5"]  # US and International Academic
        
        periods = self.DATE_PERIODS[:years]
        results = []
        
        try:
            self.setup_driver()
            
            total = len(periods) * len(sections)
            current = 0
            
            for period in periods:
                for section_value in sections:
                    current += 1
                    section_name = self.SECTIONS.get(section_value, section_value)
                    
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Downloading {current}/{total}: {period} - {section_name}")
                    logger.info(f"{'='*60}")
                    
                    file_path = self.download_data(period, section_value)
                    
                    if file_path:
                        results.append({
                            'period': period,
                            'section': section_name,
                            'file': file_path,
                            'timestamp': datetime.now().isoformat()
                        })
                        logger.info(f"✓ Success: {file_path}")
                    else:
                        logger.error(f"✗ Failed: {period} - {section_name}")
                    
                    # Delay between downloads
                    time.sleep(3)
            
            # Save metadata
            metadata_file = self.download_dir / "download_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump({
                    'downloads': results,
                    'last_update': datetime.now().isoformat(),
                    'total_files': len(results)
                }, f, indent=2)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"DOWNLOAD COMPLETE")
            logger.info(f"Downloaded {len(results)}/{total} files")
            logger.info(f"Saved to: {self.download_dir}")
            logger.info(f"{'='*60}")
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def test_download(self):
        """Test downloading a single file."""
        try:
            self.setup_driver()
            
            # Test with current period, US Academic
            period = self.DATE_PERIODS[0]
            section_value = "1"  # US Academic
            
            logger.info("="*60)
            logger.info("TESTING DOWNLOAD")
            logger.info(f"Period: {period}")
            logger.info(f"Section: {self.SECTIONS.get(section_value)}")
            logger.info("="*60)
            
            file_path = self.download_data(period, section_value)
            
            if file_path:
                logger.info(f"\n✅ TEST SUCCESSFUL!")
                logger.info(f"Downloaded: {file_path}")
                
                # Try reading it
                try:
                    df = pd.read_excel(file_path)
                    logger.info(f"File contains {len(df)} listings")
                    logger.info(f"Columns: {', '.join(df.columns[:5])}...")
                except Exception as e:
                    logger.warning(f"Could not read Excel file: {e}")
                
                return True
            else:
                logger.error("\n❌ TEST FAILED")
                return False
                
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Working JOE Scraper')
    parser.add_argument('--test', action='store_true', help='Run test download')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--years', type=int, default=5, help='Number of years to download')
    parser.add_argument('--all-sections', action='store_true', help='Download all sections')
    
    args = parser.parse_args()
    
    scraper = JOEWorkingScraper(headless=args.headless)
    
    if args.test:
        success = scraper.test_download()
        sys.exit(0 if success else 1)
    else:
        sections = None
        if args.all_sections:
            sections = ["1", "2", "5", "6", "9", "10"]  # All main sections
        
        scraper.download_all(years=args.years, sections=sections)


if __name__ == "__main__":
    main()