"""
Direct HTTP scraper for AEA JOE listings - simpler alternative to Selenium.
Uses direct API endpoints to download data.
"""

import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import requests
from urllib.parse import urlencode, quote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JOEDirectScraper:
    """Direct HTTP-based scraper for JOE listings."""
    
    def __init__(self, download_dir: str = None):
        """
        Initialize the scraper.
        
        Args:
            download_dir: Directory to save downloaded files
        """
        self.base_url = "https://www.aeaweb.org/joe"
        self.listings_url = f"{self.base_url}/listings.php"
        
        # Download endpoints discovered from the site
        self.download_endpoints = {
            'xml': '/joe/resultset_output.php?mode=full_xml',
            'xls_xml': '/joe/resultset_output.php?mode=xls_xml',
            'native_xls': '/joe/resultset_xls_output.php'
        }
        
        # Set up download directory
        if download_dir is None:
            download_dir = os.path.join(os.path.dirname(__file__), 'joe_data', 'downloads')
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Session for maintaining cookies
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def get_current_issue(self) -> Optional[str]:
        """
        Get the current JOE issue identifier.
        
        Returns:
            Issue identifier (e.g., "2025-02") or None
        """
        try:
            # Load the listings page to get current issue
            response = self.session.get(self.listings_url)
            response.raise_for_status()
            
            # Look for issue in the page content
            # The issue is typically in format "YYYY-MM"
            import re
            issue_pattern = r'issue["\']?\s*[:=]\s*["\']?(\d{4}-\d{2})'
            match = re.search(issue_pattern, response.text, re.IGNORECASE)
            
            if match:
                issue = match.group(1)
                logger.info(f"Found current issue: {issue}")
                return issue
            
            # Alternative: check for current date-based issue
            now = datetime.now()
            issue = f"{now.year}-{now.month:02d}"
            logger.info(f"Using date-based issue: {issue}")
            return issue
            
        except Exception as e:
            logger.error(f"Error getting current issue: {e}")
            return None
    
    def build_query_params(self, 
                          section: str = None,
                          country: str = None,
                          keywords: str = None,
                          jel_codes: List[str] = None) -> Dict:
        """
        Build query parameters for filtering listings.
        
        Args:
            section: Job section filter (e.g., "1" for US Academic)
            country: Country code filter
            keywords: Search keywords
            jel_codes: JEL classification codes
            
        Returns:
            Dictionary of query parameters
        """
        params = {}
        
        # Get current issue
        issue = self.get_current_issue()
        if issue:
            params['issue'] = issue
        
        # Add filters
        if section:
            params['section'] = section
        
        if country:
            params['country'] = country
            
        if keywords:
            params['keywords'] = keywords
            
        if jel_codes:
            params['jel-classification'] = ','.join(jel_codes)
        
        return params
    
    def download_listings(self, 
                         format: str = 'native_xls',
                         section: str = None,
                         filters: Dict = None) -> Optional[str]:
        """
        Download JOE listings in specified format.
        
        Args:
            format: Download format ('xml', 'xls_xml', 'native_xls')
            section: Section filter (e.g., "1" for US Academic)
            filters: Additional filter parameters
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Build query parameters
            if filters is None:
                filters = {}
            
            if section:
                filters['section'] = section
            
            params = self.build_query_params(**filters)
            
            # Get the download endpoint
            if format not in self.download_endpoints:
                logger.error(f"Invalid format: {format}")
                return None
            
            endpoint = self.download_endpoints[format]
            download_url = f"https://www.aeaweb.org{endpoint}"
            
            # Add parameters to URL
            if params:
                # For the download endpoints, parameters might need to be encoded differently
                # The 'q' parameter appears to be an encoded query string
                query_string = urlencode(params)
                download_url = f"{download_url}&q={quote(query_string)}"
            
            logger.info(f"Downloading from: {download_url}")
            
            # Make the download request
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()
            
            # Determine file extension
            extensions = {
                'xml': 'xml',
                'xls_xml': 'xml',
                'native_xls': 'xlsx'
            }
            ext = extensions.get(format, 'dat')
            
            # Save the file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"joe_listings_{timestamp}.{ext}"
            filepath = self.download_dir / filename
            
            # Write content to file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Downloaded successfully to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error downloading listings: {e}")
            return None
    
    def download_all_sections(self) -> Dict[str, str]:
        """
        Download listings for all major sections.
        
        Returns:
            Dictionary mapping section names to file paths
        """
        # Common JOE sections
        sections = {
            'us_academic': '1',  # US: Full-Time Academic
            'international': '2',  # International Academic
            'us_other': '3',  # US: Other Academic
            'public_sector': '4',  # Public Sector
            'private_sector': '5',  # Private Sector
        }
        
        results = {}
        
        for section_name, section_id in sections.items():
            logger.info(f"Downloading section: {section_name}")
            
            filepath = self.download_listings(
                format='native_xls',
                section=section_id
            )
            
            if filepath:
                results[section_name] = filepath
            else:
                logger.warning(f"Failed to download section: {section_name}")
            
            # Small delay between requests
            time.sleep(2)
        
        return results


def test_direct_scraper():
    """Test the direct scraper."""
    scraper = JOEDirectScraper()
    
    # Test 1: Download all listings
    print("\n=== Test 1: Download all listings ===")
    file_path = scraper.download_listings(format='native_xls')
    if file_path:
        print(f"✓ Downloaded all listings to: {file_path}")
    else:
        print("✗ Failed to download all listings")
    
    # Test 2: Download US Academic only
    print("\n=== Test 2: Download US Academic listings ===")
    file_path = scraper.download_listings(
        format='native_xls',
        section='1'  # US Academic
    )
    if file_path:
        print(f"✓ Downloaded US Academic to: {file_path}")
    else:
        print("✗ Failed to download US Academic listings")
    
    # Test 3: Try getting current issue
    print("\n=== Test 3: Get current issue ===")
    issue = scraper.get_current_issue()
    if issue:
        print(f"✓ Current issue: {issue}")
    else:
        print("✗ Could not determine current issue")


if __name__ == "__main__":
    test_direct_scraper()