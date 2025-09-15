#!/usr/bin/env python3
"""
Download the missing years (2019-2023) with all sections.
"""

from joe_working_scraper import JOEWorkingScraper
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Download missing years with all sections."""
    
    # Only the years we're missing with all sections
    periods = [
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
                    logger.info(f"  Backing up existing file to .bak")
                    backup_path = scraper.download_dir / f"joe_{year}_all_sections.bak.xlsx"
                    if backup_path.exists():
                        backup_path.unlink()
                    new_path.rename(backup_path)
                
                old_path.rename(new_path)
                logger.info(f"✓ Saved as: {new_path}")
            else:
                logger.error(f"Failed to download {year}")
        
        logger.info("\n✅ All downloads complete!")
        
    finally:
        if scraper.driver:
            scraper.driver.quit()


if __name__ == "__main__":
    main()