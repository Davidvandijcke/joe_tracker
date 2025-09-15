#!/usr/bin/env python3
"""
Robust JOE scraper that handles the actual website structure.
Based on the screenshots provided, implements the exact workflow.
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
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JOERobustScraper:
    """Robust scraper that follows the exact JOE website workflow."""
    
    def __init__(self, download_dir: str = None, headless: bool = False):
        """Initialize the scraper."""
        if download_dir is None:
            download_dir = os.path.join(os.path.dirname(__file__), 'joe_data')
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Set up Chrome driver."""
        options = Options()
        
        # Download settings
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
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
        
        while time.time() - start_time < timeout:
            files = list(self.download_dir.glob("*.xls*"))
            
            # Check for new files
            for file in files:
                if file.stat().st_mtime > start_time and not file.name.startswith('.'):
                    if not file.name.endswith('.crdownload'):
                        logger.info(f"Download complete: {file}")
                        return str(file)
            
            time.sleep(1)
        
        logger.warning("Download timeout")
        return None
    
    def download_period(self, period_text: str, section: str = None) -> Optional[str]:
        """
        Download data for a specific period.
        
        Args:
            period_text: Text of the period link (e.g., "August 1, 2025 - January 31, 2026")
            section: Optional section to filter
            
        Returns:
            Path to downloaded file or None
        """
        try:
            # Navigate to the main page with the specific issue
            # The URL structure includes the issue parameter
            year = period_text.split(",")[1].strip().split("-")[0].strip()
            
            # Construct the URL - JOE uses issue parameter in format YYYY-MM
            # August periods start with issue 2025-02 format
            issue_param = f"{year}-02"  # February issue for August-January period
            url = f"https://www.aeaweb.org/joe/listings?issue={issue_param}"
            
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            # Step 1: Click the period in the sidebar (if not already selected)
            try:
                period_link = self.driver.find_element(By.LINK_TEXT, period_text)
                logger.info(f"Clicking period: {period_text}")
                period_link.click()
                time.sleep(2)
            except:
                logger.info(f"Period already selected or not found: {period_text}")
            
            # Step 2: Apply section filter if specified
            if section:
                logger.info(f"Applying section filter: {section}")
                
                # Click Section/Type to open the filter
                try:
                    # The Section/Type is an h3 element that's clickable
                    section_header = self.driver.find_element(By.XPATH, "//h3[contains(text(), 'Section/Type')]")
                    section_header.click()
                    time.sleep(1)
                    
                    # Find and check the appropriate checkbox
                    checkbox_label = self.driver.find_element(By.XPATH, f"//label[contains(text(), '{section}')]")
                    checkbox = checkbox_label.find_element(By.XPATH, "./preceding-sibling::input[@type='checkbox']")
                    
                    if not checkbox.is_selected():
                        checkbox.click()
                        logger.info(f"Selected section: {section}")
                    
                    # Click Apply Filter
                    apply_btn = self.driver.find_element(By.XPATH, "//button[text()='Apply Filter']")
                    apply_btn.click()
                    time.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Could not apply section filter: {e}")
            
            # Step 3: Set Results Per Page to All
            try:
                results_select = Select(self.driver.find_element(By.XPATH, "//select[contains(@id, 'results') or contains(@name, 'results')]"))
                results_select.select_by_visible_text("All")
                time.sleep(2)
                logger.info("Set results per page to All")
            except:
                logger.warning("Could not set results to All, using default")
            
            # Step 4: Click Download Options and Native XLS
            logger.info("Looking for download options...")
            
            # Click on "Download Options" tab/button
            download_tab = self.driver.find_element(By.XPATH, "//a[text()='Download Options'] | //button[text()='Download Options']")
            download_tab.click()
            time.sleep(1)
            
            # Click Native XLS
            native_xls = self.driver.find_element(By.XPATH, "//a[text()='Native XLS'] | //button[text()='Native XLS']")
            logger.info("Clicking Native XLS download...")
            native_xls.click()
            
            # Wait for download
            downloaded_file = self.wait_for_download(timeout=60)
            
            if downloaded_file:
                # Rename with metadata
                section_name = section.replace(":", "").replace(" ", "_") if section else "all"
                new_name = f"joe_{year}_{section_name}.xlsx"
                new_path = self.download_dir / new_name
                
                Path(downloaded_file).rename(new_path)
                logger.info(f"Saved as: {new_path}")
                return str(new_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error downloading {period_text}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def download_all_periods(self, years: int = 5):
        """
        Download data for multiple years.
        
        Args:
            years: Number of years to download (default 5)
        """
        periods = [
            "August 1, 2025 - January 31, 2026",
            "August 1, 2024 – January 31, 2025",
            "August 1, 2023 – January 31, 2024",
            "August 1, 2022 – January 31, 2023",
            "August 1, 2021 – January 31, 2022",
            "August 1, 2020 – January 31, 2021",
            "August 1, 2019 – January 31, 2020",
            "August 1, 2018 – January 31, 2019",
            "August 1, 2017 – January 31, 2018",
            "August 1, 2016 – January 31, 2017",
        ]
        
        sections = [
            "US: Full-Time Academic (Permanent, Tenure Track or Tenured)",
            "International: Full-Time Academic (Permanent, Tenure Track or Tenured)",
        ]
        
        # Limit periods based on years parameter
        periods = periods[:years]
        
        results = []
        
        try:
            self.setup_driver()
            
            for period in periods:
                for section in sections:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Downloading: {period} - {section}")
                    logger.info(f"{'='*60}")
                    
                    file_path = self.download_period(period, section)
                    
                    if file_path:
                        results.append({
                            'period': period,
                            'section': section,
                            'file': file_path,
                            'timestamp': datetime.now().isoformat()
                        })
                        logger.info(f"✓ Success: {file_path}")
                    else:
                        logger.error(f"✗ Failed: {period} - {section}")
                    
                    # Delay between downloads
                    time.sleep(3)
            
            # Save metadata
            metadata_file = self.download_dir / "download_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump({
                    'downloads': results,
                    'last_update': datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Downloaded {len(results)} files")
            logger.info(f"Saved to: {self.download_dir}")
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def test_download(self):
        """Test downloading a single file."""
        try:
            self.setup_driver()
            
            # Test with current period, no section filter
            period = "August 1, 2025 - January 31, 2026"
            
            logger.info("Testing download...")
            file_path = self.download_period(period, section=None)
            
            if file_path:
                logger.info(f"✅ Test successful! Downloaded: {file_path}")
                
                # Try reading it
                df = pd.read_excel(file_path)
                logger.info(f"File contains {len(df)} listings")
                return True
            else:
                logger.error("❌ Test failed")
                return False
                
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Robust JOE Scraper')
    parser.add_argument('--test', action='store_true', help='Run test download')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--years', type=int, default=5, help='Number of years to download')
    
    args = parser.parse_args()
    
    scraper = JOERobustScraper(headless=args.headless)
    
    if args.test:
        success = scraper.test_download()
        sys.exit(0 if success else 1)
    else:
        scraper.download_all_periods(years=args.years)


if __name__ == "__main__":
    main()