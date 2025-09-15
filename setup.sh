#!/bin/bash

# Setup script for JOE Market Tracker
# This script helps set up the environment for local development or deployment

echo "==================================="
echo "JOE Market Tracker Setup"
echo "==================================="

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi

echo "✓ Python version check passed ($python_version)"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating data directories..."
mkdir -p joe_data/downloads
mkdir -p joe_data/archive
mkdir -p logs

# Check Chrome installation
if command -v google-chrome &> /dev/null; then
    echo "✓ Google Chrome is installed"
    chrome_version=$(google-chrome --version | awk '{print $3}')
    echo "  Version: $chrome_version"
else
    echo "⚠ Google Chrome is not installed"
    echo "  Please install Chrome for Selenium to work:"
    echo "  - Mac: brew install --cask google-chrome"
    echo "  - Ubuntu: sudo apt-get install google-chrome-stable"
    echo "  - Or download from: https://www.google.com/chrome/"
fi

# Check ChromeDriver
if command -v chromedriver &> /dev/null; then
    echo "✓ ChromeDriver is installed"
    driver_version=$(chromedriver --version | awk '{print $2}')
    echo "  Version: $driver_version"
else
    echo "⚠ ChromeDriver is not installed"
    echo "  Installing ChromeDriver..."
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install --cask chromedriver
        else
            echo "  Please install ChromeDriver manually or install Homebrew first"
        fi
    else
        # Linux
        echo "  Please install ChromeDriver manually:"
        echo "  wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE/chromedriver_linux64.zip"
        echo "  unzip chromedriver_linux64.zip"
        echo "  sudo mv chromedriver /usr/local/bin/"
    fi
fi

# Create .env file template if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env template..."
    cat > .env << EOF
# Environment variables for JOE Market Tracker

# Data directories (optional - defaults will be used if not set)
JOE_DATA_DIR=./joe_data
LOG_DIR=./logs

# Scraper settings
HEADLESS_BROWSER=true
DOWNLOAD_TIMEOUT=60

# Update schedule (24-hour format)
UPDATE_HOUR=2
UPDATE_MINUTE=0

# Web app settings
STREAMLIT_PORT=8501
EOF
    echo "✓ Created .env file (please review and update as needed)"
fi

echo ""
echo "==================================="
echo "Setup completed successfully!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Test the scraper: python joe_selenium_scraper.py"
echo "3. Run the web app: streamlit run joe_web_app.py"
echo "4. For automated updates: python joe_daily_updater.py"
echo ""
echo "For Docker deployment:"
echo "  docker-compose up -d"
echo ""