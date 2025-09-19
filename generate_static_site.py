#!/usr/bin/env python3
"""
Generate static HTML/JS site for GitHub Pages hosting.
This creates a standalone website that doesn't need Python/Streamlit.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from process_xls_with_openings import process_xls_files, analyze_date_fields, filter_us_academic, create_weekly_cumulative


def generate_data_json():
    """Generate JSON data file from Excel sources."""
    # Process data
    df = process_xls_files()

    # Handle empty DataFrame
    if df.empty:
        print("No data files found. Creating empty dataset.")
        return {
            'metadata': {
                'last_update': datetime.now().isoformat(),
                'total_postings': 0,
                'date_range': {
                    'start': None,
                    'end': None
                }
            },
            'sections': {}
        }

    df = analyze_date_fields(df)

    # For 2019-2024, we only have US Academic data
    # For 2025, we have all sections
    # So we'll create an "all_sections" view that combines available data

    sections_data = {}
    
    # Process US Academic (all years have this)
    us_academic_df = df[df['jp_section'].str.contains('US: Full-Time Academic', na=False, case=False)]
    if len(us_academic_df) > 0:
        weekly_data = create_weekly_cumulative(us_academic_df)
        section_json = {}
        for year, data in weekly_data.items():
            # For current year, truncate at last available week
            weeks = [int(w) for w in data['weeks']]
            cumulative = [int(c) for c in data['cumulative']]
            
            # If 2025/current year, find last week with data
            if year == 2025 and len(weeks) > 0:
                # Find last non-zero increment
                for i in range(len(cumulative) - 1, 0, -1):
                    if cumulative[i] > cumulative[i-1]:
                        weeks = weeks[:i+1]
                        cumulative = cumulative[:i+1]
                        break
            
            section_json[str(year)] = {
                'weeks': weeks,
                'cumulative': cumulative,
                'total': int(data['total']),
                'postings': int(data['postings'])
            }
        sections_data['us_academic'] = section_json
    
    # For "all sections" view - combine all available data per year
    all_sections_data = {}
    for year in df['academic_year'].unique():
        year_df = df[df['academic_year'] == year]
        weekly_data = create_weekly_cumulative(year_df)
        
        if year in weekly_data:
            data = weekly_data[year]
            weeks = [int(w) for w in data['weeks']]
            cumulative = [int(c) for c in data['cumulative']]
            
            # Truncate current year at last data point
            if year == 2025 and len(weeks) > 0:
                for i in range(len(cumulative) - 1, 0, -1):
                    if cumulative[i] > cumulative[i-1]:
                        weeks = weeks[:i+1]
                        cumulative = cumulative[:i+1]
                        break
            
            all_sections_data[str(year)] = {
                'weeks': weeks,
                'cumulative': cumulative,
                'total': int(data['total']),
                'postings': int(data['postings'])
            }
    sections_data['all_sections'] = all_sections_data
    
    # Process other sections (only 2025 has these)
    other_sections = {
        'intl_academic': 'International: Full-Time Academic',
        'nonacademic': 'Nonacademic'
    }
    
    for section_key, section_filter in other_sections.items():
        section_df = df[df['jp_section'].str.contains(section_filter, na=False, case=False)]
        if len(section_df) > 0:
            weekly_data = create_weekly_cumulative(section_df)
            section_json = {}
            for year, data in weekly_data.items():
                weeks = [int(w) for w in data['weeks']]
                cumulative = [int(c) for c in data['cumulative']]
                
                # Truncate at last data point
                if len(weeks) > 0:
                    for i in range(len(cumulative) - 1, 0, -1):
                        if cumulative[i] > cumulative[i-1]:
                            weeks = weeks[:i+1]
                            cumulative = cumulative[:i+1]
                            break
                
                section_json[str(year)] = {
                    'weeks': weeks,
                    'cumulative': cumulative,
                    'total': int(data['total']),
                    'postings': int(data['postings'])
                }
            sections_data[section_key] = section_json
    
    # Add metadata
    metadata = {
        'last_update': datetime.now().isoformat(),
        'total_postings': len(df),
        'date_range': {
            'start': str(df['Date_Active'].min()),
            'end': str(df['Date_Active'].max())
        }
    }
    
    return {
        'metadata': metadata,
        'sections': sections_data
    }


def generate_html():
    """Generate the HTML file for the static site."""
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JOE Market Tracker</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            border: 1px solid #e0e0e0;
            padding: 30px;
            margin-bottom: 30px;
        }
        
        h1 {
            color: #1a1a1a;
            font-size: 2em;
            font-weight: 600;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 1em;
            margin-bottom: 20px;
        }
        
        .automation-note {
            background: #f8f9fa;
            border-left: 4px solid #0066cc;
            padding: 12px 16px;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #555;
        }
        
        .controls {
            background: white;
            border: 1px solid #e0e0e0;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .control-group {
            margin-bottom: 25px;
        }
        
        .control-group:last-child {
            margin-bottom: 0;
        }
        
        .control-group label {
            display: block;
            font-weight: 500;
            color: #333;
            margin-bottom: 12px;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .year-selector {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .year-btn {
            padding: 8px 14px;
            border: 1px solid #ccc;
            background: white;
            color: #333;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 400;
            font-size: 0.95em;
        }
        
        .year-btn:hover {
            background: #f0f0f0;
            border-color: #999;
        }
        
        .year-btn.active {
            background: #333;
            color: white;
            border-color: #333;
        }
        
        select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            font-size: 0.95em;
            background: white;
            cursor: pointer;
            color: #333;
        }
        
        select:focus {
            outline: none;
            border-color: #666;
        }
        
        .chart-container {
            background: white;
            border: 1px solid #e0e0e0;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: white;
            border: 1px solid #e0e0e0;
            padding: 20px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 1.8em;
            font-weight: 600;
            color: #1a1a1a;
        }
        
        .metric-label {
            color: #666;
            margin-top: 5px;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .update-info {
            font-size: 0.9em;
            color: #666;
        }
        
        footer {
            text-align: center;
            color: #666;
            margin-top: 50px;
            padding: 20px;
            font-size: 0.9em;
        }
        
        footer a {
            color: #0066cc;
            text-decoration: none;
        }
        
        footer a:hover {
            text-decoration: underline;
        }
        
        @media (max-width: 768px) {
            h1 {
                font-size: 1.5em;
            }
            
            .controls {
                padding: 15px;
            }
            
            .year-btn {
                padding: 6px 12px;
                font-size: 0.9em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>JOE Market Tracker</h1>
            <p class="subtitle">Track job openings for economists from AEA JOE listings</p>
            <div class="automation-note">
                <strong>Automated Updates:</strong> This site automatically refreshes data every Friday at 5:00 PM EST.
            </div>
            <div class="update-info" id="updateInfo">Loading...</div>
        </header>
        
        <div class="controls">
            <div class="control-group">
                <label>Select Years</label>
                <div class="year-selector" id="yearSelector"></div>
            </div>
            
            <div class="control-group">
                <label>Select Section</label>
                <select id="sectionSelector">
                    <option value="all_sections">All Sections</option>
                    <option value="us_academic">US: Full-Time Academic</option>
                    <option value="intl_academic">International: Full-Time Academic</option>
                    <option value="nonacademic">Nonacademic</option>
                </select>
            </div>
        </div>
        
        <div class="metrics" id="metrics"></div>
        
        <div class="chart-container">
            <div id="mainChart"></div>
        </div>
        
        <div class="chart-container">
            <div id="comparisonChart"></div>
        </div>
        
        <footer>
            <p>Data source: <a href="https://www.aeaweb.org/joe/listings" target="_blank">AEA JOE</a></p>
            <p>View source on <a href="https://github.com/Davidvandijcke/joe_tracker" target="_blank">GitHub</a></p>
        </footer>
    </div>
    
    <script>
        let jobData = null;
        let selectedYears = [2023, 2024, 2025];
        let selectedSection = 'all_sections';
        
        const colors = {
            2019: '#4A90E2',
            2020: '#E94B3C',
            2021: '#2ECC71',
            2022: '#9B59B6',
            2023: '#F39C12',
            2024: '#1ABC9C',
            2025: '#FFD700',
            2026: '#FF69B4'
        };
        
        // Load data
        fetch('joe_data.json')
            .then(response => response.json())
            .then(data => {
                jobData = data;
                initializeApp();
            })
            .catch(error => {
                console.error('Error loading data:', error);
                document.getElementById('updateInfo').textContent = 'Error loading data';
            });
        
        function initializeApp() {
            // Display update info
            const updateDate = new Date(jobData.metadata.last_update);
            document.getElementById('updateInfo').textContent = 
                `Last updated: ${updateDate.toLocaleDateString()} at ${updateDate.toLocaleTimeString()}`;
            
            // Create year selectors
            const yearSelector = document.getElementById('yearSelector');
            const availableYears = new Set();
            
            Object.values(jobData.sections).forEach(section => {
                Object.keys(section).forEach(year => availableYears.add(parseInt(year)));
            });
            
            Array.from(availableYears).sort().forEach(year => {
                const btn = document.createElement('button');
                btn.className = 'year-btn';
                btn.textContent = year;
                btn.dataset.year = year;
                
                if (selectedYears.includes(year)) {
                    btn.classList.add('active');
                }
                
                btn.onclick = () => toggleYear(year);
                yearSelector.appendChild(btn);
            });
            
            // Add section selector listener
            document.getElementById('sectionSelector').onchange = (e) => {
                selectedSection = e.target.value;
                updateVisualization();
            };
            
            // Initial render
            updateVisualization();
        }
        
        function toggleYear(year) {
            const index = selectedYears.indexOf(year);
            if (index > -1) {
                selectedYears.splice(index, 1);
            } else {
                selectedYears.push(year);
            }
            
            // Update button states
            document.querySelectorAll('.year-btn').forEach(btn => {
                const btnYear = parseInt(btn.dataset.year);
                if (selectedYears.includes(btnYear)) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            
            updateVisualization();
        }
        
        function updateVisualization() {
            if (!jobData || selectedYears.length === 0) return;
            
            const sectionData = jobData.sections[selectedSection] || {};
            
            // Calculate metrics
            let totalOpenings = 0;
            let totalPostings = 0;
            
            selectedYears.forEach(year => {
                if (sectionData[year]) {
                    totalOpenings += sectionData[year].total;
                    totalPostings += sectionData[year].postings;
                }
            });
            
            // Calculate average openings per year
            const avgPerYear = selectedYears.length > 0 ? Math.round(totalOpenings / selectedYears.length) : 0;
            
            // Get current year's openings if selected
            const currentYear = new Date().getFullYear();
            const currentAcademicYear = new Date().getMonth() >= 7 ? currentYear : currentYear - 1;
            let currentYearOpenings = 0;
            if (selectedYears.includes(currentAcademicYear) && sectionData[currentAcademicYear]) {
                currentYearOpenings = sectionData[currentAcademicYear].total;
            }
            
            // Update metrics
            const metricsHtml = `
                <div class="metric-card">
                    <div class="metric-value">${totalOpenings.toLocaleString()}</div>
                    <div class="metric-label">Total Openings</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${totalPostings.toLocaleString()}</div>
                    <div class="metric-label">Total Postings</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${avgPerYear.toLocaleString()}</div>
                    <div class="metric-label">Avg Openings/Year</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${currentYearOpenings > 0 ? currentYearOpenings.toLocaleString() : 'N/A'}</div>
                    <div class="metric-label">${currentAcademicYear} Openings</div>
                </div>
            `;
            document.getElementById('metrics').innerHTML = metricsHtml;
            
            // Create main plot
            const traces = [];
            
            selectedYears.sort().reverse().forEach(year => {
                if (sectionData[year]) {
                    const yearData = sectionData[year];
                    traces.push({
                        x: yearData.weeks,
                        y: yearData.cumulative,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: year.toString(),
                        line: { color: colors[year], width: 2.5 },
                        marker: { size: 5 }
                    });
                }
            });
            
            const layout = {
                title: 'JOE Openings by Week (Pre-ASSA Listings, Aug-Dec)',
                xaxis: { 
                    title: 'Week of Year (ISO)',
                    gridcolor: '#e0e0e0',
                    range: [29, 54]
                },
                yaxis: { 
                    title: 'Number of Openings (Cumulative)',
                    gridcolor: '#e0e0e0'
                },
                hovermode: 'x unified',
                height: 500,
                paper_bgcolor: 'white',
                plot_bgcolor: '#f8f9fa'
            };
            
            Plotly.newPlot('mainChart', traces, layout, {responsive: true});
            
            // Create comparison chart
            const comparisonData = [];
            selectedYears.forEach(year => {
                if (sectionData[year]) {
                    comparisonData.push({
                        year: year,
                        total: sectionData[year].total
                    });
                }
            });
            
            const compTrace = {
                x: comparisonData.map(d => d.year),
                y: comparisonData.map(d => d.total),
                type: 'bar',
                marker: {
                    color: comparisonData.map(d => colors[d.year])
                },
                text: comparisonData.map(d => d.total),
                textposition: 'outside'
            };
            
            const compLayout = {
                title: 'Total Openings by Year',
                xaxis: { title: 'Academic Year' },
                yaxis: { title: 'Total Openings' },
                height: 400,
                paper_bgcolor: 'white',
                plot_bgcolor: '#f8f9fa'
            };
            
            Plotly.newPlot('comparisonChart', [compTrace], compLayout, {responsive: true});
        }
    </script>
</body>
</html>"""
    
    return html_content


def generate_github_action():
    """Generate GitHub Action workflow for automatic updates."""
    
    workflow = """name: Update JOE Data

on:
  schedule:
    # Run at 5pm EST every Friday (22:00 UTC, day 5)
    - cron: '0 22 * * 5'
  workflow_dispatch:  # Allow manual trigger

jobs:
  update-data:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install Chrome
      uses: browser-actions/setup-chrome@latest
    
    - name: Install dependencies
      run: |
        pip install selenium pandas openpyxl matplotlib
        pip install webdriver-manager
    
    - name: Run scraper
      run: |
        python joe_working_scraper.py --years 1 --headless
    
    - name: Generate static site
      run: |
        python generate_static_site.py
    
    - name: Commit and push if changed
      run: |
        git config --global user.email "action@github.com"
        git config --global user.name "GitHub Action"
        git add -A
        git diff --quiet && git diff --staged --quiet || (git commit -m "Auto-update JOE data" && git push)
"""
    
    return workflow


def main():
    """Generate the static site files."""
    
    print("Generating static site for GitHub Pages...")
    
    # Create output directory
    output_dir = Path("docs")  # GitHub Pages looks for this
    output_dir.mkdir(exist_ok=True)
    
    # Generate data JSON
    print("Processing data...")
    data = generate_data_json()
    
    with open(output_dir / "joe_data.json", "w") as f:
        json.dump(data, f)
    print(f"✓ Generated joe_data.json")
    
    # Generate HTML
    print("Generating HTML...")
    html = generate_html()
    
    with open(output_dir / "index.html", "w") as f:
        f.write(html)
    print(f"✓ Generated index.html")
    
    # Generate GitHub Action workflow
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    with open(workflow_dir / "update-joe-data.yml", "w") as f:
        f.write(generate_github_action())
    print(f"✓ Generated GitHub Action workflow")
    
    # Create README for GitHub
    readme = """# JOE Market Tracker

Live site: https://davidvandijcke.com/joe_tracker/

This repository automatically tracks job openings for economists from the AEA JOE website.

## Features
- Weekly automatic updates every Friday at 5pm EST
- Interactive visualizations
- Year and section filtering
- Historical data from 2019-present

## Setup
1. Fork this repository
2. Enable GitHub Pages from Settings > Pages > Source: Deploy from branch (main, /docs)
3. Enable Actions from Settings > Actions
4. Update the username in the README

The site will be available at: https://[your-username].github.io/[repo-name]/
"""
    
    with open("README.md", "w") as f:
        f.write(readme)
    print(f"✓ Generated README.md")
    
    print("\n" + "="*60)
    print("Static site generated successfully!")
    print("="*60)
    print("\nTo deploy on GitHub:")
    print("1. Create a new GitHub repository")
    print("2. Push these files to the repository")
    print("3. Enable GitHub Pages (Settings > Pages > Source: /docs)")
    print("4. Your site will be at: https://[username].github.io/[repo-name]/")
    print("\nThe GitHub Action will automatically update data every Friday at 5pm EST")


if __name__ == "__main__":
    main()
