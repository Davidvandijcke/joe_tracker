#!/usr/bin/env python3
"""
Update only the current year's data while preserving historical data.
This is used by GitHub Actions to update without re-scraping all years.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from generate_static_site import generate_data_json

def update_current_year_only():
    """Update only current year data while preserving historical."""

    # Load existing data
    docs_path = Path('docs')
    data_file = docs_path / 'joe_data.json'

    existing_data = {}
    if data_file.exists():
        try:
            with open(data_file, 'r') as f:
                existing_data = json.load(f)
            print(f"Loaded existing data with {len(existing_data.get('sections', {}))} sections")
        except Exception as e:
            print(f"Error loading existing data: {e}")
            existing_data = {}

    # Generate new data (this will include whatever Excel files are present)
    new_data = generate_data_json()

    # Get current academic year
    current_date = datetime.now()
    current_year = current_date.year if current_date.month >= 7 else current_date.year - 1

    # Merge data: preserve all historical years, update current year
    if 'sections' not in existing_data:
        existing_data['sections'] = {}

    # Update metadata
    existing_data['metadata'] = new_data['metadata']

    # Update current year data in all sections
    for section_name, section_data in new_data.get('sections', {}).items():
        if section_name not in existing_data['sections']:
            existing_data['sections'][section_name] = {}

        # Update current year if it exists in new data
        if str(current_year) in section_data:
            existing_data['sections'][section_name][str(current_year)] = section_data[str(current_year)]
            print(f"Updated {section_name} for year {current_year}")

    # Recalculate total postings
    total_postings = 0
    for section_data in existing_data['sections'].values():
        for year_data in section_data.values():
            total_postings += year_data.get('postings', 0)

    existing_data['metadata']['total_postings'] = total_postings

    # Save merged data
    with open(data_file, 'w') as f:
        json.dump(existing_data, f, separators=(',', ':'))

    print(f"Updated joe_data.json with {total_postings} total postings")
    print(f"Sections in final data: {list(existing_data['sections'].keys())}")

    # Check what years we have
    years_by_section = {}
    for section_name, section_data in existing_data['sections'].items():
        years_by_section[section_name] = list(section_data.keys())

    print("Years available by section:")
    for section, years in years_by_section.items():
        print(f"  {section}: {sorted(years)}")

if __name__ == "__main__":
    update_current_year_only()