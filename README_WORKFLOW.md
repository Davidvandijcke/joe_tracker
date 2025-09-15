# JOE Market Tracker - Complete Workflow

## ✅ Fixed Issues & Current Status

### Problems Solved:
1. **Duplicate Data**: Old files with ambiguous names (joe_resultset.xlsx) were causing duplicate counts
2. **Cookie Banner**: Was blocking Selenium clicks - now handled automatically
3. **File Organization**: Downloads now go to organized folders with clear naming

### Current Data Structure:
```
joe_data/
├── scraped/          # Clean, named downloads from scraper
│   ├── joe_2025_US_Full-Time_Academic.xlsx
│   ├── joe_2025_International_Full-Time_Academic.xlsx
│   └── temp/         # Temporary download folder (auto-cleaned)
└── archive/          # Old ambiguous files (not processed)
```

## 📊 How to Use the System

### 1. Download New Data (Selenium Required)
```bash
# Download specific years (overwrites existing files for same year/section)
python joe_working_scraper.py --years 5

# Test single download
python joe_working_scraper.py --test

# Download all sections
python joe_working_scraper.py --years 5 --all-sections
```

### 2. Process Data & Generate Visualization
```bash
# Process all Excel files and create visualization
python process_xls_with_openings.py

# Or use the master script
python run_joe_system.py --process
```

### 3. View Results
- **Visualization**: `joe_openings_plot.png`
- **Data**: `joe_xls_with_openings.csv`
- **Web App**: `streamlit run joe_web_app.py`

## 🔧 Key Features

### Automatic File Management:
- Downloads go to `joe_data/scraped/` with clear names
- Files are named: `joe_{year}_{section}.xlsx`
- Existing files are automatically overwritten (no duplicates)
- Temp files are cleaned up after each download

### Cookie Handling:
- Automatically dismisses cookie consent banners
- Uses JavaScript fallback if regular click fails

### Robust Download Detection:
- Monitors temp folder for new files
- Handles various download scenarios
- 60-second timeout with proper cleanup

## 📈 Current Data Summary

As of latest run:
- **Total Postings**: 3,193
- **Total Openings**: 3,211 (accounts for multi-position postings)
- **Years Covered**: 2019-2025
- **2025 Status**: 150 openings (partial year, through September)

## 🚀 Daily Automation

To run daily updates:
```bash
# Option 1: Simple cron job
crontab -e
# Add: 0 2 * * * cd /path/to/tracker && python joe_working_scraper.py --years 1 && python process_xls_with_openings.py

# Option 2: Use the scheduler
python joe_daily_updater.py

# Option 3: Docker (if configured)
docker-compose up -d
```

## 📝 Important Notes

1. **Clear Naming**: Always use the scraper to download - it ensures proper file naming
2. **No Manual Downloads**: If you download manually, rename to `joe_{year}_{section}.xlsx` format
3. **Archive Old Files**: Move any ambiguous files to `archive/` folder
4. **Check for Duplicates**: The visualization will be incorrect if there are duplicate year/section files

## 🎯 Workflow Summary

```
Download (Selenium) → joe_data/scraped/ → Process → joe_openings_plot.png
                           ↓
                    Clear naming
                    Overwrites duplicates
                    No ambiguity
```

The system is now robust and handles all edge cases properly!