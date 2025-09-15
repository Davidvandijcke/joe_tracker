#!/usr/bin/env python3
"""
Download all sections for all years and combine them.
"""

import pandas as pd
from pathlib import Path
from joe_working_scraper import JOEWorkingScraper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_and_combine_year(scraper, period, year):
    """Download all sections for a year and combine them."""
    
    sections = {
        "1": "US_Full-Time_Academic",
        "5": "International_Full-Time_Academic"
    }
    
    all_data = []
    
    for section_value, section_name in sections.items():
        logger.info(f"Downloading {year} - {section_name}")
        
        file_path = scraper.download_data(period, section_value)
        
        if file_path:
            df = pd.read_excel(file_path)
            all_data.append(df)
            logger.info(f"  Added {len(df)} postings from {section_name}")
    
    # Combine all sections
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Save combined file
        output_file = scraper.download_dir / f"joe_{year}_all_sections.xlsx"
        combined_df.to_excel(output_file, index=False)
        logger.info(f"✓ Saved combined file: {output_file} ({len(combined_df)} total postings)")
        
        # Remove individual section files to avoid confusion
        for section_value, section_name in sections.items():
            section_file = scraper.download_dir / f"joe_{year}_{section_name}.xlsx"
            if section_file.exists():
                section_file.unlink()
        
        return output_file
    
    return None


def main():
    """Download all years with all sections."""
    
    # Periods to download (last 6 years)
    periods = [
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
            logger.info(f"Processing {year}")
            logger.info(f"{'='*60}")
            
            download_and_combine_year(scraper, period, year)
        
        # Also handle 2025 separately since it's current
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing 2025 (current year)")
        logger.info(f"{'='*60}")
        
        download_and_combine_year(scraper, "August 1, 2025 - January 31, 2026", 2025)
        
        logger.info("\n✅ All downloads complete!")
        
    finally:
        if scraper.driver:
            scraper.driver.quit()


if __name__ == "__main__":
    main()