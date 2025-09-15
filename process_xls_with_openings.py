import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from matplotlib.ticker import MultipleLocator
import numpy as np
from datetime import datetime
import os
from glob import glob
import re

def extract_position_count(row):
    """Extract the number of positions from title and full text."""
    
    # Default to 1 position
    count = 1
    
    # Check title first
    title = str(row.get('jp_title', '')).lower()
    
    # Direct number patterns in title
    number_patterns = [
        (r'\((\d+) positions?\)', 1),  # (4 positions)
        (r'(\d+) tenure[- ]?track position', 1),  # 2 tenure-track positions
        (r'(\d+) position', 1),  # 3 positions
        (r'\btwo\b', 2),
        (r'\bthree\b', 3),
        (r'\bfour\b', 4),
        (r'\bfive\b', 5),
        (r'\bsix\b', 6),
        (r'\bseveral\b', 3),  # Conservative estimate
        (r'\bmultiple\b', 2),  # Conservative estimate
    ]
    
    for pattern, value in number_patterns:
        match = re.search(pattern, title)
        if match:
            if isinstance(value, int):
                count = value
            else:
                count = int(match.group(1))
            break
    
    # If no match in title, check full text for explicit mentions
    if count == 1:
        full_text = str(row.get('jp_full_text', '')).lower()
        
        # More specific patterns for full text
        text_patterns = [
            (r'we (?:are|have) (\d+) (?:openings|positions|vacancies)', 1),
            (r'(\d+) tenure[- ]?track positions?', 1),
            (r'hiring (\d+) (?:assistant|associate|full)', 1),
            (r'invites applications for (\d+)', 1),
            (r'we seek (\d+)', 1),
            (r'recruiting (\d+)', 1),
            (r'we (?:are|have) two', 2),
            (r'we (?:are|have) three', 3),
            (r'we (?:are|have) four', 4),
            (r'we (?:are|have) five', 5),
        ]
        
        for pattern, value in text_patterns:
            match = re.search(pattern, full_text[:1000])  # Check first 1000 chars
            if match:
                if isinstance(value, int):
                    count = value
                else:
                    try:
                        count = int(match.group(1))
                    except:
                        count = 1
                break
    
    # Cap at reasonable number
    return min(count, 10)

def process_xls_files():
    """Process XLS files with date_active field for accurate week-by-week visualization."""
    
    # Find all XLS files in both main directory and scraped subdirectory
    xls_dir = '/Users/davidvandijcke/University of Michigan Dropbox/David Van Dijcke/job_market/tracker/joe_data/'
    
    # Get files from main directory
    xls_files = glob(os.path.join(xls_dir, '*.xlsx'))
    
    # Also get files from scraped subdirectory
    scraped_dir = os.path.join(xls_dir, 'scraped')
    if os.path.exists(scraped_dir):
        xls_files.extend(glob(os.path.join(scraped_dir, '*.xlsx')))
    
    print("Processing XLS files - Counting Job OPENINGS (not just postings)")
    print("=" * 70)
    
    all_data = []
    
    for file_path in sorted(xls_files):
        filename = os.path.basename(file_path)
        print(f"\nReading {filename}")
        
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Add to collection
        df['source_file'] = filename
        all_data.append(df)
        
        print(f"  Postings: {len(df)}")
    
    # Combine all data
    full_df = pd.concat(all_data, ignore_index=True)
    print(f"\nTotal postings across all files: {len(full_df)}")
    
    # Extract position counts
    print("\nExtracting position counts from postings...")
    full_df['position_count'] = full_df.apply(extract_position_count, axis=1)
    
    # Show statistics
    multi_position = full_df[full_df['position_count'] > 1]
    print(f"Postings with multiple positions: {len(multi_position)}")
    print(f"Total job OPENINGS: {full_df['position_count'].sum()}")
    print(f"Average positions per posting: {full_df['position_count'].mean():.2f}")
    
    if len(multi_position) > 0:
        print("\nSample of multi-position postings:")
        for idx, row in multi_position.head(5).iterrows():
            print(f"  - {row['jp_institution']}: {row['jp_title'][:60]} ({row['position_count']} positions)")
    
    # Save for inspection
    full_df.to_csv('joe_xls_with_openings.csv', index=False)
    print("\nSaved data with opening counts to 'joe_xls_with_openings.csv'")
    
    return full_df

def analyze_date_fields(df):
    """Analyze the Date_Active field and calculate ISO weeks."""
    
    print("\n" + "=" * 70)
    print("Analyzing Date_Active field")
    print("=" * 70)
    
    if 'Date_Active' not in df.columns:
        print("ERROR: Date_Active column not found!")
        return None
    
    # Convert Date_Active to datetime
    df['Date_Active'] = pd.to_datetime(df['Date_Active'], errors='coerce')
    
    # Remove rows with invalid dates
    valid_dates = df['Date_Active'].notna()
    print(f"Valid dates: {valid_dates.sum()} / {len(df)}")
    
    df = df[valid_dates].copy()
    
    # Calculate ISO week and year
    df['iso_year'] = df['Date_Active'].dt.isocalendar().year
    df['iso_week'] = df['Date_Active'].dt.isocalendar().week
    
    # Add academic year (August to July)
    df['academic_year'] = df['Date_Active'].apply(
        lambda x: x.year if x.month >= 8 else x.year - 1
    )
    
    print(f"\nDate range: {df['Date_Active'].min()} to {df['Date_Active'].max()}")
    print(f"ISO weeks range: {df['iso_week'].min()} to {df['iso_week'].max()}")
    print(f"Academic years: {sorted(df['academic_year'].unique())}")
    
    return df

def filter_us_academic(df):
    """Filter for US Academic positions."""
    
    print("\n" + "=" * 70)
    print("Filtering for US Academic positions")
    print("=" * 70)
    
    # Filter for US Academic
    us_academic = df[df['jp_section'].str.contains('US: Full-Time Academic', na=False, case=False)]
    
    print(f"US Academic postings: {len(us_academic)}")
    print(f"US Academic OPENINGS: {us_academic['position_count'].sum()}")
    
    return us_academic

def create_weekly_cumulative(df):
    """Create weekly cumulative counts of JOB OPENINGS following AEA methodology."""
    
    print("\n" + "=" * 70)
    print("Creating weekly cumulative OPENING counts")
    print("=" * 70)
    
    # Group by academic year and ISO week
    weekly_data = {}
    
    for ac_year in sorted(df['academic_year'].unique()):
        year_data = df[df['academic_year'] == ac_year]
        
        # Count OPENINGS (not postings) by ISO week
        week_openings = year_data.groupby('iso_week')['position_count'].sum()
        
        # Create cumulative from week 30 onwards
        weeks = range(30, 58)
        cumulative = []
        total_so_far = 0
        
        for week in weeks:
            if week in week_openings.index:
                total_so_far += week_openings[week]
            cumulative.append(total_so_far)
        
        weekly_data[ac_year] = {
            'weeks': list(weeks),
            'cumulative': cumulative,
            'total': total_so_far,
            'postings': len(year_data)
        }
        
        print(f"Academic year {ac_year}-{ac_year+1}:")
        print(f"  Total OPENINGS: {total_so_far}")
        print(f"  Total postings: {len(year_data)}")
        print(f"  Avg openings/posting: {total_so_far/len(year_data) if len(year_data) > 0 else 0:.2f}")
        print(f"  Week 30-35 openings: {cumulative[5] if len(cumulative) > 5 else 0}")
        print(f"  Week 48 openings: {cumulative[18] if len(cumulative) > 18 else 0}")
    
    return weekly_data

def create_aea_visualization(weekly_data):
    """Create visualization following exact AEA methodology."""
    
    print("\n" + "=" * 70)
    print("Creating AEA-methodology visualization")
    print("=" * 70)
    
    # Create figure matching the original style
    fig, ax = plt.subplots(figsize=(14, 8), facecolor='#1a1a1a')
    ax.set_facecolor('#1a1a1a')
    
    colors = {
        2019: '#4A90E2',  # Blue
        2020: '#E94B3C',  # Red - COVID year
        2021: '#2ECC71',  # Green
        2022: '#9B59B6',  # Purple
        2023: '#F39C12',  # Orange
        2024: '#1ABC9C',  # Teal
        2025: '#FFD700'   # Gold - partial year
    }
    
    # Store data for zoom inset
    plot_data = {}
    
    # Plot each academic year in reverse order for legend
    for ac_year in sorted(weekly_data.keys(), reverse=True):
        if ac_year not in colors:
            continue
            
        data = weekly_data[ac_year]
        weeks = np.array(data['weeks'])
        cumulative = np.array(data['cumulative'])
        
        # For 2025 (partial), only show data up to week 37
        if ac_year == 2025:
            # Cut off at week 37
            week_37_idx = 7  # weeks 30, 31, 32, 33, 34, 35, 36, 37
            weeks = weeks[:week_37_idx + 1]
            cumulative = cumulative[:week_37_idx + 1]
            label = f'{ac_year} (partial)'
        else:
            label = str(ac_year)
        
        # Store for zoom
        plot_data[ac_year] = (weeks, cumulative)
        
        # Plot
        ax.plot(weeks, cumulative,
                color=colors[ac_year],
                linewidth=2.5,
                marker='o',
                markersize=5,
                label=label,
                alpha=0.9)
        
        # Add end value label
        if len(weeks) > 0 and len(cumulative) > 0:
            ax.text(weeks[-1] + 0.5, cumulative[-1],
                    f'{int(cumulative[-1])}',
                    color=colors[ac_year],
                    fontsize=11,
                    va='center',
                    fontweight='bold')
    
    # Add titles
    ax.text(0.5, 1.02,
            'JOE Openings by Week (Pre-ASSA Listings, Aug-Dec)',
            transform=ax.transAxes,
            ha='center',
            fontsize=16,
            color='white',
            fontweight='bold')
    
    ax.text(0.5, 0.98,
            'Section 1: US: Full-Time Academic (Permanent, Tenure Track or Tenured)',
            transform=ax.transAxes,
            ha='center',
            fontsize=13,
            color='white')
    
    # Set axes
    ax.set_xlabel('Week of Year (ISO)', fontsize=12, color='white')
    ax.set_ylabel('Number of Openings (Cumulative)', fontsize=12, color='white')
    ax.set_xlim(29, 58)
    ax.set_ylim(0, 700)
    
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.yaxis.set_major_locator(MultipleLocator(100))
    
    # Grid
    ax.grid(True, color='#404040', linestyle='-', linewidth=0.5, alpha=0.7)
    ax.tick_params(colors='white', which='both')
    
    # Add zoom inset for weeks 31-37
    axins = ax.inset_axes([0.08, 0.43, 0.32, 0.32])
    axins.set_facecolor('#1a1a1a')
    
    # Plot zoomed data
    for ac_year in sorted(plot_data.keys(), reverse=True):
        if ac_year in colors:
            weeks, cumulative = plot_data[ac_year]
            zoom_mask = (weeks >= 31) & (weeks <= 37)
            if any(zoom_mask):
                axins.plot(weeks[zoom_mask], cumulative[zoom_mask],
                          color=colors[ac_year],
                          linewidth=2,
                          marker='o',
                          markersize=4,
                          alpha=0.9)
    
    axins.set_xlim(30.5, 37.5)
    axins.set_ylim(-5, 120)
    axins.grid(True, color='#404040', linestyle='-', linewidth=0.3, alpha=0.5)
    axins.tick_params(colors='white', labelsize=8)
    axins.set_xlabel('Week', fontsize=9, color='white')
    axins.set_ylabel('Openings', fontsize=9, color='white')
    axins.set_title('Weeks 31-37 Detail', fontsize=9, color='white', pad=3)
    
    # Style zoom box
    for spine in axins.spines.values():
        spine.set_color('#555')
        spine.set_linewidth(0.5)
    
    # Legend - reverse order for 2020 at top
    handles, labels = ax.get_legend_handles_labels()
    legend = ax.legend(handles[::-1], labels[::-1],
                      loc='center right',
                      title='Year',
                      title_fontsize=11,
                      fontsize=10,
                      frameon=True,
                      facecolor='#2a2a2a',
                      edgecolor='#555',
                      labelcolor='white')
    legend.get_title().set_color('white')
    
    # Spines
    for spine in ax.spines.values():
        spine.set_color('#555')
        spine.set_linewidth(1)
    
    # Add note about data source
    ax.text(0.02, 0.02,
            'Counting individual job openings (not just postings) based on Date_Active field',
            transform=ax.transAxes,
            fontsize=8,
            color='#888',
            va='bottom')
    
    plt.tight_layout()
    plt.savefig('joe_openings_plot.png',
                dpi=150,
                facecolor='#1a1a1a',
                edgecolor='none')
    
    print("\n✅ Saved visualization as 'joe_openings_plot.png'")

def main():
    """Main processing pipeline."""
    
    # Load XLS files
    df = process_xls_files()
    
    # Analyze date fields
    df = analyze_date_fields(df)
    
    if df is None:
        print("ERROR: Could not process date fields")
        return
    
    # Filter for US Academic
    df = filter_us_academic(df)
    
    # Create weekly cumulative data
    weekly_data = create_weekly_cumulative(df)
    
    # Create visualization
    create_aea_visualization(weekly_data)
    
    print("\n" + "=" * 70)
    print("Processing complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()