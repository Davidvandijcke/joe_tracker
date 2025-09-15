#!/usr/bin/env python3
"""
Comprehensive Selenium scraper for AEA JOE listings.
Downloads data for all year/section combinations as shown in the screenshots.
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JOEComprehensiveScraper:
    """Comprehensive scraper for JOE listings with date and section filtering."""
    
    # Define the date periods (Aug-Jan) for the last 10 years
    DATE_PERIODS = [
        "August 1, 2025 - January 31, 2026",  # Current cycle
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
    
    # Define the sections to scrape
    SECTIONS = {
        "us_academic": "US: Full-Time Academic (Permanent, Tenure Track or Tenured)",
        "us_other_academic": "US: Other Academic (Temporary, Adjunct, Visiting, Part-Time)",
        "intl_academic": "International: Full-Time Academic (Permanent, Tenure Track or Tenured)",
        "intl_other_academic": "International: Other Academic (Temporary, Adjunct, Visiting, Part-Time)",
        "full_time_nonacademic": "Full-Time Nonacademic",
        "other_nonacademic": "Other Nonacademic (Temporary, Part-Time, Non-Salaried, Consulting, Etc.)"
    }
    
    def __init__(self, download_dir: str = None, headless: bool = False):
        """
        Initialize the scraper.
        
        Args:
            download_dir: Directory to save downloaded files
            headless: Run browser in headless mode
        """
        self.base_url = "https://www.aeaweb.org/joe/listings"
        
        # Set up download directory
        if download_dir is None:
            download_dir = os.path.join(os.path.dirname(__file__), 'joe_data', 'downloads')
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.headless = headless
        self.driver = None
        
        # Track download metadata
        self.metadata_file = self.download_dir / "download_metadata.json"
        self.load_metadata()
        
    def load_metadata(self):
        """Load metadata about previous downloads."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                'downloads': [],
                'last_update': None
            }
    
    def save_metadata(self):
        """Save metadata about downloads."""
        self.metadata['last_update'] = datetime.now().isoformat()
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome driver with appropriate options."""
        chrome_options = Options()
        
        # Configure download behavior
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            
        # Additional options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        return driver
    
    def wait_for_download(self, timeout: int = 30) -> Optional[str]:
        """Wait for download to complete and return the downloaded file path."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for any .xlsx or .xls files in download directory
            files = list(self.download_dir.glob("*.xls*"))
            
            # Filter out temporary/partial download files
            complete_files = [f for f in files if not f.name.startswith('.') 
                            and not f.name.endswith('.crdownload')
                            and not f.name.endswith('.tmp')]
            
            # Find the newest file that was created after we started
            for file in sorted(complete_files, key=lambda f: f.stat().st_mtime, reverse=True):
                if file.stat().st_mtime > start_time:
                    logger.info(f"Download complete: {file}")
                    return str(file)
                    
            time.sleep(1)
        
        logger.warning(f"Download timeout after {timeout} seconds")
        return None
    
    def click_date_period(self, period: str) -> bool:
        """
        Click on a specific date period in the left sidebar.
        
        Args:
            period: The date period text to click
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Selecting date period: {period}")
            wait = WebDriverWait(self.driver, 10)
            
            # Find the date period link
            # The periods are links in the left sidebar
            date_link = wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, period))
            )
            
            # Scroll to element and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", date_link)
            time.sleep(0.5)
            date_link.click()
            
            # Wait for page to load
            time.sleep(2)
            logger.info(f"Successfully selected period: {period}")
            return True
            
        except Exception as e:
            logger.error(f"Error selecting date period '{period}': {e}")
            return False
    
    def select_section(self, section_text: str) -> bool:
        """
        Select a specific section/type filter.
        
        Args:
            section_text: The section text to select
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Selecting section: {section_text}")
            wait = WebDriverWait(self.driver, 10)
            
            # Click on Section/Type filter button
            section_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Section/Type')]"))
            )
            section_button.click()
            time.sleep(1)
            
            # Find and check the checkbox for the specific section
            # The checkboxes are in a modal/dropdown
            checkbox_xpath = f"//label[contains(text(), '{section_text}')]/preceding-sibling::input[@type='checkbox']"
            
            # Alternative: sometimes the checkbox might be inside the label
            alt_xpath = f"//label[contains(text(), '{section_text}')]//input[@type='checkbox']"
            
            try:
                checkbox = self.driver.find_element(By.XPATH, checkbox_xpath)
            except:
                checkbox = self.driver.find_element(By.XPATH, alt_xpath)
            
            # Check if already selected
            if not checkbox.is_selected():
                checkbox.click()
                logger.info(f"Checked section: {section_text}")
            else:
                logger.info(f"Section already selected: {section_text}")
            
            # Click Apply Filter button
            apply_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Apply Filter')]")
            apply_button.click()
            
            # Wait for filter to apply
            time.sleep(2)
            logger.info(f"Successfully applied section filter: {section_text}")
            return True
            
        except Exception as e:
            logger.error(f"Error selecting section '{section_text}': {e}")
            return False
    
    def select_all_results(self) -> bool:
        """
        Select 'All' in the results per page dropdown.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Selecting 'All' results per page")
            wait = WebDriverWait(self.driver, 10)
            
            # Find the results per page dropdown
            # It's likely a select element or a custom dropdown
            results_dropdown = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//select[@id='results-per-page' or contains(@class, 'results-per-page')]"))
            )
            
            # Select 'All' option
            from selenium.webdriver.support.ui import Select
            select = Select(results_dropdown)
            select.select_by_visible_text("All")
            
            # Wait for page to reload with all results
            time.sleep(3)
            logger.info("Successfully selected 'All' results")
            return True
            
        except Exception as e:
            logger.warning(f"Could not select 'All' results: {e}")
            # Try alternative method
            try:
                # Sometimes it might be a different type of dropdown
                dropdown = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Results Per Page')]")
                dropdown.click()
                time.sleep(0.5)
                all_option = self.driver.find_element(By.XPATH, "//option[text()='All'] | //li[text()='All']")
                all_option.click()
                time.sleep(3)
                logger.info("Successfully selected 'All' results (alternative method)")
                return True
            except:
                logger.warning("Could not select 'All' results, continuing with default pagination")
                return False
    
    def download_native_xls(self) -> Optional[str]:
        """
        Click the download options and download Native XLS format.
        
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            logger.info("Starting download process")
            wait = WebDriverWait(self.driver, 10)
            
            # Click on Download Options button/tab
            download_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[contains(text(), 'Download Options')] | " +
                    "//a[contains(text(), 'Download Options')] | " +
                    "//div[contains(text(), 'Download Options')]"))
            )
            download_button.click()
            time.sleep(1)
            
            # Click on Native XLS button
            native_xls_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[contains(text(), 'Native XLS')] | " +
                    "//a[contains(text(), 'Native XLS')]"))
            )
            
            logger.info("Clicking Native XLS download button")
            native_xls_button.click()
            
            # Wait for download to complete
            downloaded_file = self.wait_for_download(timeout=60)
            
            return downloaded_file
            
        except Exception as e:
            logger.error(f"Error during download: {e}")
            return None
    
    def scrape_period_section(self, period: str, section_key: str, section_text: str) -> Optional[str]:
        """
        Scrape data for a specific period and section combination.
        
        Args:
            period: Date period to select
            section_key: Key for the section (for naming)
            section_text: Section text to select
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Navigate to base URL
            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # Select date period
            if not self.click_date_period(period):
                return None
            
            # Select section
            if not self.select_section(section_text):
                return None
            
            # Select all results
            self.select_all_results()
            
            # Download the data
            downloaded_file = self.download_native_xls()
            
            if downloaded_file:
                # Rename file with metadata
                year_match = period.split(",")[1].strip().split("-")[0].strip()
                new_filename = f"joe_{year_match}_{section_key}.xlsx"
                new_path = self.download_dir / new_filename
                
                Path(downloaded_file).rename(new_path)
                logger.info(f"Saved as: {new_path}")
                
                # Update metadata
                self.metadata['downloads'].append({
                    'period': period,
                    'section': section_key,
                    'file': str(new_path),
                    'timestamp': datetime.now().isoformat()
                })
                self.save_metadata()
                
                return str(new_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error scraping {period} - {section_key}: {e}")
            return None
    
    def scrape_all_combinations(self, 
                               periods: List[str] = None, 
                               sections: Dict[str, str] = None) -> Dict[str, List[str]]:
        """
        Scrape all combinations of periods and sections.
        
        Args:
            periods: List of date periods to scrape (default: last 5 years)
            sections: Dictionary of sections to scrape (default: main sections)
            
        Returns:
            Dictionary mapping periods to list of downloaded files
        """
        if periods is None:
            # Default to last 5 years for testing
            periods = self.DATE_PERIODS[:5]
        
        if sections is None:
            # Default to main academic sections
            sections = {
                "us_academic": self.SECTIONS["us_academic"],
                "intl_academic": self.SECTIONS["intl_academic"]
            }
        
        results = {}
        
        try:
            # Set up driver
            self.driver = self.setup_driver()
            
            total_combinations = len(periods) * len(sections)
            current = 0
            
            for period in periods:
                period_files = []
                
                for section_key, section_text in sections.items():
                    current += 1
                    logger.info(f"Processing {current}/{total_combinations}: {period} - {section_key}")
                    
                    file_path = self.scrape_period_section(period, section_key, section_text)
                    
                    if file_path:
                        period_files.append(file_path)
                        logger.info(f"✓ Downloaded: {file_path}")
                    else:
                        logger.warning(f"✗ Failed: {period} - {section_key}")
                    
                    # Small delay between downloads
                    time.sleep(2)
                
                results[period] = period_files
            
        finally:
            if self.driver:
                self.driver.quit()
        
        return results
    
    def test_single_download(self):
        """Test downloading a single period/section combination."""
        try:
            self.driver = self.setup_driver()
            
            # Test with current year US Academic
            period = self.DATE_PERIODS[0]  # Current cycle
            section_key = "us_academic"
            section_text = self.SECTIONS[section_key]
            
            logger.info(f"Testing download for: {period} - {section_text}")
            
            file_path = self.scrape_period_section(period, section_key, section_text)
            
            if file_path:
                logger.info(f"✅ Test successful! File: {file_path}")
                
                # Try reading the file
                df = pd.read_excel(file_path)
                logger.info(f"   File contains {len(df)} listings")
                logger.info(f"   Columns: {', '.join(df.columns[:5])}...")
                
                return True
            else:
                logger.error("❌ Test failed - no file downloaded")
                return False
                
        except Exception as e:
            logger.error(f"Test error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Main function for testing and running the scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive JOE Scraper')
    parser.add_argument('--test', action='store_true', 
                       help='Test with single download')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode')
    parser.add_argument('--years', type=int, default=5,
                       help='Number of years to scrape (default: 5)')
    parser.add_argument('--all-sections', action='store_true',
                       help='Scrape all sections (default: only academic)')
    
    args = parser.parse_args()
    
    scraper = JOEComprehensiveScraper(headless=args.headless)
    
    if args.test:
        # Run test
        success = scraper.test_single_download()
        sys.exit(0 if success else 1)
    else:
        # Run full scrape
        periods = scraper.DATE_PERIODS[:args.years]
        
        if args.all_sections:
            sections = scraper.SECTIONS
        else:
            # Just academic sections
            sections = {
                "us_academic": scraper.SECTIONS["us_academic"],
                "intl_academic": scraper.SECTIONS["intl_academic"]
            }
        
        logger.info(f"Starting scrape for {len(periods)} periods and {len(sections)} sections")
        logger.info(f"Total combinations: {len(periods) * len(sections)}")
        
        results = scraper.scrape_all_combinations(periods, sections)
        
        # Summary
        total_files = sum(len(files) for files in results.values())
        logger.info(f"\n{'='*70}")
        logger.info(f"Scraping complete!")
        logger.info(f"Total files downloaded: {total_files}")
        logger.info(f"Results saved in: {scraper.download_dir}")
        logger.info(f"{'='*70}")


if __name__ == "__main__":
    main()