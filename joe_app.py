#!/usr/bin/env python3
"""
JOE Market Tracker - Interactive Web Application
Tracks job openings for economists with automatic daily updates.
"""

import os
import json
import time
from datetime import datetime, timedelta, date
from pathlib import Path
import threading
import schedule

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Set page config
st.set_page_config(
    page_title="JOE Market Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme matching the original plot
st.markdown("""
    <style>
    .stApp {
        background-color: #f0f0f0;
    }
    h1 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #2c3e50;
    }
    .metric-label {
        font-size: 0.9em;
        color: #7f8c8d;
        margin-top: 5px;
    }
    .update-status {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)


class JOETracker:
    """Main application class for JOE tracking."""
    
    def __init__(self):
        """Initialize the tracker."""
        self.data_dir = Path("joe_data/scraped")
        self.metadata_file = self.data_dir / "app_metadata.json"
        
        # Color scheme for years
        self.colors = {
            2019: '#4A90E2',  # Blue
            2020: '#E94B3C',  # Red - COVID year
            2021: '#2ECC71',  # Green
            2022: '#9B59B6',  # Purple
            2023: '#F39C12',  # Orange
            2024: '#1ABC9C',  # Teal
            2025: '#FFD700',  # Gold
            2026: '#FF69B4',  # Hot Pink
        }
        
        # Section definitions
        self.sections = {
            "US: Full-Time Academic": "US: Full-Time Academic (Permanent, Tenure Track or Tenured)",
            "US: Other Academic": "US: Other Academic",
            "International: Full-Time Academic": "International: Full-Time Academic",
            "International: Other Academic": "International: Other Academic",
            "Full-Time Nonacademic": "Full-Time Nonacademic",
            "Other Nonacademic": "Other Nonacademic"
        }
        
        # Initialize auto-updater in background
        if 'auto_updater_started' not in st.session_state:
            st.session_state.auto_updater_started = True
            self.start_auto_updater()
    
    @st.cache_data(ttl=3600)
    def load_data(_self) -> pd.DataFrame:
        """Load and cache all data."""
        all_data = []
        
        if _self.data_dir.exists():
            for xlsx_file in _self.data_dir.glob("*.xlsx"):
                try:
                    df = pd.read_excel(xlsx_file)
                    df['source_file'] = xlsx_file.name
                    all_data.append(df)
                except Exception as e:
                    st.warning(f"Could not load {xlsx_file.name}: {e}")
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Process dates and add calculated fields
            combined_df['Date_Active'] = pd.to_datetime(combined_df['Date_Active'])
            combined_df['iso_year'] = combined_df['Date_Active'].dt.isocalendar().year
            combined_df['iso_week'] = combined_df['Date_Active'].dt.isocalendar().week
            combined_df['academic_year'] = combined_df['Date_Active'].apply(
                lambda x: x.year if x.month >= 8 else x.year - 1
            )
            
            # Extract position counts
            from process_xls_with_openings import extract_position_count
            combined_df['position_count'] = combined_df.apply(extract_position_count, axis=1)
            
            return combined_df
        
        return pd.DataFrame()
    
    def get_last_update(self) -> dict:
        """Get last update information."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {'last_update': None, 'last_scrape': None}
    
    def create_main_plot(self, df: pd.DataFrame, selected_years: list, selected_section: str) -> go.Figure:
        """Create the main cumulative plot."""
        
        # Filter by section
        if selected_section != "All Sections":
            section_filter = self.sections.get(selected_section, selected_section)
            df = df[df['jp_section'].str.contains(section_filter, na=False, case=False)]
        
        # Get current date info
        today = datetime.now()
        current_week = today.isocalendar()[1]
        current_year = today.year
        
        # Create figure with dark theme
        fig = go.Figure()
        
        # Store max value for y-axis
        max_value = 0
        
        # Plot each selected year
        for ac_year in sorted(selected_years, reverse=True):
            year_data = df[df['academic_year'] == ac_year]
            
            if len(year_data) == 0:
                continue
            
            # Count openings by ISO week
            week_openings = year_data.groupby('iso_week')['position_count'].sum()
            
            # Create cumulative from week 30 onwards (roughly August)
            weeks = list(range(30, 54))  # Through December
            cumulative = []
            total_so_far = 0
            
            for week in weeks:
                if week in week_openings.index:
                    total_so_far += week_openings[week]
                cumulative.append(total_so_far)
            
            # For current year, only show completed weeks
            if ac_year == current_year - 1 or (ac_year == current_year and today.month < 8):
                # This is the current academic year
                weeks_to_show = min(current_week - 30 + 1, len(weeks))
                if weeks_to_show > 0:
                    weeks = weeks[:weeks_to_show]
                    cumulative = cumulative[:weeks_to_show]
                    label = f'{ac_year} (current)'
                else:
                    continue  # Skip if no weeks to show
            else:
                label = str(ac_year)
            
            max_value = max(max_value, max(cumulative) if cumulative else 0)
            
            # Add trace
            color = self.colors.get(ac_year, '#888888')
            
            fig.add_trace(go.Scatter(
                x=weeks,
                y=cumulative,
                mode='lines+markers',
                name=label,
                line=dict(color=color, width=2.5),
                marker=dict(size=5),
                hovertemplate='Week %{x}<br>Openings: %{y}<extra></extra>'
            ))
        
        # Update layout to match original style
        fig.update_layout(
            title={
                'text': f'JOE Openings by Week (Pre-ASSA Listings, Aug-Dec)<br>' +
                       f'<sub>{selected_section}</sub>',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'color': 'white'}
            },
            xaxis_title='Week of Year (ISO)',
            yaxis_title='Number of Openings (Cumulative)',
            plot_bgcolor='#1a1a1a',
            paper_bgcolor='#1a1a1a',
            font=dict(color='white'),
            xaxis=dict(
                gridcolor='#404040',
                range=[29, 54],
                dtick=2,
                color='white'
            ),
            yaxis=dict(
                gridcolor='#404040',
                range=[0, max_value * 1.1] if max_value > 0 else [0, 100],
                color='white'
            ),
            legend=dict(
                bgcolor='#2a2a2a',
                bordercolor='#555',
                borderwidth=1,
                font={'color': 'white'}
            ),
            hovermode='x unified',
            height=600
        )
        
        # Add inset for last 6 weeks
        if len(fig.data) > 0:
            # Calculate weeks to show in detail (last 6 weeks from current week)
            detail_end = min(current_week, 53)
            detail_start = max(detail_end - 6, 30)
            
            # Create inset axes
            fig.add_annotation(
                x=0.15,
                y=0.65,
                xref='paper',
                yref='paper',
                text=f'Weeks {detail_start}-{detail_end} Detail',
                showarrow=False,
                font=dict(color='white', size=10),
                bgcolor='#2a2a2a',
                bordercolor='#555',
                borderwidth=1
            )
        
        return fig
    
    def create_comparison_chart(self, df: pd.DataFrame, selected_years: list, selected_section: str) -> go.Figure:
        """Create year-over-year comparison at current week."""
        
        # Filter by section
        if selected_section != "All Sections":
            section_filter = self.sections.get(selected_section, selected_section)
            df = df[df['jp_section'].str.contains(section_filter, na=False, case=False)]
        
        current_week = datetime.now().isocalendar()[1]
        
        comparison_data = []
        for ac_year in selected_years:
            year_df = df[(df['academic_year'] == ac_year) & (df['iso_week'] <= current_week)]
            if len(year_df) > 0:
                total_openings = year_df['position_count'].sum()
                comparison_data.append({
                    'Year': ac_year,
                    'Openings': total_openings,
                    'Color': self.colors.get(ac_year, '#888888')
                })
        
        if comparison_data:
            comp_df = pd.DataFrame(comparison_data)
            
            fig = go.Figure(data=[
                go.Bar(
                    x=comp_df['Year'],
                    y=comp_df['Openings'],
                    marker_color=comp_df['Color'],
                    text=comp_df['Openings'],
                    textposition='outside',
                    textfont=dict(color='white')
                )
            ])
            
            fig.update_layout(
                title=f'Total Openings by Week {current_week}',
                xaxis_title='Academic Year',
                yaxis_title='Total Openings',
                plot_bgcolor='#1a1a1a',
                paper_bgcolor='#1a1a1a',
                font=dict(color='white'),
                xaxis=dict(gridcolor='#404040', color='white'),
                yaxis=dict(gridcolor='#404040', color='white'),
                showlegend=False,
                height=400
            )
            
            return fig
        
        return None
    
    def start_auto_updater(self):
        """Start the auto-updater thread for 5pm daily updates."""
        def run_updater():
            # Schedule daily update at 5pm
            schedule.every().day.at("17:00").do(self.run_daily_update)
            
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        # Start in background thread
        updater_thread = threading.Thread(target=run_updater, daemon=True)
        updater_thread.start()
    
    def run_daily_update(self):
        """Run the daily update at 5pm."""
        try:
            from joe_working_scraper import JOEWorkingScraper
            
            # Download latest 2025 data
            scraper = JOEWorkingScraper(headless=True)
            scraper.setup_driver()
            
            current_year = datetime.now().year
            period = f"August 1, {current_year} - January 31, {current_year + 1}"
            
            # Download US Academic
            scraper.download_data(period, "1")
            
            # Update metadata
            metadata = {
                'last_update': datetime.now().isoformat(),
                'last_scrape': datetime.now().isoformat(),
                'status': 'success'
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f)
            
            # Clear cache to reload data
            st.cache_data.clear()
            
        except Exception as e:
            print(f"Auto-update failed: {e}")
    
    def render_sidebar(self) -> dict:
        """Render sidebar with filters."""
        st.sidebar.title("🎓 JOE Market Tracker")
        st.sidebar.markdown("---")
        
        # Last update info
        metadata = self.get_last_update()
        if metadata.get('last_update'):
            last_update = datetime.fromisoformat(metadata['last_update'])
            st.sidebar.success(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M')}")
        
        # Auto-update status
        st.sidebar.info("📅 Auto-updates daily at 5:00 PM")
        
        st.sidebar.markdown("---")
        
        # Year selection
        st.sidebar.subheader("Select Years")
        available_years = list(range(2019, datetime.now().year + 1))
        
        # Default to last 3 years
        default_years = available_years[-3:] if len(available_years) >= 3 else available_years
        
        selected_years = st.sidebar.multiselect(
            "Years to display:",
            available_years,
            default=default_years
        )
        
        # Section selection
        st.sidebar.subheader("Select Section")
        sections = ["All Sections"] + list(self.sections.keys())
        selected_section = st.sidebar.selectbox(
            "Section type:",
            sections,
            index=1  # Default to US: Full-Time Academic
        )
        
        # Manual update button
        if st.sidebar.button("🔄 Update Now"):
            with st.spinner("Updating data..."):
                self.run_daily_update()
                st.success("Update complete!")
                st.rerun()
        
        return {
            'years': selected_years,
            'section': selected_section
        }
    
    def run(self):
        """Run the main application."""
        st.title("📊 JOE Market Tracker")
        st.markdown("Track job openings for economists from AEA JOE listings")
        
        # Load data
        df = self.load_data()
        
        if len(df) == 0:
            st.error("No data available. Please check the data directory.")
            return
        
        # Get filters from sidebar
        filters = self.render_sidebar()
        
        if not filters['years']:
            st.warning("Please select at least one year to display.")
            return
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Filter data for metrics
        metric_df = df[df['academic_year'].isin(filters['years'])]
        if filters['section'] != "All Sections":
            section_filter = self.sections.get(filters['section'], filters['section'])
            metric_df = metric_df[metric_df['jp_section'].str.contains(section_filter, na=False, case=False)]
        
        with col1:
            total_openings = metric_df['position_count'].sum()
            st.metric("Total Openings", f"{total_openings:,}")
        
        with col2:
            total_postings = len(metric_df)
            st.metric("Total Postings", f"{total_postings:,}")
        
        with col3:
            if total_postings > 0:
                avg_per_posting = total_openings / total_postings
                st.metric("Avg Openings/Posting", f"{avg_per_posting:.2f}")
            else:
                st.metric("Avg Openings/Posting", "N/A")
        
        with col4:
            unique_institutions = metric_df['jp_institution'].nunique()
            st.metric("Institutions Hiring", f"{unique_institutions:,}")
        
        # Main visualization
        st.subheader("Weekly Cumulative Openings")
        main_fig = self.create_main_plot(df, filters['years'], filters['section'])
        st.plotly_chart(main_fig, use_container_width=True)
        
        # Comparison chart
        if len(filters['years']) > 1:
            st.subheader("Year-over-Year Comparison")
            comp_fig = self.create_comparison_chart(df, filters['years'], filters['section'])
            if comp_fig:
                st.plotly_chart(comp_fig, use_container_width=True)
        
        # Data table
        with st.expander("📋 View Raw Data"):
            display_df = metric_df[['Date_Active', 'jp_institution', 'jp_title', 'jp_section', 'position_count']]
            display_df = display_df.sort_values('Date_Active', ascending=False)
            st.dataframe(display_df.head(100))
        
        # Download button
        st.markdown("---")
        csv = metric_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"joe_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


def main():
    """Main entry point."""
    app = JOETracker()
    app.run()


if __name__ == "__main__":
    main()