# Data Backup Directory

This directory contains backup copies of the full historical data to prevent data loss during GitHub Actions runs.

The file `joe_data_backup.json` should be updated whenever running `generate_static_site.py` locally with all years of data available.

This ensures that GitHub Actions always have access to historical data even if the live website gets corrupted.