#!/usr/bin/env python3
"""
Generate building reports for specific BBLs only
Used by nyc-deploy script
"""

import sys
import os

# Add the Scripts directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Get BBLs from command line
if len(sys.argv) < 2:
    print("Usage: generate_specific_buildings.py BBL1,BBL2,BBL3 [commit_message]")
    sys.exit(1)

# Parse BBLs
bbls_str = sys.argv[1]
specific_bbls = [int(bbl.strip()) for bbl in bbls_str.split(',')]

# Get optional commit message
commit_message = sys.argv[2] if len(sys.argv) > 2 else None

print(f"Generating reports for {len(specific_bbls)} buildings: {specific_bbls}")

# Import all the necessary modules and data
import pandas as pd
from datetime import datetime, timedelta
import pytz
import requests
import urllib.parse
from dotenv import load_dotenv
import json
import re
import time

# Load environment variables from .env file
load_dotenv()

# Server key for report generation (air quality API) - unrestricted
SERVER_API_KEY = "AIzaSyCZU0mRkd5VlOXgsLFyH_tzWT3nT6MUZlI"
# OpenWeatherMap API key for air pollution data (30 days historical)
OPENWEATHER_API_KEY = "9e666d3512bac2a16c6b9c3c029dcef6"

# AWS S3 bucket URL for aerial videos
AWS_VIDEO_BUCKET = "https://aerial-videos-forrest.s3.us-east-2.amazonaws.com"

# Version tracking for cache busting
version = int(datetime.now().timestamp())

# Import the helper functions from building.py
from building import find_logo_file, safe_val

# Read ALL the CSVs we need
scoring = pd.read_csv('../data/odcv_scoring.csv')
buildings = pd.read_csv('../data/buildings_BIG.csv')
ll97 = pd.read_csv('../data/LL97_BIG.csv')
system = pd.read_csv('../data/system_BIG.csv')
energy = pd.read_csv('../data/energy_BIG.csv')
addresses = pd.read_csv('../data/all_building_addresses.csv')
hvac = pd.read_csv('../data/hvac_office_energy_BIG.csv')
office = pd.read_csv('../data/office_energy_BIG.csv')

# Read building heights
heights = pd.read_csv('../data/building_heights.csv')

# Read equipment counts
try:
    equipment_counts = pd.read_csv('../data/equipment_counts.csv')
except:
    equipment_counts = pd.DataFrame()  # Empty dataframe if file not found

# Check which aerial videos exist in S3
aerial_videos_available = set()
try:
    aerial_df = pd.read_csv('../data/aerial_videos.csv')
    for _, row in aerial_df.iterrows():
        if row['status'] == 'active' and pd.notna(row['video_id']):
            aerial_videos_available.add(int(row['bbl']))
except:
    # If no CSV, assume all videos are available
    aerial_videos_available = set(scoring['bbl'].values)

# Read CostarExport data for owner phone information
try:
    costar_df = pd.read_csv('../data/CostarExport_Master_with_BBL_filtered.csv')
except:
    pass  # No CostarExport file

# Read tenant data
try:
    tenants_df = pd.read_csv('../data/Costar_Tenants_2025_07_31_17_56.csv')
    # Clean SF Occupied - remove commas and convert to numeric
    tenants_df['SF_Occupied_Clean'] = tenants_df['SF Occupied'].str.replace(',', '').str.replace('"', '')
    tenants_df['SF_Occupied_Clean'] = pd.to_numeric(tenants_df['SF_Occupied_Clean'], errors='coerce')
except:
    tenants_df = pd.DataFrame()  # Empty dataframe if file not found

# Filter scoring to only include specific BBLs
scoring = scoring[scoring['bbl'].isin(specific_bbls)]

# Now run the rest of the building.py code
# Import the entire building generation logic
with open('building.py', 'r') as f:
    building_code = f.read()
    
# Extract just the main loop part (after line 140)
# Find the start of the main loop
start_marker = "# For each building"
start_pos = building_code.find(start_marker)

if start_pos == -1:
    print("Error: Could not find main loop in building.py")
    sys.exit(1)

# Set sys.argv so building code can see the commit message
if commit_message:
    sys.argv = ['generate_specific_buildings.py', commit_message]
else:
    sys.argv = ['generate_specific_buildings.py']

# Execute the main loop code
exec(building_code[start_pos:])

print(f"✓ Generated {len(specific_bbls)} specific building reports")