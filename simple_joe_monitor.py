#!/usr/bin/env python3
"""
Simple JOE data monitor and visualization updater.
Since we already have Excel files, this script monitors them and updates visualizations.
Manual download instructions included for updating data.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

import pandas as pd

from process_xls_with_openings import (
    process_xls_files,
    analyze_date_fields,
    filter_us_academic,
    create_weekly_cumulative,
    create_aea_visualization
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('joe_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JOEDataMonitor:
    """Monitor JOE Excel files and update visualizations when data changes."""
    
    def __init__(self):
        """Initialize the monitor."""
        self.data_dir = Path("joe_data")
        self.state_file = self.data_dir / "monitor_state.json"
        self.plot_file = Path("joe_openings_plot.png")
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def get_file_hash(self, filepath: Path) -> str:
        """Calculate hash of a file for change detection."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def load_state(self) -> dict:
        """Load the monitor state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'file_hashes': {},
            'last_update': None,
            'total_openings': 0
        }
    
    def save_state(self, state: dict):
        """Save the monitor state."""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def check_for_updates(self) -> bool:
        """Check if Excel files have changed."""
        state = self.load_state()
        current_hashes = {}
        has_changes = False
        
        # Check all Excel files
        excel_files = list(self.data_dir.glob("*.xlsx")) + list(self.data_dir.glob("*.xls"))
        
        for file in excel_files:
            current_hash = self.get_file_hash(file)
            current_hashes[file.name] = current_hash
            
            if file.name not in state['file_hashes'] or state['file_hashes'][file.name] != current_hash:
                logger.info(f"Detected change in {file.name}")
                has_changes = True
        
        # Check for removed files
        for filename in state['file_hashes']:
            if filename not in current_hashes:
                logger.info(f"File removed: {filename}")
                has_changes = True
        
        if has_changes:
            state['file_hashes'] = current_hashes
            self.save_state(state)
        
        return has_changes
    
    def update_visualization(self):
        """Update the visualization from current Excel files."""
        logger.info("=" * 70)
        logger.info("Updating JOE visualization")
        logger.info("=" * 70)
        
        try:
            # Process all Excel files
            df = process_xls_files()
            
            if df is None or len(df) == 0:
                logger.error("No data to process")
                return False
            
            # Analyze and filter data
            df = analyze_date_fields(df)
            if df is None:
                logger.error("Failed to analyze date fields")
                return False
            
            df = filter_us_academic(df)
            
            # Create visualization
            weekly_data = create_weekly_cumulative(df)
            create_aea_visualization(weekly_data)
            
            # Update state
            state = self.load_state()
            state['last_update'] = datetime.now().isoformat()
            state['total_openings'] = df['position_count'].sum()
            state['total_postings'] = len(df)
            self.save_state(state)
            
            logger.info(f"✅ Visualization updated successfully")
            logger.info(f"   Total openings: {state['total_openings']}")
            logger.info(f"   Total postings: {state['total_postings']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating visualization: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def print_download_instructions(self):
        """Print instructions for manually downloading new data."""
        print("\n" + "=" * 70)
        print("📥 How to Download New JOE Data")
        print("=" * 70)
        print("""
1. Go to: https://www.aeaweb.org/joe/listings.php

2. Apply filters (optional):
   - Section: "US: Full-Time Academic" for academic positions
   - Date range: Select as needed

3. Download the data:
   - Look for "Output current result set to:" dropdown
   - Select "Native XLS" format
   - Click the download/output button
   
4. Save the file to the joe_data/ directory:
   {}/
   
5. The monitor will automatically detect the new file and update the visualization!

Note: You can download multiple filtered datasets (e.g., different years or sections)
      The script will combine all Excel files in the directory.
""".format(self.data_dir.absolute()))
        print("=" * 70 + "\n")
    
    def run_monitor(self, check_interval: int = 300):
        """
        Run the monitor continuously.
        
        Args:
            check_interval: Seconds between checks (default 5 minutes)
        """
        logger.info("Starting JOE data monitor")
        self.print_download_instructions()
        
        # Initial update
        if self.check_for_updates():
            self.update_visualization()
        else:
            logger.info("No changes detected, using existing visualization")
        
        # Monitor loop
        while True:
            try:
                time.sleep(check_interval)
                
                if self.check_for_updates():
                    logger.info("Changes detected, updating visualization...")
                    self.update_visualization()
                else:
                    logger.debug(f"No changes detected (checked at {datetime.now()})")
                    
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(60)  # Wait a bit before retrying
    
    def run_once(self):
        """Run a single update check and visualization update."""
        logger.info("Running single update check...")
        
        if self.check_for_updates():
            logger.info("Changes detected, updating visualization...")
            success = self.update_visualization()
        else:
            logger.info("No changes detected")
            
            # Check if plot exists
            if not self.plot_file.exists():
                logger.info("Plot doesn't exist, creating it...")
                success = self.update_visualization()
            else:
                logger.info("Using existing visualization")
                success = True
        
        # Show current stats
        state = self.load_state()
        if state['last_update']:
            print(f"\nLast update: {state['last_update']}")
            print(f"Total openings: {state.get('total_openings', 'N/A')}")
            print(f"Total postings: {state.get('total_postings', 'N/A')}")
        
        return success


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor JOE Excel files and update visualizations'
    )
    parser.add_argument(
        '--once', 
        action='store_true',
        help='Run once and exit'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Check interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--instructions',
        action='store_true',
        help='Show download instructions and exit'
    )
    
    args = parser.parse_args()
    
    monitor = JOEDataMonitor()
    
    if args.instructions:
        monitor.print_download_instructions()
    elif args.once:
        monitor.run_once()
    else:
        monitor.run_monitor(check_interval=args.interval)


if __name__ == "__main__":
    main()