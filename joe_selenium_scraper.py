"""
Selenium-based scraper for AEA JOE (Job Openings for Economists) listings.
Downloads data automatically in Excel format for processing.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import shutil

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JOEScraper:
    """Scraper for downloading JOE listings data."""
    
    def __init__(self, download_dir: str = None, headless: bool = True):
        """
        Initialize the JOE scraper.
        
        Args:
            download_dir: Directory to save downloaded files
            headless: Run browser in headless mode
        """
        self.base_url = "https://www.aeaweb.org/joe/listings.php"
        
        # Set up download directory
        if download_dir is None:
            download_dir = os.path.join(os.path.dirname(__file__), 'joe_data', 'downloads')
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Archive directory for processed files
        self.archive_dir = self.download_dir.parent / 'archive'
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        self.headless = headless
        self.driver = None
        
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
        
        return driver
    
    def wait_for_download(self, timeout: int = 30) -> Optional[str]:
        """
        Wait for download to complete and return the downloaded file path.
        
        Args:
            timeout: Maximum time to wait for download
            
        Returns:
            Path to downloaded file or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for any .xlsx or .xls files in download directory
            files = list(self.download_dir.glob("*.xls*"))
            
            # Filter out temporary/partial download files
            complete_files = [f for f in files if not f.name.startswith('.') 
                            and not f.name.endswith('.crdownload')
                            and not f.name.endswith('.tmp')]
            
            if complete_files:
                # Return the most recent file
                newest_file = max(complete_files, key=lambda f: f.stat().st_mtime)
                logger.info(f"Download complete: {newest_file}")
                return str(newest_file)
                
            time.sleep(1)
        
        logger.warning(f"Download timeout after {timeout} seconds")
        return None
    
    def clear_download_directory(self):
        """Clear the download directory before new download."""
        for file in self.download_dir.glob("*"):
            if file.is_file():
                try:
                    file.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete {file}: {e}")
    
    def scrape_listings(self, 
                       sections: List[str] = None,
                       date_range: str = "all") -> Optional[str]:
        """
        Scrape JOE listings and download as Excel file.
        
        Args:
            sections: List of sections to filter (e.g., ["US: Full-Time Academic"])
            date_range: Date range filter ("all", "week", "month", "year")
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Clear previous downloads
            self.clear_download_directory()
            
            # Set up driver
            self.driver = self.setup_driver()
            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for listings to load (look for the listings table or a specific element)
            try:
                wait.until(
                    EC.presence_of_element_located((By.ID, "ListingsForm"))
                )
                logger.info("Listings page loaded successfully")
            except TimeoutException:
                logger.warning("Listings form not found, continuing anyway...")
            
            # Apply section filters if specified
            if sections:
                self._apply_section_filter(sections, wait)
            
            # Apply date range filter
            if date_range != "all":
                self._apply_date_filter(date_range, wait)
            
            # Method 1: Try finding direct download links
            logger.info("Looking for download links...")
            
            # Look for XLS download link with the specific URL pattern
            download_links = self.driver.find_elements(
                By.XPATH, 
                "//a[contains(@href, 'resultset_xls_output.php') or " +
                "contains(@href, 'resultset_output.php?mode=xls')]"
            )
            
            if download_links:
                # Use the first Excel download link found
                download_link = download_links[0]
                href = download_link.get_attribute('href')
                logger.info(f"Found download link: {href}")
                
                # Click the download link
                download_link.click()
                
            else:
                # Method 2: Try constructing the download URL directly
                logger.info("No direct download links found, constructing URL...")
                
                # Get the current URL parameters (which include filters)
                current_url = self.driver.current_url
                
                # Check if we can find the encoded query parameter
                if "?" in current_url:
                    base_params = current_url.split("?")[1]
                else:
                    base_params = ""
                
                # Construct XLS download URL
                # The JOE site uses these endpoints for downloads:
                # - /joe/resultset_output.php?mode=xls_xml&q=[encoded_query]
                # - /joe/resultset_xls_output.php?mode=xls_xml&q=[encoded_query]
                
                download_url = f"https://www.aeaweb.org/joe/resultset_xls_output.php?mode=xls_xml&{base_params}"
                logger.info(f"Navigating to download URL: {download_url}")
                
                # Navigate to the download URL
                self.driver.get(download_url)
            
            # Wait for download to complete
            downloaded_file = self.wait_for_download(timeout=60)
            
            if downloaded_file:
                # Rename file with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"joe_listings_{timestamp}.xlsx"
                new_path = self.download_dir / new_filename
                
                Path(downloaded_file).rename(new_path)
                logger.info(f"Downloaded and renamed to: {new_path}")
                
                return str(new_path)
            else:
                logger.error("Download failed or timed out")
                return None
                
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def _apply_section_filter(self, sections: List[str], wait):
        """Apply section filters on the listings page."""
        try:
            # Look for section checkboxes or dropdown
            for section in sections:
                # Try to find checkbox for the section
                checkbox_xpath = f"//input[@type='checkbox' and following-sibling::text()[contains(., '{section}')]]"
                try:
                    checkbox = wait.until(
                        EC.presence_of_element_located((By.XPATH, checkbox_xpath))
                    )
                    if not checkbox.is_selected():
                        checkbox.click()
                        logger.info(f"Selected section: {section}")
                except TimeoutException:
                    logger.warning(f"Could not find checkbox for section: {section}")
                    
        except Exception as e:
            logger.warning(f"Error applying section filter: {e}")
    
    def _apply_date_filter(self, date_range: str, wait):
        """Apply date range filter."""
        try:
            # Map date range to days
            days_map = {
                "week": 7,
                "month": 30,
                "year": 365
            }
            
            if date_range in days_map:
                # Look for date filter dropdown or input
                date_select = wait.until(
                    EC.presence_of_element_located((By.NAME, "date_range"))
                )
                
                select = Select(date_select)
                select.select_by_value(str(days_map[date_range]))
                logger.info(f"Applied date filter: {date_range}")
                
        except Exception as e:
            logger.warning(f"Error applying date filter: {e}")
    
    def archive_old_files(self, days_to_keep: int = 30):
        """Archive files older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for file in self.download_dir.glob("joe_listings_*.xlsx"):
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            
            if file_time < cutoff_date:
                # Move to archive
                archive_path = self.archive_dir / file.name
                shutil.move(str(file), str(archive_path))
                logger.info(f"Archived old file: {file.name}")


def main():
    """Main function for testing the scraper."""
    scraper = JOEScraper(headless=False)  # Set to True for production
    
    # Download all US Academic positions
    file_path = scraper.scrape_listings(
        sections=["US: Full-Time Academic"],
        date_range="all"
    )
    
    if file_path:
        print(f"Successfully downloaded: {file_path}")
        
        # Test reading the file
        df = pd.read_excel(file_path)
        print(f"Downloaded {len(df)} job listings")
        print(f"Columns: {', '.join(df.columns[:5])}...")
    else:
        print("Download failed")
    
    # Archive old files
    scraper.archive_old_files()


if __name__ == "__main__":
    main()