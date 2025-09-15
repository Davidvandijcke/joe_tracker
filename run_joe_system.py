#!/usr/bin/env python3
"""
Main script to run the complete JOE tracking system.
Downloads data, processes it, and generates visualizations.
"""

import os
import sys
import argparse
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the JOE tracking system."""
    
    parser = argparse.ArgumentParser(
        description='JOE Market Tracker System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download new data (Selenium required)
  python run_joe_system.py --download
  
  # Process existing data and create visualization
  python run_joe_system.py --process
  
  # Run web app
  python run_joe_system.py --webapp
  
  # Do everything
  python run_joe_system.py --all
        """
    )
    
    parser.add_argument('--download', action='store_true',
                       help='Download new data from JOE website')
    parser.add_argument('--process', action='store_true',
                       help='Process data and create visualizations')
    parser.add_argument('--webapp', action='store_true',
                       help='Launch the web application')
    parser.add_argument('--monitor', action='store_true',
                       help='Run the file monitor')
    parser.add_argument('--all', action='store_true',
                       help='Run complete pipeline')
    parser.add_argument('--years', type=int, default=5,
                       help='Number of years to download (default: 5)')
    parser.add_argument('--headless', action='store_true',
                       help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    # If no specific action, show help
    if not any([args.download, args.process, args.webapp, args.monitor, args.all]):
        parser.print_help()
        return
    
    # Handle --all flag
    if args.all:
        args.download = True
        args.process = True
    
    # Step 1: Download data
    if args.download:
        print("\n" + "="*70)
        print("STEP 1: DOWNLOADING JOE DATA")
        print("="*70)
        
        try:
            from joe_working_scraper import JOEWorkingScraper
            
            print(f"Downloading data for {args.years} years...")
            print("Sections: US Academic, International Academic")
            
            scraper = JOEWorkingScraper(headless=args.headless)
            
            # Download just the main academic sections
            scraper.download_all(years=args.years, sections=["1", "5"])
            
            print("✅ Download complete!")
            
        except ImportError:
            print("❌ Scraper not available. Please check installation.")
        except Exception as e:
            print(f"❌ Download failed: {e}")
    
    # Step 2: Process data
    if args.process:
        print("\n" + "="*70)
        print("STEP 2: PROCESSING DATA & CREATING VISUALIZATION")
        print("="*70)
        
        try:
            # Import and run the processing script
            from process_xls_with_openings import main as process_main
            
            print("Processing Excel files...")
            process_main()
            
            # Check if plot was created
            plot_path = Path("joe_openings_plot.png")
            if plot_path.exists():
                print(f"✅ Visualization created: {plot_path}")
                print(f"   File size: {plot_path.stat().st_size / 1024:.1f} KB")
            else:
                print("⚠️  Visualization not created")
                
        except ImportError:
            print("❌ Processing script not available")
        except Exception as e:
            print(f"❌ Processing failed: {e}")
    
    # Step 3: Launch web app
    if args.webapp:
        print("\n" + "="*70)
        print("STEP 3: LAUNCHING WEB APPLICATION")
        print("="*70)
        
        try:
            import subprocess
            
            print("Starting Streamlit web app...")
            print("URL: http://localhost:8501")
            print("Press Ctrl+C to stop")
            
            subprocess.run(["streamlit", "run", "joe_web_app.py"])
            
        except ImportError:
            print("❌ Streamlit not installed")
            print("   Install with: pip install streamlit plotly")
        except KeyboardInterrupt:
            print("\n✅ Web app stopped")
        except Exception as e:
            print(f"❌ Web app failed: {e}")
    
    # Step 4: Run monitor
    if args.monitor:
        print("\n" + "="*70)
        print("STEP 4: RUNNING FILE MONITOR")
        print("="*70)
        
        try:
            from simple_joe_monitor import JOEDataMonitor
            
            print("Starting file monitor...")
            print("Drop new Excel files in joe_data/ to auto-update visualizations")
            print("Press Ctrl+C to stop")
            
            monitor = JOEDataMonitor()
            monitor.run_monitor()
            
        except ImportError:
            print("❌ Monitor not available")
        except KeyboardInterrupt:
            print("\n✅ Monitor stopped")
        except Exception as e:
            print(f"❌ Monitor failed: {e}")
    
    print("\n" + "="*70)
    print("JOE TRACKING SYSTEM COMPLETE")
    print("="*70)
    
    # Summary
    data_dir = Path("joe_data")
    if data_dir.exists():
        excel_files = list(data_dir.glob("*.xlsx"))
        print(f"\nData files: {len(excel_files)} Excel files")
        
        plot_path = Path("joe_openings_plot.png")
        if plot_path.exists():
            print(f"Visualization: ✅ {plot_path}")
        else:
            print("Visualization: ❌ Not created")
        
        print("\nNext steps:")
        print("1. View visualization: open joe_openings_plot.png")
        print("2. Launch web app: python run_joe_system.py --webapp")
        print("3. Download more data: python run_joe_system.py --download --years 10")


if __name__ == "__main__":
    main()