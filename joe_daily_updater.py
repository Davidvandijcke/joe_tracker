"""
Daily updater for JOE listings data.
Scrapes new data, processes it, and updates visualizations.
"""

import os
import sys
import logging
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
import json
import traceback
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

# Import our modules
from joe_selenium_scraper import JOEScraper
from process_xls_with_openings import (
    extract_position_count,
    analyze_date_fields,
    filter_us_academic,
    create_weekly_cumulative,
    create_aea_visualization
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('joe_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JOEDataUpdater:
    """Handles daily updates of JOE data and visualizations."""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the updater.
        
        Args:
            data_dir: Base directory for all data storage
        """
        if data_dir is None:
            data_dir = os.path.dirname(__file__)
            
        self.data_dir = Path(data_dir)
        self.joe_data_dir = self.data_dir / 'joe_data'
        self.joe_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Paths for various data files
        self.combined_data_path = self.joe_data_dir / 'combined_listings.csv'
        self.metadata_path = self.joe_data_dir / 'metadata.json'
        self.visualization_path = self.data_dir / 'joe_openings_plot.png'
        
        # Initialize scraper
        self.scraper = JOEScraper(
            download_dir=str(self.joe_data_dir / 'downloads'),
            headless=True
        )
        
    def load_metadata(self) -> Dict:
        """Load metadata about previous runs."""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        return {
            'last_update': None,
            'total_listings': 0,
            'update_history': []
        }
    
    def save_metadata(self, metadata: Dict):
        """Save metadata about the current run."""
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def download_latest_data(self) -> Optional[str]:
        """Download the latest JOE data."""
        logger.info("Starting data download...")
        
        try:
            # Download all listings
            file_path = self.scraper.scrape_listings(
                sections=None,  # Get all sections for comprehensive data
                date_range="all"
            )
            
            if file_path:
                logger.info(f"Successfully downloaded: {file_path}")
                return file_path
            else:
                logger.error("Download failed")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def process_new_data(self, file_path: str) -> pd.DataFrame:
        """
        Process newly downloaded data.
        
        Args:
            file_path: Path to the downloaded Excel file
            
        Returns:
            Processed DataFrame
        """
        logger.info(f"Processing data from {file_path}")
        
        # Read the Excel file
        df = pd.read_excel(file_path)
        logger.info(f"Loaded {len(df)} listings")
        
        # Add position count
        df['position_count'] = df.apply(extract_position_count, axis=1)
        
        # Add download timestamp
        df['download_date'] = datetime.now()
        
        # Ensure required columns exist
        required_columns = ['Date_Active', 'jp_section', 'jp_institution', 'jp_title']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Missing columns: {missing_columns}")
            # Try alternative column names
            column_mapping = {
                'Date_Active': ['date_active', 'DateActive', 'post_date', 'PostDate'],
                'jp_section': ['section', 'Section', 'category', 'Category'],
                'jp_institution': ['institution', 'Institution', 'employer', 'Employer'],
                'jp_title': ['title', 'Title', 'position', 'Position']
            }
            
            for required, alternatives in column_mapping.items():
                if required not in df.columns:
                    for alt in alternatives:
                        if alt in df.columns:
                            df[required] = df[alt]
                            logger.info(f"Mapped {alt} to {required}")
                            break
        
        return df
    
    def update_combined_data(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        Update the combined dataset with new data.
        
        Args:
            new_df: New data to add
            
        Returns:
            Updated combined DataFrame
        """
        # Load existing combined data if it exists
        if self.combined_data_path.exists():
            existing_df = pd.read_csv(self.combined_data_path, parse_dates=['Date_Active', 'download_date'])
            logger.info(f"Loaded {len(existing_df)} existing listings")
            
            # Combine with new data
            # Remove duplicates based on key fields
            key_columns = ['jp_institution', 'jp_title', 'Date_Active']
            
            # Ensure key columns exist in both dataframes
            key_columns = [col for col in key_columns if col in new_df.columns and col in existing_df.columns]
            
            if key_columns:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=key_columns, keep='last')
            else:
                # If we can't deduplicate, just append
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Save combined data
        combined_df.to_csv(self.combined_data_path, index=False)
        logger.info(f"Saved {len(combined_df)} total listings to combined data")
        
        return combined_df
    
    def generate_visualization(self, df: pd.DataFrame):
        """
        Generate the visualization from the data.
        
        Args:
            df: Combined DataFrame with all listings
        """
        logger.info("Generating visualization...")
        
        try:
            # Process the data
            df = analyze_date_fields(df)
            
            if df is None or len(df) == 0:
                logger.error("No valid data after date analysis")
                return
            
            # Filter for US Academic positions
            us_academic_df = filter_us_academic(df)
            
            if len(us_academic_df) == 0:
                logger.warning("No US Academic positions found")
                # Try without filtering
                us_academic_df = df
            
            # Create weekly cumulative data
            weekly_data = create_weekly_cumulative(us_academic_df)
            
            # Generate visualization
            create_aea_visualization(weekly_data)
            
            logger.info(f"Visualization saved to {self.visualization_path}")
            
        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            logger.error(traceback.format_exc())
    
    def run_update(self):
        """Run a complete update cycle."""
        logger.info("=" * 70)
        logger.info(f"Starting update cycle at {datetime.now()}")
        logger.info("=" * 70)
        
        # Load metadata
        metadata = self.load_metadata()
        
        try:
            # Download latest data
            file_path = self.download_latest_data()
            
            if file_path:
                # Process the new data
                new_df = self.process_new_data(file_path)
                
                # Update combined dataset
                combined_df = self.update_combined_data(new_df)
                
                # Generate visualization
                self.generate_visualization(combined_df)
                
                # Update metadata
                metadata['last_update'] = datetime.now().isoformat()
                metadata['total_listings'] = len(combined_df)
                metadata['update_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'new_listings': len(new_df),
                    'total_listings': len(combined_df),
                    'status': 'success'
                })
                
                # Keep only last 30 days of history
                cutoff = datetime.now() - timedelta(days=30)
                metadata['update_history'] = [
                    h for h in metadata['update_history']
                    if datetime.fromisoformat(h['timestamp']) > cutoff
                ]
                
                self.save_metadata(metadata)
                
                # Archive old download files
                self.scraper.archive_old_files(days_to_keep=7)
                
                logger.info("Update cycle completed successfully")
                
            else:
                logger.error("Update cycle failed - no data downloaded")
                metadata['update_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'status': 'failed',
                    'error': 'Download failed'
                })
                self.save_metadata(metadata)
                
        except Exception as e:
            logger.error(f"Error during update cycle: {e}")
            logger.error(traceback.format_exc())
            
            metadata['update_history'].append({
                'timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'error': str(e)
            })
            self.save_metadata(metadata)
    
    def schedule_updates(self, hour: int = 2, minute: int = 0):
        """
        Schedule daily updates.
        
        Args:
            hour: Hour to run update (24-hour format)
            minute: Minute to run update
        """
        # Schedule daily update
        schedule_time = f"{hour:02d}:{minute:02d}"
        schedule.every().day.at(schedule_time).do(self.run_update)
        
        logger.info(f"Scheduled daily updates at {schedule_time}")
        
        # Run immediately on start
        self.run_update()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


def main():
    """Main function to run the updater."""
    import argparse
    
    parser = argparse.ArgumentParser(description='JOE Data Updater')
    parser.add_argument('--once', action='store_true', 
                       help='Run once and exit (no scheduling)')
    parser.add_argument('--hour', type=int, default=2,
                       help='Hour to run daily update (24-hour format)')
    parser.add_argument('--minute', type=int, default=0,
                       help='Minute to run daily update')
    
    args = parser.parse_args()
    
    # Initialize updater
    updater = JOEDataUpdater()
    
    if args.once:
        # Run once and exit
        updater.run_update()
    else:
        # Schedule daily updates
        try:
            updater.schedule_updates(hour=args.hour, minute=args.minute)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")


if __name__ == "__main__":
    main()