#!/usr/bin/env python3
"""
Download all sections (combined) for each year - simpler approach.
"""

from joe_working_scraper import JOEWorkingScraper
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Download all years with all sections in one file per year."""
    
    # Periods to download (last 7 years)
    periods = [
        ("August 1, 2025 - January 31, 2026", 2025),
        ("August 1, 2024 – January 31, 2025", 2024),
        ("August 1, 2023 – January 31, 2024", 2023),
        ("August 1, 2022 – January 31, 2023", 2022),
        ("August 1, 2021 – January 31, 2022", 2021),
        ("August 1, 2020 – January 31, 2021", 2020),
        ("August 1, 2019 – January 31, 2020", 2019),
    ]
    
    scraper = JOEWorkingScraper(headless=True)
    
    try:
        scraper.setup_driver()
        
        for period, year in periods:
            logger.info(f"\n{'='*60}")
            logger.info(f"Downloading {year} - ALL SECTIONS")
            logger.info(f"{'='*60}")
            
            # Download WITHOUT section filter - gets all sections
            file_path = scraper.download_data(period, section_value=None)
            
            if file_path:
                # Rename to indicate it has all sections
                old_path = Path(file_path)
                new_path = scraper.download_dir / f"joe_{year}_all_sections.xlsx"
                
                if new_path.exists():
                    new_path.unlink()
                
                old_path.rename(new_path)
                logger.info(f"✓ Saved as: {new_path}")
                
                # Remove old single-section files if they exist
                for pattern in [f"joe_{year}_US_Full-Time_Academic.xlsx", 
                               f"joe_{year}_International_Full-Time_Academic.xlsx"]:
                    old_file = scraper.download_dir / pattern
                    if old_file.exists():
                        logger.info(f"  Removing old file: {old_file}")
                        old_file.unlink()
            else:
                logger.error(f"Failed to download {year}")
        
        logger.info("\n✅ All downloads complete!")
        
    finally:
        if scraper.driver:
            scraper.driver.quit()


if __name__ == "__main__":
    main()