"""
Web application for visualizing JOE (Job Openings for Economists) data.
Provides interactive visualizations and data exploration tools.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import io
import base64

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
        background-color: #1a1a1a;
    }
    .metric-card {
        background-color: #2a2a2a;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #555;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #FFD700;
    }
    .metric-label {
        font-size: 0.9em;
        color: #888;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)


class JOEWebApp:
    """Web application for JOE data visualization."""
    
    def __init__(self):
        """Initialize the web app."""
        self.data_dir = Path("joe_data")
        self.combined_data_path = self.data_dir / "combined_listings.csv"
        self.metadata_path = self.data_dir / "metadata.json"
        self.plot_path = Path("joe_openings_plot.png")
        
        # Color scheme matching original plot
        self.colors = {
            2019: '#4A90E2',  # Blue
            2020: '#E94B3C',  # Red - COVID year
            2021: '#2ECC71',  # Green
            2022: '#9B59B6',  # Purple
            2023: '#F39C12',  # Orange
            2024: '#1ABC9C',  # Teal
            2025: '#FFD700',  # Gold
        }
        
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def load_data(_self) -> pd.DataFrame:
        """Load and cache the combined data."""
        if _self.combined_data_path.exists():
            df = pd.read_csv(_self.combined_data_path, parse_dates=['Date_Active', 'download_date'])
            
            # Add calculated fields
            df['iso_year'] = pd.to_datetime(df['Date_Active']).dt.isocalendar().year
            df['iso_week'] = pd.to_datetime(df['Date_Active']).dt.isocalendar().week
            df['academic_year'] = df['Date_Active'].apply(
                lambda x: x.year if x.month >= 8 else x.year - 1
            )
            
            return df
        return pd.DataFrame()
    
    @st.cache_data(ttl=3600)
    def load_metadata(_self) -> dict:
        """Load metadata about updates."""
        if _self.metadata_path.exists():
            with open(_self.metadata_path, 'r') as f:
                return json.load(f)
        return {
            'last_update': None,
            'total_listings': 0,
            'update_history': []
        }
    
    def create_interactive_plot(self, df: pd.DataFrame, section_filter: str = None) -> go.Figure:
        """
        Create an interactive Plotly version of the JOE openings plot.
        
        Args:
            df: DataFrame with job listings
            section_filter: Optional section filter
            
        Returns:
            Plotly figure
        """
        # Filter data if needed
        if section_filter and section_filter != "All Sections":
            df = df[df['jp_section'].str.contains(section_filter, na=False, case=False)]
        
        # Calculate weekly cumulative by academic year
        fig = go.Figure()
        
        # Store max value for y-axis scaling
        max_value = 0
        
        for ac_year in sorted(df['academic_year'].unique(), reverse=True):
            if ac_year < 2019:  # Skip very old data
                continue
                
            year_data = df[df['academic_year'] == ac_year]
            
            # Count openings by ISO week
            week_openings = year_data.groupby('iso_week')['position_count'].sum()
            
            # Create cumulative from week 30 onwards
            weeks = list(range(30, 58))
            cumulative = []
            total_so_far = 0
            
            for week in weeks:
                if week in week_openings.index:
                    total_so_far += week_openings[week]
                cumulative.append(total_so_far)
            
            max_value = max(max_value, max(cumulative) if cumulative else 0)
            
            # For 2025 (partial), only show available data
            if ac_year == 2025:
                # Find last week with data
                last_week_with_data = year_data['iso_week'].max()
                if pd.notna(last_week_with_data):
                    cutoff_idx = min(int(last_week_with_data) - 30 + 1, len(weeks))
                    weeks = weeks[:cutoff_idx]
                    cumulative = cumulative[:cutoff_idx]
                label = f'{ac_year} (partial)'
            else:
                label = str(ac_year)
            
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
                'text': 'JOE Openings by Week (Pre-ASSA Listings, Aug-Dec)<br>' +
                       '<sub>Section 1: US: Full-Time Academic (Permanent, Tenure Track or Tenured)</sub>',
                'x': 0.5,
                'xanchor': 'center'
            },
            xaxis_title='Week of Year (ISO)',
            yaxis_title='Number of Openings (Cumulative)',
            plot_bgcolor='#1a1a1a',
            paper_bgcolor='#1a1a1a',
            font=dict(color='white'),
            xaxis=dict(
                gridcolor='#404040',
                range=[29, 58],
                dtick=5
            ),
            yaxis=dict(
                gridcolor='#404040',
                range=[0, max_value * 1.1]
            ),
            legend=dict(
                bgcolor='#2a2a2a',
                bordercolor='#555',
                borderwidth=1
            ),
            hovermode='x unified',
            height=600
        )
        
        return fig
    
    def create_comparison_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a year-over-year comparison chart."""
        current_year = datetime.now().year
        current_week = datetime.now().isocalendar()[1]
        
        # Filter for current week across years
        comparison_data = []
        
        for ac_year in range(2019, current_year + 1):
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
                    textposition='outside'
                )
            ])
            
            fig.update_layout(
                title=f'Total Openings by Week {current_week}',
                xaxis_title='Academic Year',
                yaxis_title='Total Openings',
                plot_bgcolor='#1a1a1a',
                paper_bgcolor='#1a1a1a',
                font=dict(color='white'),
                xaxis=dict(gridcolor='#404040'),
                yaxis=dict(gridcolor='#404040'),
                showlegend=False,
                height=400
            )
            
            return fig
        
        return None
    
    def create_institution_rankings(self, df: pd.DataFrame, year: int = None) -> pd.DataFrame:
        """Create institution rankings by number of openings."""
        if year:
            df = df[df['academic_year'] == year]
        
        # Group by institution
        inst_df = df.groupby('jp_institution').agg({
            'position_count': 'sum',
            'jp_title': 'count'
        }).reset_index()
        
        inst_df.columns = ['Institution', 'Total Openings', 'Number of Postings']
        inst_df = inst_df.sort_values('Total Openings', ascending=False).head(20)
        
        return inst_df
    
    def render_sidebar(self) -> dict:
        """Render the sidebar with filters and options."""
        st.sidebar.title("🎓 JOE Market Tracker")
        st.sidebar.markdown("---")
        
        # Load metadata
        metadata = self.load_metadata()
        
        # Display last update
        if metadata['last_update']:
            last_update = datetime.fromisoformat(metadata['last_update'])
            st.sidebar.info(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M')}")
        
        # Filters
        st.sidebar.subheader("Filters")
        
        # Section filter
        section_filter = st.sidebar.selectbox(
            "Section",
            ["All Sections", "US: Full-Time Academic", "International Academic", 
             "Public Sector", "Private Sector"]
        )
        
        # Year filter
        current_year = datetime.now().year
        year_filter = st.sidebar.selectbox(
            "Academic Year",
            ["All Years"] + list(range(current_year, 2018, -1))
        )
        
        # View options
        st.sidebar.subheader("View Options")
        show_static = st.sidebar.checkbox("Show Original Static Plot", value=False)
        show_rankings = st.sidebar.checkbox("Show Institution Rankings", value=True)
        show_stats = st.sidebar.checkbox("Show Statistics", value=True)
        
        return {
            'section_filter': section_filter,
            'year_filter': year_filter,
            'show_static': show_static,
            'show_rankings': show_rankings,
            'show_stats': show_stats
        }
    
    def render_main_content(self, df: pd.DataFrame, filters: dict):
        """Render the main content area."""
        st.title("JOE Market Tracker")
        st.markdown("Track job openings for economists from AEA JOE listings")
        
        # Apply year filter if needed
        if filters['year_filter'] != "All Years":
            df = df[df['academic_year'] == int(filters['year_filter'])]
        
        # Display metrics
        if filters['show_stats']:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_openings = df['position_count'].sum()
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{total_openings:,}</div>
                        <div class="metric-label">Total Openings</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                total_postings = len(df)
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{total_postings:,}</div>
                        <div class="metric-label">Total Postings</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col3:
                avg_per_posting = total_openings / total_postings if total_postings > 0 else 0
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{avg_per_posting:.2f}</div>
                        <div class="metric-label">Avg Openings/Posting</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col4:
                unique_institutions = df['jp_institution'].nunique()
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{unique_institutions:,}</div>
                        <div class="metric-label">Institutions Hiring</div>
                    </div>
                """, unsafe_allow_html=True)
        
        # Main visualization
        st.subheader("Weekly Cumulative Openings")
        
        if filters['show_static'] and self.plot_path.exists():
            # Show static plot
            with open(self.plot_path, 'rb') as f:
                st.image(f.read(), use_column_width=True)
        else:
            # Show interactive plot
            fig = self.create_interactive_plot(df, filters['section_filter'])
            st.plotly_chart(fig, use_container_width=True)
        
        # Year comparison
        st.subheader("Year-over-Year Comparison")
        comp_fig = self.create_comparison_chart(df)
        if comp_fig:
            st.plotly_chart(comp_fig, use_container_width=True)
        
        # Institution rankings
        if filters['show_rankings']:
            st.subheader("Top Hiring Institutions")
            
            year_for_ranking = None
            if filters['year_filter'] != "All Years":
                year_for_ranking = int(filters['year_filter'])
            
            rankings_df = self.create_institution_rankings(df, year_for_ranking)
            
            if len(rankings_df) > 0:
                # Create bar chart
                fig = px.bar(
                    rankings_df.head(10),
                    x='Total Openings',
                    y='Institution',
                    orientation='h',
                    color='Total Openings',
                    color_continuous_scale='YlOrRd',
                    title='Top 10 Institutions by Number of Openings'
                )
                
                fig.update_layout(
                    plot_bgcolor='#1a1a1a',
                    paper_bgcolor='#1a1a1a',
                    font=dict(color='white'),
                    xaxis=dict(gridcolor='#404040'),
                    yaxis=dict(gridcolor='#404040'),
                    showlegend=False,
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show full table
                with st.expander("View Full Rankings Table"):
                    st.dataframe(rankings_df, use_container_width=True)
    
    def render_data_tab(self, df: pd.DataFrame):
        """Render the data exploration tab."""
        st.header("Data Explorer")
        
        # Search and filter
        col1, col2 = st.columns(2)
        
        with col1:
            search_term = st.text_input("Search institutions or titles:", "")
        
        with col2:
            min_openings = st.number_input("Minimum openings:", min_value=1, value=1)
        
        # Apply filters
        filtered_df = df.copy()
        
        if search_term:
            mask = (
                filtered_df['jp_institution'].str.contains(search_term, case=False, na=False) |
                filtered_df['jp_title'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        filtered_df = filtered_df[filtered_df['position_count'] >= min_openings]
        
        # Display results
        st.info(f"Showing {len(filtered_df)} listings")
        
        # Show data table
        display_columns = ['Date_Active', 'jp_institution', 'jp_title', 
                          'jp_section', 'position_count']
        
        display_df = filtered_df[display_columns].sort_values('Date_Active', ascending=False)
        display_df.columns = ['Date', 'Institution', 'Title', 'Section', 'Openings']
        
        st.dataframe(display_df, use_container_width=True, height=600)
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name=f"joe_listings_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    def run(self):
        """Run the web application."""
        # Load data
        df = self.load_data()
        
        if len(df) == 0:
            st.error("No data available. Please run the data updater first.")
            st.stop()
        
        # Render sidebar
        filters = self.render_sidebar()
        
        # Create tabs
        tab1, tab2, tab3 = st.tabs(["📊 Visualizations", "🔍 Data Explorer", "ℹ️ About"])
        
        with tab1:
            self.render_main_content(df, filters)
        
        with tab2:
            self.render_data_tab(df)
        
        with tab3:
            st.header("About JOE Market Tracker")
            st.markdown("""
            ### Overview
            This application tracks job openings for economists from the American Economic Association's 
            JOE (Job Openings for Economists) website. The data is updated daily through automated web scraping.
            
            ### Methodology
            - **Data Source**: AEA JOE listings (www.aeaweb.org/joe)
            - **Update Frequency**: Daily at 2:00 AM EST
            - **Position Counting**: Multi-position postings are identified and counted appropriately
            - **Academic Year**: Defined as August to July for consistency with hiring cycles
            
            ### Key Features
            - Real-time tracking of job market trends
            - Year-over-year comparisons
            - Institution rankings by hiring activity
            - Interactive data exploration tools
            
            ### Technical Details
            - Built with Python, Streamlit, and Plotly
            - Automated data collection using Selenium
            - Data processing follows AEA methodology for consistency
            
            ### Contact
            For questions or issues, please contact the administrator.
            """)


def main():
    """Main function to run the Streamlit app."""
    app = JOEWebApp()
    app.run()


if __name__ == "__main__":
    main()