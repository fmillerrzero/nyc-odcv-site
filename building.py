import pandas as pd
from datetime import datetime, timedelta
import pytz
import requests
import urllib.parse
import os
from dotenv import load_dotenv
import sys
import json
import re
import time

# Load environment variables from .env file
load_dotenv()

# Server key for report generation (air quality API) - unrestricted
SERVER_API_KEY = "AIzaSyCZU0mRkd5VlOXgsLFyH_tzWT3nT6MUZlI"
# OpenWeatherMap API key for air pollution data (30 days historical)
OPENWEATHER_API_KEY = "9e666d3512bac2a16c6b9c3c029dcef6"

# Client key for aerial videos (domain-restricted to test and main sites)
# CLIENT_API_KEY = "AIzaSyDQdR4xY0a_qmEsYairsp6r6tXwh5qx_ho"

# AWS S3 bucket URL for aerial videos
AWS_VIDEO_BUCKET = "https://aerial-videos-forrest.s3.us-east-2.amazonaws.com"

# Version tracking for cache busting
version = int(datetime.now().timestamp())

# Logo mapping function
def find_logo_file(company_name):
    """Find matching logo file for a company name"""
    if pd.isna(company_name) or not company_name:
        return None
    
    # Clean and convert company name to match logo filename format
    clean_name = company_name.strip()
    clean_name = clean_name.replace("'", "")  # Remove apostrophes
    clean_name = clean_name.replace(" & ", "_")  # Replace " & " with "_"
    clean_name = clean_name.replace(" ", "_")  # Replace spaces with underscores
    logo_filename = f"{clean_name}.png"
    
    # Handle special case for CommonWealth Partners (jpg not png)
    if clean_name == "CommonWealth_Partners":
        logo_filename = "CommonWealth_Partners.jpg"
    
    # List of available logos to verify match exists
    available_logos = [
        "Actors_Equity_Association.png", "Amazon.png", "Blackstone.png", "Bloomberg.png",
        "Brookfield.png", "Brown_Harris_Stevens.png", "CBRE.png", "CBS.png",
        "Century_Link.png", "Chetrit_Group.png", "China_Orient_Asset_Management_Corporation.png",
        "CIM_Group.png", "City_of_New_York.png", "Clarion_Partners.png", "Colliers.png",
        "Columbia_University.png", "CommonWealth_Partners.jpg", "Cooper_Union.png",
        "Cushman_Wakefield.png", "DCAS.png", "Douglas_Elliman.png", "Durst_Organization.png",
        "Empire_State_Realty_Trust.png", "Episcopal_Church.png", "EQ_Office.png",
        "Extell_Development.png", "Feil_Organization.png", "Fisher_Brothers_Management.png",
        "Fosun_International.png", "George_Comfort_Sons.png", "GFP_Real_Estate.png",
        "Goldman_Sachs_Group.png", "Google.png", "Greystone.png", "Harbor_Group_International.png",
        "Hines.png", "JLL.png", "Kaufman_Organization.png", "Kushner_Companies.png",
        "La_Caisse.png", "Lalezarian_Properties.png", "Lee_Associates.png", "Lincoln_Property.png",
        "MetLife.png", "Metropolitan_Transportation_Authority.png", "Mitsui_Fudosan_America.png",
        "Moinian_Group.png", "New_School.png", "Newmark.png", "NYU.png", "Olayan_America.png",
        "Paramount_Group.png", "Piedmont_Realty_Trust.png", "Prudential.png", "RFR_Realty.png",
        "Rockefeller_Group.png", "Rockpoint.png", "Rudin.png", "RXR_Realty.png",
        "Safra_National_Bank.png", "Silverstein_Properties.png", "SL_Green_Realty.png",
        "Tishman_Speyer.png", "Trinity_Church_Wall_Street.png", "Vornado_Realty_Trust.png"
    ]
    
    # Return logo filename if it exists in our list
    if logo_filename in available_logos:
        return logo_filename
    
    return None

# Helper function for safe value extraction
def safe_val(df, bbl, column, default='N/A'):
    if df.empty or column not in df.columns:
        return default
    filtered = df[df['bbl'] == bbl]
    if filtered.empty:
        return default
    val = filtered[column].iloc[0]
    if pd.isna(val):
        return default
    return val

# Read ALL the CSVs we need
scoring = pd.read_csv('data/odcv_scoring.csv')
buildings = pd.read_csv('data/buildings_BIG.csv')
ll97 = pd.read_csv('data/LL97_BIG.csv')
system = pd.read_csv('data/system_BIG.csv')
energy = pd.read_csv('data/energy_BIG.csv')
addresses = pd.read_csv('data/all_building_addresses.csv')
hvac = pd.read_csv('data/hvac_office_energy_BIG.csv')
office = pd.read_csv('data/office_energy_BIG.csv')

# Read building heights
heights = pd.read_csv('data/building_heights.csv')

# Read equipment counts
try:
    equipment_counts = pd.read_csv('data/equipment_counts.csv')
except:
    equipment_counts = pd.DataFrame()  # Empty dataframe if file not found

# Check which aerial videos exist in S3
aerial_videos_available = set()
try:
    aerial_df = pd.read_csv('data/aerial_videos.csv')
    for _, row in aerial_df.iterrows():
        if row['status'] == 'active' and pd.notna(row['video_id']):
            aerial_videos_available.add(int(row['bbl']))
except:
    # If no CSV, assume all videos are available
    aerial_videos_available = set(scoring['bbl'].values)

# Read CostarExport data for owner phone information
try:
    costar_df = pd.read_csv('data/CostarExport_Master_with_BBL_filtered.csv')
except:
    pass  # No CostarExport file

# Read tenant data
try:
    tenants_df = pd.read_csv('data/Costar_Tenants_2025_07_31_17_56.csv')
    # PropertyID extraction removed - using BBL directly
    # Clean SF Occupied - remove commas and convert to numeric
    tenants_df['SF_Occupied_Clean'] = tenants_df['SF Occupied'].str.replace(',', '').str.replace('"', '')
    tenants_df['SF_Occupied_Clean'] = pd.to_numeric(tenants_df['SF_Occupied_Clean'], errors='coerce')
except:
    tenants_df = pd.DataFrame()  # Empty dataframe if file not found

# For each building
for i, row in scoring.iterrows():
    bbl = row['bbl']
    
    try:
            # Validate required columns exist
            required_cols = ['bbl', 'Total_ODCV_Savings_Annual_USD', 'total_score', 'final_rank']
            if not all(col in row.index for col in required_cols):
                print(f"Skipping {bbl} - missing required columns")
                continue
            
            # Get building data
            building = buildings[buildings['bbl'] == bbl]
            if building.empty:
                continue
                
            # Get data from each CSV
            ll97_data = ll97[ll97['bbl'] == bbl]
            system_data = system[system['bbl'] == bbl]
            energy_data = energy[energy['bbl'] == bbl]
            address_data = addresses[addresses['bbl'] == bbl]
            
            # Skip if critical data missing
            if ll97_data.empty or energy_data.empty:
                print(f"Skipping {bbl} - missing critical data")
                continue
                
            # Get building height for panorama
            building_height = safe_val(heights, bbl, 'Height Roof', 200)  # Default 200ft
            
            # Get monthly energy data - SIMPLE VERSION
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            elec_usage = []
            gas_usage = []
            steam_usage = []
            hvac_pct = []
            odcv_savings = []
            
            for m in months:
                # Safely get values with your data
                hvac_monthly = float(safe_val(energy_data, bbl, f'Elec_HVAC_{m}_2023_kBtu', 0))
                non_hvac = float(safe_val(energy_data, bbl, f'Elec_NonHVAC_{m}_2023_kBtu', 0))
                gas = float(safe_val(energy_data, bbl, f'Gas_{m}_2023_kBtu', 0))
                steam = float(safe_val(energy_data, bbl, f'Steam_{m}_2023_kBtu', 0))
                total = hvac_monthly + non_hvac
                
                elec_usage.append(hvac_monthly)
                gas_usage.append(gas)
                steam_usage.append(steam)
                hvac_pct.append(hvac_monthly/total if total > 0 else 0)
            
            # Calculate annual average HVAC percentage
            annual_avg_hvac_pct = sum(hvac_pct) / len(hvac_pct) if hvac_pct else 0
            
            # Get ODCV savings data from hvac CSV
            hvac_data = hvac[hvac['bbl'] == bbl]
            odcv_elec_savings = []
            odcv_gas_savings = []
            odcv_steam_savings = []
            for m in months:
                val = hvac_data[f'Office_Elec_Savings_ODCV_{m}_USD'].iloc[0] if not hvac_data.empty else 0
                odcv_elec_savings.append(float(val) if pd.notna(val) else 0)
                val = hvac_data[f'Office_Gas_Savings_ODCV_{m}_USD'].iloc[0] if not hvac_data.empty else 0
                odcv_gas_savings.append(float(val) if pd.notna(val) else 0)
                val = hvac_data[f'Office_Steam_Savings_ODCV_{m}_USD'].iloc[0] if not hvac_data.empty else 0
                odcv_steam_savings.append(float(val) if pd.notna(val) else 0)
            
            # Calculate total ODCV savings per month using REAL data
            odcv_savings = []
            for i in range(12):
                monthly_total = odcv_elec_savings[i] + odcv_gas_savings[i] + odcv_steam_savings[i]
                odcv_savings.append(monthly_total)
            
            # Office energy data
            office_data = office[office['bbl'] == bbl]
            office_elec_usage = []
            office_gas_usage = []
            office_steam_usage = []
            for m in months:
                val = office_data[f'Office_Elec_Usage_Current_{m}_kBtu'].iloc[0] if not office_data.empty else 0
                office_elec_usage.append(float(val) if pd.notna(val) else 0)
                val = office_data[f'Office_Gas_Usage_Current_{m}_kBtu'].iloc[0] if not office_data.empty else 0
                office_gas_usage.append(float(val) if pd.notna(val) else 0)
                val = office_data[f'Office_Steam_Usage_Current_{m}_kBtu'].iloc[0] if not office_data.empty else 0
                office_steam_usage.append(float(val) if pd.notna(val) else 0)
            
            # Energy costs
            elec_cost = []
            gas_cost = []
            steam_cost = []
            for m in months:
                elec_cost.append(float(energy_data[f'Elec_HVAC_{m}_2023_Cost_USD'].iloc[0]) + float(energy_data[f'Elec_NonHVAC_{m}_2023_Cost_USD'].iloc[0]) if not energy_data.empty else 0)
                gas_cost.append(float(energy_data[f'Gas_{m}_2023_Cost_USD'].iloc[0]) if not energy_data.empty else 0)
                steam_cost.append(float(energy_data[f'Steam_{m}_2023_Cost_USD'].iloc[0]) if not energy_data.empty else 0)
            
            # Office costs
            office_elec_cost = []
            office_gas_cost = []
            office_steam_cost = []
            for m in months:
                val = office_data[f'Office_Elec_Cost_Current_{m}_USD'].iloc[0] if not office_data.empty else 0
                office_elec_cost.append(float(val) if pd.notna(val) else 0)
                val = office_data[f'Office_Gas_Cost_Current_{m}_USD'].iloc[0] if not office_data.empty else 0
                office_gas_cost.append(float(val) if pd.notna(val) else 0)
                val = office_data[f'Office_Steam_Cost_Current_{m}_USD'].iloc[0] if not office_data.empty else 0
                office_steam_cost.append(float(val) if pd.notna(val) else 0)
            
            # Calculate annual cost totals
            annual_building_cost = sum(elec_cost) + sum(gas_cost) + sum(steam_cost)
            annual_office_cost = sum(office_elec_cost) + sum(office_gas_cost) + sum(office_steam_cost)
            
            # Extract values (default to 'N/A' if missing) - SIMPLE VERSION
            owner = building['ownername'].iloc[0] if not building.empty else 'N/A'
            floors = int(building['numfloors'].iloc[0]) if not building.empty and pd.notna(building['numfloors'].iloc[0]) else 'N/A'
            year_built = building['yearalter'].iloc[0] if not building.empty else 'N/A'
            building_class = safe_val(building, bbl, 'Class', 'N/A')
            
            # Commercial info
            property_manager = safe_val(building, bbl, 'property_manager', 'Unknown')
            pct_leased = int(float(safe_val(building, bbl, '% Leased', 0)))
            
            # Format landlord contact - handle multiple phone numbers from different sources
            landlord_contact_raw = safe_val(building, bbl, 'LandlordContact', 'Unavailable')
            
            # Get owner phone and name from CostarExport if available
            costar_owner_phone = None
            costar_owner_name = None
            if 'costar_df' in globals():
                costar_data = costar_df[costar_df['BBL'].astype(str).str.replace('.0', '', regex=False) == str(bbl)]
                if not costar_data.empty:
                    owner_phone = costar_data['Owner Phone'].iloc[0]
                    owner_name = costar_data.get('Owner Contact', pd.Series()).iloc[0] if 'Owner Contact' in costar_data.columns else None
                    
                    if pd.notna(owner_phone) and owner_phone:
                        # Format phone if numeric
                        if str(owner_phone).replace('.', '').isdigit():
                            phone = str(int(float(owner_phone)))
                            if len(phone) == 10:
                                costar_owner_phone = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                            else:
                                costar_owner_phone = str(owner_phone)
                        else:
                            costar_owner_phone = str(owner_phone)
                    
                    if pd.notna(owner_name) and owner_name:
                        costar_owner_name = str(owner_name).strip()
            
            if landlord_contact_raw != 'Unavailable' and landlord_contact_raw != 'N/A':
                # Remove (p) and (e) indicators
                landlord_contact_clean = landlord_contact_raw.replace(' (p)', '').replace(' (e)', '')
                
                # Patterns for phone and email
                phone_pattern = r'(\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4}|\d{10})'
                email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                
                # Find all phones and emails in landlord contact
                phone_matches = list(re.finditer(phone_pattern, landlord_contact_clean))
                email_matches = list(re.finditer(email_pattern, landlord_contact_clean))
                
                # Extract existing phone from landlord contact
                existing_phone = None
                if phone_matches:
                    existing_phone = phone_matches[0].group()
                
                # Check if we need to show both phones
                if costar_owner_phone and existing_phone and costar_owner_phone != existing_phone:
                    # Two different phone numbers - show both with labels
                    if phone_matches or email_matches:
                        # Find the earliest match position
                        first_contact_pos = float('inf')
                        if phone_matches:
                            first_contact_pos = min(first_contact_pos, phone_matches[0].start())
                        if email_matches:
                            first_contact_pos = min(first_contact_pos, email_matches[0].start())
                        
                        # Extract name (everything before first contact info)
                        if first_contact_pos > 0 and first_contact_pos != float('inf'):
                            name_part = landlord_contact_clean[:first_contact_pos].strip()
                            
                            # Build contact with both phones - use names if available
                            landlord_label = name_part if name_part else "landlord"
                            owner_label = costar_owner_name if costar_owner_name else "owner"
                            
                            if name_part:
                                # If there's a main name, use it at the beginning
                                if costar_owner_name and costar_owner_name != name_part:
                                    landlord_contact = f"{name_part} • {existing_phone} or {costar_owner_name} • {costar_owner_phone}"
                                else:
                                    landlord_contact = f"{name_part} • {existing_phone} or {costar_owner_phone}"
                            else:
                                # No main name, show both contacts
                                if costar_owner_name:
                                    landlord_contact = f"{existing_phone} or {costar_owner_name} • {costar_owner_phone}"
                                else:
                                    landlord_contact = f"{existing_phone} or {costar_owner_phone}"
                        else:
                            # Extract landlord name from the clean contact if possible
                            landlord_name = None
                            if not landlord_contact_clean.startswith('('):
                                # There might be a name before the phone
                                parts = landlord_contact_clean.split(' ')
                                if len(parts) > 1:
                                    landlord_name = ' '.join(parts[:-1]).strip()
                            
                            if landlord_name and costar_owner_name and landlord_name != costar_owner_name:
                                landlord_contact = f"{landlord_name} • {existing_phone} or {costar_owner_name} • {costar_owner_phone}"
                            elif landlord_name:
                                landlord_contact = f"{landlord_name} • {existing_phone} or {costar_owner_phone}"
                            elif costar_owner_name:
                                landlord_contact = f"{existing_phone} or {costar_owner_name} • {costar_owner_phone}"
                            else:
                                landlord_contact = f"{existing_phone} or {costar_owner_phone}"
                    else:
                        if costar_owner_name:
                            landlord_contact = f"{landlord_contact_clean} or {costar_owner_name} • {costar_owner_phone}"
                        else:
                            landlord_contact = f"{landlord_contact_clean} or {costar_owner_phone}"
                else:
                    # Only one phone number or they're the same - format normally without labels
                    if phone_matches or email_matches:
                        # Find the earliest match position
                        first_contact_pos = float('inf')
                        if phone_matches:
                            first_contact_pos = min(first_contact_pos, phone_matches[0].start())
                        if email_matches:
                            first_contact_pos = min(first_contact_pos, email_matches[0].start())
                        
                        # Extract name (everything before first contact info)
                        if first_contact_pos > 0 and first_contact_pos != float('inf'):
                            name_part = landlord_contact_clean[:first_contact_pos].strip()
                            contact_part = landlord_contact_clean[first_contact_pos:].strip()
                            
                            if name_part:
                                landlord_contact = f"{name_part} • {contact_part}"
                            else:
                                landlord_contact = landlord_contact_clean
                        else:
                            landlord_contact = landlord_contact_clean
                    else:
                        landlord_contact = landlord_contact_clean
            elif costar_owner_phone:
                # No landlord contact but we have owner phone from CostarExport
                landlord_contact = costar_owner_phone
            else:
                landlord_contact = landlord_contact_raw
            
            # Format property manager contact - same format as owner contact
            property_manager_contact_raw = safe_val(building, bbl, 'PropertyManagerContact', 'Unavailable')
            if property_manager_contact_raw != 'Unavailable' and property_manager_contact_raw != 'N/A':
                # Remove (p) and (e) indicators
                pm_contact_clean = property_manager_contact_raw.replace(' (p)', '').replace(' (e)', '')
                
                # Patterns for phone and email
                phone_pattern = r'(\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4}|\d{10})'
                email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                
                # Find all phones and emails
                phone_matches = list(re.finditer(phone_pattern, pm_contact_clean))
                email_matches = list(re.finditer(email_pattern, pm_contact_clean))
                
                if phone_matches or email_matches:
                    # Find the earliest match position
                    first_contact_pos = float('inf')
                    if phone_matches:
                        first_contact_pos = min(first_contact_pos, phone_matches[0].start())
                    if email_matches:
                        first_contact_pos = min(first_contact_pos, email_matches[0].start())
                    
                    # Extract name (everything before first contact info)
                    if first_contact_pos > 0 and first_contact_pos != float('inf'):
                        name_part = pm_contact_clean[:first_contact_pos].strip()
                        contact_part = pm_contact_clean[first_contact_pos:].strip()
                        
                        if name_part:
                            property_manager_contact = f"{name_part} • {contact_part}"
                        else:
                            property_manager_contact = pm_contact_clean
                    else:
                        property_manager_contact = pm_contact_clean
                else:
                    property_manager_contact = pm_contact_clean
            else:
                property_manager_contact = property_manager_contact_raw
            
            # Logo mapping using the same function as homepage
            logo_file = find_logo_file(owner)
            if logo_file:
                owner_logo = f' <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/Logos/{logo_file}" style="height:30px;margin-left:10px;vertical-align:middle;">'
            else:
                owner_logo = ""
            
            # Manager logo
            manager_logo_file = find_logo_file(property_manager)
            if manager_logo_file:
                manager_logo = f' <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/Logos/{manager_logo_file}" style="height:30px;margin-left:10px;vertical-align:middle;">'
            else:
                manager_logo = ""
            
            # Get detailed BAS info
            has_bas = safe_val(system_data, bbl, 'Has Building Automation', 'N/A')
            heating_automation = safe_val(system_data, bbl, 'Heating Automation', 'N/A')
            cooling_automation = safe_val(system_data, bbl, 'Cooling Automation', 'N/A')
            energy_star = building['Latest_ENERGY_STAR_Score'].iloc[0] if not building.empty else 'N/A'
            
            # System info
            heating_type = system_data['Heating System Type'].iloc[0] if not system_data.empty and 'Heating System Type' in system_data.columns else 'N/A'
            cooling_type = system_data['Cooling System Type'].iloc[0] if not system_data.empty and 'Cooling System Type' in system_data.columns else 'N/A'
            
            # Property details
            num_floors = int(building['numfloors'].iloc[0]) if not building.empty and pd.notna(building['numfloors'].iloc[0]) else 'N/A'
            year_built_real = building['yearalter'].iloc[0] if not building.empty else 'N/A'
            total_area = building['total_gross_floor_area'].iloc[0] if not building.empty else 0
            office_sqft = int(float(safe_val(building, bbl, 'office_sqft', 0)))
            office_pct = int(float(safe_val(hvac_data, bbl, 'office_pct_of_building', 0)) * 100)
            year_altered = safe_val(building, bbl, 'yearalter', 'N/A')
            total_units = int(safe_val(building, bbl, 'unitstotal', 0))
            num_elevators = int(safe_val(building, bbl, 'Number Of Elevators', 0))
            opex_per_sqft = safe_val(building, bbl, '2024 Building OpEx/SF', 'N/A')
            typical_floor_sqft = safe_val(building, bbl, 'Typical Floor Sq Ft', 'N/A')
            # Format as comma-separated number if it's numeric
            if typical_floor_sqft != 'N/A':
                try:
                    typical_floor_sqft = f"{int(float(typical_floor_sqft)):,}"
                except:
                    pass
            
            penalty_2026 = ll97_data['penalty_2026_dollars'].iloc[0] if not ll97_data.empty else 0
            penalty_2030 = ll97_data['penalty_2030_dollars'].iloc[0] if not ll97_data.empty else 0
            
            # Carbon emissions
            carbon_limit_2024 = float(safe_val(ll97_data, bbl, 'carbon_limit_2024_tCO2e', 0))
            carbon_limit_2030 = float(safe_val(ll97_data, bbl, 'carbon_limit_2030_tCO2e', 0))
            total_carbon_emissions = float(safe_val(ll97_data, bbl, 'total_carbon_emissions_tCO2e', 0))
            
            # Get LL33 grade - use REAL data, not fake 'B'
            ll33_grade = safe_val(building, bbl, 'LL33 grade', 'N/A')
            ll33_grade_raw = str(ll33_grade).replace(' ', '').upper() if ll33_grade != 'N/A' else 'NA'
            
            # Get compliance status
            compliance_2024 = 'Yes' if penalty_2026 == 0 else 'No'
            compliance_2030 = 'Yes' if penalty_2030 == 0 else 'No'
            
            # Get green rating (LEED, Energy Star certification)
            green_rating = safe_val(building, bbl, 'GreenRating', '')
            
            # Get address and building name
            main_address = address_data['main_address'].iloc[0] if not address_data.empty else row['address']
            building_name = safe_val(address_data, bbl, 'primary_building_name', '')
            neighborhood = safe_val(building, bbl, 'neighborhood', 'Manhattan')
            
            # Get building coordinates from CSV data or use default
            lat = safe_val(building, bbl, 'latitude', 40.7580)
            lon = safe_val(building, bbl, 'longitude', -73.9855)
            
            # Get tenant data for this building
            building_tenants = pd.DataFrame()  # Default empty
            if not tenants_df.empty:
                # Get tenants for this BBL directly
                building_tenants = tenants_df[tenants_df['BBL'] == bbl].copy()
                if not building_tenants.empty:
                    # Sort by SF Occupied (descending) and get top 10
                    building_tenants = building_tenants.sort_values('SF_Occupied_Clean', ascending=False).head(10)
            
            # Get equipment counts for this building
            cooling_towers = 0
            water_tanks = 0
            if not equipment_counts.empty:
                equipment_data = equipment_counts[equipment_counts['bbl'] == bbl]
                if not equipment_data.empty:
                    cooling_towers = int(equipment_data['cooling_towers'].iloc[0])
                    water_tanks = int(equipment_data['water_tanks'].iloc[0])
            
            # Convert to float if they're strings
            try:
                lat = float(lat) if lat != 'N/A' else 40.7580
                lon = float(lon) if lon != 'N/A' else -73.9855
            except (ValueError, TypeError):
                lat, lon = 40.7580, -73.9855
                print(f"Invalid coordinates for {main_address}, using Manhattan center")

            # Get 30-day PM2.5 with proper error handling - DAILY AVERAGES
            daily_pm25 = {}  # Date -> list of values
            chart_dates = []
            chart_values = []
            try:
                # Calculate timestamps for 30 days ago and now
                end_timestamp = int(time.time())
                start_timestamp = end_timestamp - (30 * 24 * 60 * 60)  # 30 days ago
                
                air_response = requests.get(
                    f"http://api.openweathermap.org/data/2.5/air_pollution/history",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "start": start_timestamp,
                        "end": end_timestamp,
                        "appid": OPENWEATHER_API_KEY
                    }
                )
                
                if air_response.status_code == 200:
                    data = air_response.json()
                    if 'list' in data:
                        print(f"OpenWeatherMap API returned {len(data.get('list', []))} hours of data for BBL {bbl}")
                        
                        for hour_data in data.get('list', []):
                            # Get timestamp and convert to date
                            timestamp = hour_data.get('dt', 0)
                            if timestamp:
                                dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
                                dt_local = dt.astimezone(pytz.timezone('America/New_York'))
                                date_key = dt_local.strftime('%Y-%m-%d')
                                
                                # Get PM2.5 value from components
                                pm25_value = hour_data.get('components', {}).get('pm2_5', 0)
                                
                                # Add to daily collection
                                if date_key not in daily_pm25:
                                    daily_pm25[date_key] = []
                                daily_pm25[date_key].append(pm25_value)
                    else:
                        print(f"OpenWeatherMap API response missing 'list' for BBL {bbl}")
                else:
                    print(f"OpenWeatherMap API error {air_response.status_code} for BBL {bbl}")
                                
            except Exception as e:
                print(f"OpenWeatherMap API error for {bbl}: {e}")
            
            # Calculate daily averages
            for date_key in sorted(daily_pm25.keys()):
                daily_values = daily_pm25[date_key]
                if daily_values:
                    daily_avg = sum(daily_values) / len(daily_values)
                    chart_dates.append(date_key)
                    chart_values.append(daily_avg)
            
            print(f"PM2.5 processed {len(chart_dates)} days of data for BBL {bbl}")
            if len(chart_dates) > 0:
                print(f"Date range: {chart_dates[0]} to {chart_dates[-1]}")
            
            # Calculate overall statistics
            if chart_values:
                avg_pm25 = sum(chart_values) / len(chart_values)
                max_pm25 = max(chart_values)
            else:
                avg_pm25 = 0
                max_pm25 = 0
            
            # EPA AQI categories for PM2.5
            if avg_pm25 <= 12:
                aqi_color = "#00e400"
            elif avg_pm25 <= 35.4:
                aqi_color = "#FFB300"
            elif avg_pm25 <= 55.4:
                aqi_color = "#ff7e00"
            elif avg_pm25 <= 150.4:
                aqi_color = "#ff0000"
            else:
                aqi_color = "#8f3f97"
            
            # Simple calculations
            total_odcv_savings = row['Total_ODCV_Savings_Annual_USD']
            score = row['total_score']
            rank = int(row['final_rank'])
            total_2026_savings = total_odcv_savings + penalty_2026
            
            # Penalty breakdown for header
            if penalty_2026 > 0:
                penalty_breakdown_html = f'''<div style="font-size: 0.75em; opacity: 0.9; margin-top: 8px; line-height: 1.4;">
                    <div>ODCV Savings: ${total_odcv_savings:,.0f}</div>
                    <div>LL97 Penalty Avoidance: ${penalty_2026:,.0f}</div>
                </div>'''
            else:
                penalty_breakdown_html = ''
            
            # Get owner building count for portfolio score
            owner_building_count = buildings[buildings['ownername'] == owner].shape[0] if owner != 'N/A' else 1
            
            # Simple score breakdown
            cost_savings_score = min(40, total_odcv_savings / 25000)  # Max 40 pts
            bas_score = 30 if has_bas == 'yes' else 0  # 30 pts for BAS
            portfolio_score = 20 if owner_building_count > 5 else 10  # 20 pts for big portfolios
            ease_score = 10 if num_floors < 20 else 5  # 10 pts for smaller buildings
            
            # Energy Star calculations
            energy_star_num = float(energy_star) if energy_star != 'N/A' and energy_star else 0
            target_energy_star = 75  # Target score
            if energy_star_num < 50:
                energy_star_color = '#c41e3a'  # Red
            elif energy_star_num < 75:
                energy_star_color = '#ffc107'  # Yellow
            else:
                energy_star_color = '#38a169'  # Green
            
            # Energy Star comparison
            energy_star_delta = ""
            target_score = 75  # Default for display (as integer)
            if energy_star != 'N/A' and not pd.isna(energy_star):
                try:
                    current_score = float(energy_star)
                    target_score = 75  # Default target
                    # Try to get actual target from buildings data
                    target_energy_star_val = safe_val(building, bbl, 'Latest_Target_ENERGY_STAR_Score', 75)
                    if target_energy_star_val != 'N/A':
                        target_score = int(float(target_energy_star_val))
                    
                    delta = target_score - current_score
                    if delta > 0:
                        energy_star_delta = f'<div style="color: #c41e3a;">↑ {delta:.0f} points needed</div>'
                    else:
                        energy_star_delta = f'<div style="color: #38a169;">✓ Exceeds target by {abs(delta):.0f} points</div>'
                except:
                    energy_star_delta = ""
            
            # Create BAS text with details
            if has_bas == 'yes':
                has_heating = heating_automation == 'yes'
                has_cooling = cooling_automation == 'yes'
                
                if has_heating and has_cooling:
                    bas_text = '<span style="color: black; font-weight: normal;">Ventilation</span><span style="color: black;">,</span> <span style="color: #ff6600; font-weight: normal;">Heating</span><span style="color: black;">,</span> <span style="color: #0066cc; font-weight: normal;">Cooling</span> <span style="font-weight: normal;">Controls</span>'
                elif has_heating:
                    bas_text = '<span style="color: black; font-weight: normal;">Ventilation</span><span style="color: black;">,</span> <span style="color: #ff6600; font-weight: normal;">Heating</span> <span style="font-weight: normal;">Controls</span>'
                elif has_cooling:
                    bas_text = '<span style="color: black; font-weight: normal;">Ventilation</span><span style="color: black;">,</span> <span style="color: #0066cc; font-weight: normal;">Cooling</span> <span style="font-weight: normal;">Controls</span>'
                else:
                    bas_text = '<span style="color: black; font-weight: normal;">Ventilation Controls</span>'
                bas_class = 'bas'
            elif has_bas == 'no':
                bas_text = '<span style="color: #c41e3a; font-weight: 600;">⚠️  Absent</span>'
                bas_class = ''
            else:
                bas_text = '<span style="color: #FFB300; font-weight: 600;">Unknown</span>'
                bas_class = ''
            
            # Green rating badge
            green_rating_badge = ""
            if green_rating and green_rating != 'N/A' and green_rating != '':
                badge_class = 'green-badge'
                if 'Platinum' in green_rating:
                    badge_class = 'green-badge platinum'
                elif 'Gold' in green_rating:
                    badge_class = 'green-badge gold'
                elif 'Silver' in green_rating:
                    badge_class = 'green-badge silver'
                elif 'Certified' in green_rating:
                    badge_class = 'green-badge certified'
                
                green_rating_badge = f' <span class="{badge_class}">{green_rating}</span>'
            
            # Check if building has aerial video
            if bbl in aerial_videos_available:
                aerial_content = f'''<div id="aerial-video-{bbl}" style="width: 100%; height: 100%; background: #000; display: flex; align-items: center; justify-content: center; position: relative;">
                    <video controls autoplay loop muted preload="auto" style="width: 100%; height: 100%; object-fit: contain;" 
                           onerror="this.style.display='none'; document.getElementById('video-error-{bbl}').style.display='flex';">
                        <source src="{AWS_VIDEO_BUCKET}/{bbl}_aerial.mp4" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div id="video-error-{bbl}" style="display: none; width: 100%; height: 100%; background: #f0f0f0; align-items: center; justify-content: center; flex-direction: column; position: absolute; top: 0; left: 0;">
                        <div style="text-align: center; color: #666;">
                            <h3>Aerial Video Unavailable</h3>
                            <p>The aerial view for this building is being processed</p>
                            <p style="font-size: 0.9em;">Please check back later</p>
                        </div>
                    </div>
                    <script>
                        // Ensure video autoplays on page load
                        document.addEventListener('DOMContentLoaded', function() {{
                            const video = document.querySelector('#aerial-video-{bbl} video');
                            if (video) {{
                                video.play().catch(e => console.log('Autoplay prevented:', e));
                            }}
                        }});
                    </script>
                </div>'''
            else:
                # Video still processing
                aerial_content = '''<div style="width: 100%; height: 100%; background: #f0f0f0; display: flex; align-items: center; justify-content: center;">
                    <div style="text-align: center; color: #666;">
                        <h3>Aerial View Coming Soon</h3>
                        <p>Google is generating the aerial video for this building</p>
                        <p style="font-size: 0.9em;">Check back in a few hours</p>
                    </div>
                </div>'''
            
            # Create penalty section
            penalty_section = f"""
                <div class="page">
                    <h3 class="page-title">LL97 Compliance</h3>
                    <div class="stat">
                        <span class="stat-label">2024-2029 Status: </span>
                        <span class="stat-value"><span class="{'yes' if compliance_2024 == 'Yes' else 'no'}">{compliance_2024}</span>{f' <span style="color: #c41e3a; font-weight: bold;">(${penalty_2026:,.0f} in annual penalties)</span>' if compliance_2024 == 'No' else ''}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">2030-2034 Status: </span>
                        <span class="stat-value"><span class="{'yes' if compliance_2030 == 'Yes' else 'no'}">{compliance_2030}</span>{f' <span style="color: #c41e3a; font-weight: bold;">(${penalty_2030:,.0f} in annual penalties)</span>' if compliance_2030 == 'No' else ''}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Current Emissions: </span>
                        <span class="stat-value">{total_carbon_emissions:,.0f} tCO2e</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">2024-2029 Limit: </span>
                        <span class="stat-value">{carbon_limit_2024:,.0f} tCO2e</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">2030-2034 Limit: </span>
                        <span class="stat-value">{carbon_limit_2030:,.0f} tCO2e</span>
                    </div>
                </div>
            """

            # Make the HTML
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{row['address']} - ODCV Analysis (v{version})</title>
    <link rel="icon" type="image/png" href="https://rzero.com/wp-content/themes/rzero/build/images/favicons/favicon.png">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Preload aerial video for faster playback -->
    <link rel="preload" 
          as="video" 
          href="https://aerial-videos-forrest.s3.us-east-2.amazonaws.com/{bbl}_aerial.mp4"
          type="video/mp4"
          crossorigin="anonymous">
    <style>
        :root {{
            --rzero-primary: #0066cc;
            --rzero-secondary: #0052a3;
            --text-light: #6b7280;
            --background: #f4fbfd;
            --card-bg: white;
            --border: #e5e7eb;
        }}
        
        body {{ 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            padding: 0; 
            background: var(--background); 
            color: #1a202c;
            line-height: 1.6;
        }}
        
        /* Header */
        .header {{
            background: white;
            border-bottom: 1px solid var(--border);
            padding: 20px 0;
        }}
        
        .logo-header {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .rzero-logo {{
            width: 200px;
            height: 50px;
        }}
        
        h1 {{
            color: var(--rzero-primary);
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
        }}
        
        /* Building Identity Bar */
        .building-identity {{
            padding: 15px 40px;
            background: #f8f8f8;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1200px;
            margin: 0 auto;
        }}

        .neighborhood-badge {{
            font-size: 1.4em;
            color: var(--rzero-primary);
            font-weight: 600;
        }}

        .building-stats {{
            display: flex;
            gap: 20px;
            align-items: center;
        }}

        .stat-item {{
            color: #666;
            font-size: 0.95em;
        }}
        
        /* Green Rating Badges */
        .green-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
            margin-left: 10px;
        }}

        .green-badge.platinum {{
            background: #e5e4e2;
            color: #333;
            border: 1px solid #999;
        }}

        .green-badge.gold {{
            background: #ffd700;
            color: #333;
        }}

        .green-badge.silver {{
            background: #c0c0c0;
            color: #333;
        }}

        .green-badge.certified {{
            background: #28a745;
            color: white;
        }}

        .green-badge:not(.platinum):not(.gold):not(.silver):not(.certified) {{
            background: #17a2b8;
            color: white;
        }}
        
        .container {{ 
            max-width: 1600px; 
            margin: 0 auto; 
            background: white;
            box-shadow: 0 4px 20px rgba(0, 118, 157, 0.08);
            padding: 0;
        }}
        
        /* Section 0 - Title */
        .title-section {{
            background: linear-gradient(to right, #0066cc, #0052a3);
            color: white;
            padding: 30px 15%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 3rem;
        }}
        
        .back {{ 
            margin: 20px 0; 
            padding: 0 20px;
        }}
        .back a {{ color: var(--rzero-primary); text-decoration: none; font-weight: 500; }}
        .back a:hover {{ text-decoration: underline; }}
        
        /* Section styling */
        .section {{ 
            padding: 40px 5%; 
            border-bottom: 3px solid var(--rzero-primary); 
            background: white;
            position: relative;
            width: 100%;
            box-sizing: border-box;
        }}
        
        .section:nth-child(even) {{
            background: #f8fafb;
        }}
        
        /* Override backgrounds to ensure proper alternating pattern */
        .section-white {{
            background: white !important;
        }}
        
        .section-gray {{
            background: #f8fafb !important;
        }}
        
        .section::after {{
            content: '';
            position: absolute;
            bottom: -3px;
            left: 0;
            right: 0;
            height: 20px;
            background: linear-gradient(to bottom, rgba(0, 118, 157, 0.05), transparent);
        }}
        
        .section-header {{ 
            font-size: 2em; 
            color: var(--rzero-primary); 
            margin-bottom: 40px; 
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 15px;
            padding-bottom: 20px;
            border-bottom: 2px solid rgba(0, 118, 157, 0.2);
        }}
        
        .section-header::before {{
            content: '';
            width: 6px;
            height: 40px;
            background: var(--rzero-primary);
            border-radius: 3px;
        }}
        
        .page {{ 
            margin-bottom: 40px;
            width: 100%;
            box-sizing: border-box;
            /* max-width: 900px; */
            /* margin-left: auto; */
            /* margin-right: auto; */
        }}
        .page-title {{ 
            font-size: 1.3em; 
            color: var(--text-dark); 
            margin-bottom: 20px; 
            font-weight: 500; 
        }}
        
        /* Stats - Prospector Style */
        .stat {{ 
            margin: 15px 0; 
            display: flex; 
            align-items: baseline;
            padding: 10px 0;
            border-bottom: 1px solid rgba(0, 102, 204, 0.08);
        }}
        
        .stat:last-child {{ border-bottom: none; }}
        
        .stat-label {{ 
            font-weight: 500; 
            color: #333; 
            min-width: 200px; 
            font-size: 1em;
        }}
        
        .stat-value {{ 
            font-size: 1.1em; 
            color: #555; 
            font-weight: 400;
        }}
        
        .penalty {{ color: #c41e3a; }}
        .savings {{ color: #38a169; }}
        
        /* Highlight boxes */
        .highlight-box {{ 
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
            padding: 40px; 
            border-radius: 12px; 
            text-align: center; 
            margin: 20px 0;
            border: 1px solid #2196f3;
        }}
        
        .highlight-box h4 {{ 
            margin: 0 0 15px 0; 
            color: var(--rzero-primary); 
            font-size: 1.4em; 
        }}
        
        .highlight-box div {{ 
            margin: 8px 0; 
            font-size: 1.1em; 
        }}
        
        .highlight-score {{ 
            font-size: 3.5em; 
            font-weight: 700; 
            color: var(--rzero-primary); 
            margin: 10px 0; 
        }}
        
        /* Carousel styles */
        .carousel-container {{
            position: relative;
            width: 100%;
            /* max-width: 900px; */
            height: 675px;
            overflow: hidden;
            border-radius: 12px;
            margin: 20px 0;
        }}
        
        .carousel-track {{
            display: flex;
            transition: transform 0.3s ease;
            height: 100%;
        }}
        
        .carousel-slide {{
            min-width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .carousel-slide img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: #f0f0f0;
        }}
        
        /* Carousel Navigation */
        .fullscreen-btn {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            border: none;
            padding: 10px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 20px;
            z-index: 10;
            transition: background 0.3s ease;
        }}
        
        .fullscreen-btn:hover {{
            background: rgba(0, 0, 0, 0.8);
        }}
        
        .download-btn:hover {{
            background: rgba(0, 0, 0, 0.8);
        }}
        
        .carousel-btn {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(0, 0, 0, 0.5);
            color: white;
            border: none;
            padding: 20px;
            cursor: pointer;
            font-size: 24px;
            border-radius: 8px;
            transition: background 0.3s ease;
            z-index: 5;
        }}
        
        .carousel-btn:hover {{
            background: rgba(0, 0, 0, 0.7);
        }}
        
        .carousel-prev {{ left: 20px; }}
        .carousel-next {{ right: 20px; }}
        
        .carousel-dots {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
            z-index: 5;
        }}
        
        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            cursor: pointer;
            transition: background 0.3s ease;
        }}
        
        .dot.active {{
            background: white;
        }}
        
        .dot:hover {{
            background: rgba(255, 255, 255, 0.8);
        }}
        
        /* Professional Class Badge from Prospector */
        .class-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-weight: bold;
            font-size: 1.8em;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            position: relative;
            background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.3), transparent);
        }}

        .class-badge::before {{
            content: '';
            position: absolute;
            top: -3px;
            left: -3px;
            right: -3px;
            bottom: -3px;
            border-radius: 50%;
            z-index: -1;
        }}

        .class-A {{ 
            background-color: #FFD700;
            background-image: linear-gradient(135deg, #FFED4E 0%, #FFD700 50%, #B8860B 100%);
            color: #6B4423;
            border: 2px solid #B8860B;
        }}

        .class-B {{ 
            background-color: #C0C0C0;
            background-image: linear-gradient(135deg, #E8E8E8 0%, #C0C0C0 50%, #8B8B8B 100%);
            color: #2C2C2C;
            border: 2px solid #8B8B8B;
        }}

        .class-C {{ 
            background-color: #CD7F32;
            background-image: linear-gradient(135deg, #E89658 0%, #CD7F32 50%, #8B4513 100%);
            color: #4A2511;
            border: 2px solid #8B4513;
        }}

        .class-D, .class-E, .class-F {{ 
            background-color: #8B7355;
            background-image: linear-gradient(135deg, #A0826D 0%, #8B7355 50%, #6B4423 100%);
            color: #FFFFFF;
            border: 2px solid #6B4423;
        }}
        
        /* Energy Grade Styling from Prospector */
        .energy-grade {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        .grade-A {{ background: #d4f1d4; color: #1e7e1e; }}
        .grade-B {{ background: #e6f3d5; color: #5d7e1e; }}
        .grade-C {{ background: #fff3cd; color: #856404; }}
        .grade-D {{ background: #f8d7da; color: #721c24; }}
        .grade-F {{ background: #f5c6cb; color: #721c24; }}
        .grade-NA {{ background: #e9ecef; color: #6c757d; }}
        
        /* Carousel Loading Animation */
        .carousel-slide iframe {{
            opacity: 0;
            transition: opacity 0.5s ease;
        }}
        
        .carousel-slide iframe.loaded {{
            opacity: 1;
        }}
        
        /* Videos should be visible immediately */
        .carousel-slide video {{
            opacity: 1;
        }}
        
        
        /* Chart Controls from Prospector */
        .chart-carousel {{ position: relative; }}
        .chart-toggle {{ 
            display: flex; 
            justify-content: center; 
            gap: 10px; 
            margin-bottom: 20px;
        }}
        .toggle-btn {{
            padding: 8px 20px;
            background: #f0f0f0;
            border: 1px solid #ddd;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: inherit;
            font-size: 14px;
        }}
        .toggle-btn.active {{
            background: var(--rzero-primary);
            color: white;
            border-color: var(--rzero-primary);
        }}
        .toggle-btn:hover {{
            opacity: 0.8;
        }}
        
        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            cursor: pointer;
        }}
        .dot.active {{
            background: white;
        }}
        
        .fullscreen-btn {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            border: none;
            padding: 10px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 20px;
            z-index: 10;
            transition: background 0.3s ease;
        }}

        .fullscreen-btn:hover {{
            background: rgba(0, 0, 0, 0.8);
        }}
        
        .class-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-weight: bold;
            font-size: 1.8em;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }}
        
        .class-A {{ 
            background: linear-gradient(135deg, #FFED4E 0%, #FFD700 50%, #B8860B 100%);
            color: #6B4423;
            border: 2px solid #B8860B;
        }}
        
        .class-B {{ 
            background: linear-gradient(135deg, #E8E8E8 0%, #C0C0C0 50%, #8B8B8B 100%);
            color: #2C2C2C;
            border: 2px solid #8B8B8B;
        }}
        
        .class-C {{ 
            background: linear-gradient(135deg, #E89658 0%, #CD7F32 50%, #8B4513 100%);
            color: #4A2511;
            border: 2px solid #8B4513;
        }}
        
        .grade-A {{ background: #d4f1d4; color: #1e7e1e; padding: 4px 12px; border-radius: 4px; font-weight: bold; }}
        .grade-B {{ background: #e6f3d5; color: #5d7e1e; padding: 4px 12px; border-radius: 4px; font-weight: bold; }}
        .grade-C {{ background: #fff3cd; color: #856404; padding: 4px 12px; border-radius: 4px; font-weight: bold; }}
        .grade-D {{ background: #f8d7da; color: #721c24; padding: 4px 12px; border-radius: 4px; font-weight: bold; }}
        
        .yes {{ color: #38a169; font-weight: bold; }}
        .no {{ color: #c41e3a; font-weight: bold; }}
        .urgent {{ color: #c41e3a; font-weight: bold; }}
        .bas {{ color: #38a169; font-weight: 600; }}
        .no-bas {{ color: #c41e3a; font-weight: 600; }}
    </style>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pannellum@2.5.6/build/pannellum.css">
    <script src="https://cdn.jsdelivr.net/npm/pannellum@2.5.6/build/pannellum.js"></script>
    <!-- Preload aerial video for faster playback -->
    <link rel="preload" as="video" href="{AWS_VIDEO_BUCKET}/{bbl}_aerial.mp4">
</head>
<body>
    <div class="container">
        <!-- Navigation Bar -->
        <div style="background: linear-gradient(to right, #0066cc, #0052a3); padding: 0; margin: 0; width: 100%; position: relative;">
            <a href="index.html" style="text-decoration: none; display: block;">
                <div style="padding: 15px 40px; display: flex; align-items: center; gap: 10px; color: white; cursor: pointer; transition: all 0.3s ease;"
                     onmouseover="this.style.background='rgba(255,255,255,0.1)'" 
                     onmouseout="this.style.background='transparent'">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transition: transform 0.3s ease;"
                         onmouseover="this.style.transform='translateX(-5px)'" 
                         onmouseout="this.style.transform='translateX(0)'">
                        <path d="M19 12H5M12 19l-7-7 7-7"/>
                    </svg>
                    <span style="font-size: 16px; font-weight: 500; opacity: 0.9;">Back to Rankings</span>
                </div>
            </a>
        </div>
        <!-- Section 0.0 - Title -->
        <div class="title-section">
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                <h1 style="margin: 0; color: white; font-size: 2em; font-weight: 700;">
                    <span style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 25px; font-size: 0.8em;">#{rank}</span>
                    <span>{main_address}</span>
                </h1>
                {"<h2 style='margin: 0; color: white; font-size: 1.5em; font-weight: 600; opacity: 0.9;'>" + building_name + "</h2>" if building_name else ""}
                <p style="margin: 0; opacity: 0.9; font-size: 1.1em; padding-left: 0.5rem;">
                    <span style="margin-right: 1.5rem;">{neighborhood}</span>
                </p>
            </div>
            <div style="text-align: center; min-width: 200px;">
                <div style="font-size: 0.9em; opacity: 0.8; margin-bottom: 8px;">2026 ODCV Savings</div>
                <div style="font-size: 2.5em; font-weight: 700; line-height: 1;">${total_2026_savings:,.0f}</div>
                {penalty_breakdown_html}
            </div>
        </div>
        
        <!-- Section 1: General -->
        <div class="section section-white">
            <h2 class="section-header">Image Gallery</h2>
            
            <div class="page">
                <h3 class="page-title" id="image-gallery-title-{bbl}">Static: <span style="color: #555;">Marketing</span></h3>
                <div class="carousel-container">
                    <div class="carousel-track" id="carousel-{bbl}">
                        <div class="carousel-slide active" data-image-type="hero">
                            <div style="position: relative; width: 100%; height: 100%;">
                                <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_hero.jpg" 
                                     style="width: 100%; height: 100%; object-fit: contain; background: #f0f0f0;"
                                     onerror="handleImageError(this, '{bbl}', 'hero')">
                                <button class="download-btn" onclick="downloadImage(this)" title="Download Image" style="position: absolute; top: 20px; left: 20px; background: rgba(0, 0, 0, 0.6); color: white; border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-size: 20px; z-index: 10; transition: background 0.3s ease;">⬇</button>
                                <button class="fullscreen-btn" onclick="toggleFullscreen(this)" title="Fullscreen">⛶</button>
                            </div>
                        </div>
                        <div class="carousel-slide" data-image-type="roadview">
                            <div style="position: relative; width: 100%; height: 100%;">
                                <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_roadview.jpg" 
                                     style="width: 100%; height: 100%; object-fit: contain; background: #f0f0f0;"
                                     onerror="handleImageError(this, '{bbl}', 'roadview')">
                                <button class="download-btn" onclick="downloadImage(this)" title="Download Image" style="position: absolute; top: 20px; left: 20px; background: rgba(0, 0, 0, 0.6); color: white; border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-size: 20px; z-index: 10; transition: background 0.3s ease;">⬇</button>
                                <button class="fullscreen-btn" onclick="toggleFullscreen(this)" title="Fullscreen">⛶</button>
                            </div>
                        </div>
                        <div class="carousel-slide" data-image-type="street">
                            <div style="position: relative; width: 100%; height: 100%;">
                                <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_street.jpg" 
                                     style="width: 100%; height: 100%; object-fit: contain; background: #f0f0f0;"
                                     onerror="handleImageError(this, '{bbl}', 'street')">
                                <button class="download-btn" onclick="downloadImage(this)" title="Download Image" style="position: absolute; top: 20px; left: 20px; background: rgba(0, 0, 0, 0.6); color: white; border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-size: 20px; z-index: 10; transition: background 0.3s ease;">⬇</button>
                                <button class="fullscreen-btn" onclick="toggleFullscreen(this)" title="Fullscreen">⛶</button>
                            </div>
                        </div>
                        <div class="carousel-slide" data-image-type="satellite">
                            <div style="position: relative; width: 100%; height: 100%;">
                                <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_satellite.jpg" 
                                     style="width: 100%; height: 100%; object-fit: contain; background: #f0f0f0;"
                                     onerror="handleImageError(this, '{bbl}', 'satellite')">
                                <button class="download-btn" onclick="downloadImage(this)" title="Download Image" style="position: absolute; top: 20px; left: 20px; background: rgba(0, 0, 0, 0.6); color: white; border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-size: 20px; z-index: 10; transition: background 0.3s ease;">⬇</button>
                                <button class="fullscreen-btn" onclick="toggleFullscreen(this)" title="Fullscreen">⛶</button>
                            </div>
                        </div>
                        <div class="carousel-slide" data-image-type="equipment">
                            <div style="position: relative; width: 100%; height: 100%;">
                                <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_equipment.jpg" 
                                     style="width: 100%; height: 100%; object-fit: contain; background: #f0f0f0;"
                                     onerror="handleImageError(this, '{bbl}', 'equipment')">
                                <button class="download-btn" onclick="downloadImage(this)" title="Download Image" style="position: absolute; top: 20px; left: 20px; background: rgba(0, 0, 0, 0.6); color: white; border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-size: 20px; z-index: 10; transition: background 0.3s ease;">⬇</button>
                                <button class="fullscreen-btn" onclick="toggleFullscreen(this)" title="Fullscreen">⛶</button>
                            </div>
                        </div>
                        <div class="carousel-slide" data-image-type="double">
                            <div style="position: relative; width: 100%; height: 100%;">
                                <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_double.jpg" 
                                     style="width: 100%; height: 100%; object-fit: contain; background: #f0f0f0;"
                                     onerror="handleImageError(this, '{bbl}', 'double')">
                                <button class="download-btn" onclick="downloadImage(this)" title="Download Image" style="position: absolute; top: 20px; left: 20px; background: rgba(0, 0, 0, 0.6); color: white; border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-size: 20px; z-index: 10; transition: background 0.3s ease;">⬇</button>
                                <button class="fullscreen-btn" onclick="toggleFullscreen(this)" title="Fullscreen">⛶</button>
                            </div>
                        </div>
                        <div class="carousel-slide" data-image-type="stack">
                            <div style="position: relative; width: 100%; height: 100%;">
                                <img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_stack.jpg" 
                                     style="width: 100%; height: 100%; object-fit: contain; background: #f0f0f0;"
                                     onerror="handleImageError(this, '{bbl}', 'stack')">
                                <button class="download-btn" onclick="downloadImage(this)" title="Download Image" style="position: absolute; top: 20px; left: 20px; background: rgba(0, 0, 0, 0.6); color: white; border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-size: 20px; z-index: 10; transition: background 0.3s ease;">⬇</button>
                                <button class="fullscreen-btn" onclick="toggleFullscreen(this)" title="Fullscreen">⛶</button>
                            </div>
                        </div>
                    </div>
                    <button class="carousel-btn carousel-prev" onclick="moveCarousel('{bbl}', -1)">❮</button>
                    <button class="carousel-btn carousel-next" onclick="moveCarousel('{bbl}', 1)">❯</button>
                    <div class="carousel-dots" id="carousel-dots-{bbl}">
                        <span class="dot active" onclick="goToSlide('{bbl}', 0)"></span>
                        <span class="dot" onclick="goToSlide('{bbl}', 1)"></span>
                        <span class="dot" onclick="goToSlide('{bbl}', 2)"></span>
                        <span class="dot" onclick="goToSlide('{bbl}', 3)"></span>
                        <span class="dot" onclick="goToSlide('{bbl}', 4)"></span>
                        <span class="dot" onclick="goToSlide('{bbl}', 5)"></span>
                    </div>
                </div>
            </div>
            
            <div class="page">
                <h3 class="page-title" id="interactive-views-title-{bbl}">Dynamic: <span style="color: #555;">Drone Footage</span></h3>
                <div class="carousel-container">
                    <div class="carousel-track" id="interactive-carousel-{bbl}">
                        <div class="carousel-slide" data-type="video">
                            {aerial_content}
                        </div>
                        <div class="carousel-slide" data-type="pano">
                            <div id="panorama-{bbl}" style="width: 100%; height: 675px; background: #f0f0f0; position: relative;">
                                <div id="viewer-{bbl}" style="width: 100%; height: 100%;"></div>
                            </div>
                        </div>
                    </div>
                    
                    
                    <!-- Navigation Controls -->
                    <button class="carousel-btn carousel-prev" onclick="moveInteractiveCarousel('{bbl}', -1)" title="Previous">❮</button>
                    <button class="carousel-btn carousel-next" onclick="moveInteractiveCarousel('{bbl}', 1)" title="Next">❯</button>
                    
                    <!-- Dot Navigation with Labels -->
                    <div class="carousel-dots">
                        <span class="dot active" onclick="goToInteractiveSlide('{bbl}', 0)" title="Aerial Video"></span>
                        <span class="dot" onclick="goToInteractiveSlide('{bbl}', 1)" title="360° Virtual Tour"></span>
                    </div>
                </div>
            </div>
        </div>
        </div>
        
        <!-- Building Overview Section -->
        <div class="section section-gray">
            <h2 class="section-header">Building Overview</h2>
            
            <div class="page">
                <h3 class="page-title">Property</h3>
                <div class="stat">
                    <span class="stat-label">Last Renovated: </span>
                    <span class="stat-value">{year_altered}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Floors: </span>
                    <span class="stat-value">{num_floors}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Units: </span>
                    <span class="stat-value">{total_units}</span>
                </div>
                {"<div class='stat'><span class='stat-label'>Avg Floor Sq Ft: </span><span class='stat-value'>" + typical_floor_sqft + " sq ft</span></div>" if typical_floor_sqft != 'N/A' else ""}
                <div class="stat">
                    <span class="stat-label">Total Floor Area: </span>
                    <span class="stat-value">{int(total_area):,} sq ft</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Office Floor Area: </span>
                    <span class="stat-value">{office_sqft:,} sq ft ({office_pct}% of total)</span>
                </div>
            </div>
            
            <div class="page">
                <h3 class="page-title">Commercial</h3>
                <div class="stat">
                    <span class="stat-label">Class: </span>
                    <span class="stat-value"><span class="class-badge class-{building_class.replace(' ', '')}">{building_class}</span></span>
                </div>
                {"<div class='stat'><span class='stat-label'>Owner & Manager: </span><span class='stat-value'>" + owner + owner_logo + "</span></div>" if owner == property_manager else "<div class='stat'><span class='stat-label'>Owner: </span><span class='stat-value'>" + owner + owner_logo + "</span></div><div class='stat'><span class='stat-label'>Manager: </span><span class='stat-value'>" + property_manager + manager_logo + "</span></div>"}
                {"<div class='stat'><span class='stat-label'>Owner Contact: </span><span class='stat-value'>" + landlord_contact + "</span></div>" if landlord_contact != 'Unavailable' else ""}
                {"<div class='stat'><span class='stat-label'>Property Manager Contact: </span><span class='stat-value'>" + property_manager_contact + "</span></div>" if property_manager_contact != 'Unavailable' else ""}
                <div class="stat">
                    <span class="stat-label">% Leased: </span>
                    <span class="stat-value">{pct_leased}%</span>
                </div>
                {"<div class='stat'><span class='stat-label'>OpEx per Sq Ft: </span><span class='stat-value'>" + opex_per_sqft + "</span></div>" if opex_per_sqft != 'N/A' else ""}
            </div>
            
            <div class="page">
                <h3 class="page-title">Equipment</h3>
                <div class="stat">
                    <span class="stat-label">Elevator Shafts: </span>
                    <span class="stat-value">{num_elevators}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">BMS Controls: </span>
                    <span class="stat-value">{bas_text}</span>
                </div>
                {"<div class='stat'><span class='stat-label'>Heating System: </span><span class='stat-value'>" + heating_type + "</span></div>" if heating_type != 'N/A' else ""}
                {"<div class='stat'><span class='stat-label'>Cooling System: </span><span class='stat-value'>" + cooling_type + "</span></div>" if cooling_type != 'N/A' else ""}
                {"<div class='stat'><span class='stat-label'>Rooftop System: </span><span class='stat-value'>Cooling Towers: " + str(cooling_towers) + " | Water Tanks: " + str(water_tanks) + "</span></div>" if (cooling_towers > 0 or water_tanks > 0) else ""}
            </div>
        </div>
        
        {f'''<!-- Major Tenants Section -->
        <div class="section section-white">
            <h2 class="section-header">Major Tenants</h2>
            <div class="page">
                <div style="overflow-x: auto;">
                    <table id="tenantTable-{bbl}" style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
                        <thead>
                            <tr style="background: #f8f9fa; border-bottom: 2px solid #e5e7eb;">
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151; cursor: pointer;" onclick="sortTenantTable(0)">Tenant* <span class="sort-indicator">↕</span></th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151; cursor: pointer;" onclick="sortTenantTable(1)">Industry <span class="sort-indicator">↕</span></th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151; cursor: pointer;" onclick="sortTenantTable(2)">Floor <span class="sort-indicator">↕</span></th>
                                <th style="padding: 12px; text-align: right; font-weight: 600; color: #374151; cursor: pointer;" onclick="sortTenantTable(3)">SF Occupied <span class="sort-indicator">↕</span></th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151; cursor: pointer;" onclick="sortTenantTable(4)">Move Date <span class="sort-indicator">↕</span></th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151; cursor: pointer;" onclick="sortTenantTable(5)">Exp Date <span class="sort-indicator">↕</span></th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f"""<tr style="border-bottom: 1px solid #e5e7eb;">
                                <td style="padding: 12px; color: #1f2937;">{tenant['Tenant']}</td>
                                <td style="padding: 12px; color: #6b7280;">{tenant['Industry']}</td>
                                <td style="padding: 12px; color: #6b7280;">{tenant['Floor']}</td>
                                <td style="padding: 12px; text-align: right; color: #1f2937; font-weight: 500;">{tenant['SF Occupied']}</td>
                                <td style="padding: 12px; color: #6b7280;">{tenant['Move In Date']}</td>
                                <td style="padding: 12px; color: #6b7280;">{tenant['Exp Date'] if tenant['Exp Date'] != '-' else 'N/A'}</td>
                            </tr>""" for _, tenant in building_tenants.iterrows()])}
                        </tbody>
                    </table>
                </div>
                <div style="margin-top: 16px; font-size: 0.85em; color: #6b7280;">
                    * Showing top {len(building_tenants)} tenants by square footage
                </div>
            </div>
        </div>
        ''' if not building_tenants.empty else ""}
        
        <!-- Section 2: Building -->
        <div class="section section-white">
            <h2 class="section-header">Energy Efficiency</h2>
            
            <!-- Page 2.0 - Efficiency -->
            <div class="page">
                <h3 class="page-title">Performance</h3>
                <div class="stat">
                    <span class="stat-label">ENERGY STAR Score: </span>
                    <div style="display: flex; align-items: center; gap: 30px;">
                        <svg viewBox="0 0 200 120" style="width: 200px; height: 120px;">
                            <!-- Colored sections -->
                            <path d="M 20 100 A 80 80 0 0 1 73 30" fill="none" stroke="#c41e3a" stroke-width="20"/>
                            <path d="M 73 30 A 80 80 0 0 1 127 30" fill="none" stroke="#ffc107" stroke-width="20"/>
                            <path d="M 127 30 A 80 80 0 0 1 180 100" fill="none" stroke="#38a169" stroke-width="20"/>
                            <!-- Score number in center -->
                            <text x="100" y="85" text-anchor="middle" font-size="36" font-weight="bold" fill="{energy_star_color}">{energy_star}</text>
                            <!-- Labels -->
                            <text x="20" y="115" text-anchor="middle" font-size="12" fill="#666">0</text>
                            <text x="180" y="115" text-anchor="middle" font-size="12" fill="#666">100</text>
                        </svg>
                        <div>
                            <div style="font-size: 1.2em; color: #666; font-weight: 500;">Target Score: {target_score} (self reported)</div>
                            <div style="font-size: 1.1em; margin-top: 5px;">{energy_star_delta}</div>
                        </div>
                    </div>
                </div>
                <div class="stat">
                    <span class="stat-label">LL33 Grade: </span>
                    <span class="stat-value"><span class="energy-grade grade-{ll33_grade_raw}">{ll33_grade}</span></span>
                </div>
            </div>
            
            {penalty_section}
        </div>
        
        <!-- Section 3: Energy Consumption -->
        <div class="section section-gray">
            <h2 class="section-header">Energy Consumption</h2>
            
            <div class="page">
                <h3 class="page-title">Usage</h3>
            <div class="chart-carousel">
                <div class="chart-toggle">
                    <button class="toggle-btn active" onclick="showChart('usage', 'building')">Building</button>
                    <button class="toggle-btn" onclick="showChart('usage', 'office')">Office</button>
                </div>
                <div id="building_usage_container" class="chart-container">
                    <div id="energy_chart" style="width: 100%; height: 400px;"></div>
                </div>
                <div id="office_usage_container" class="chart-container" style="display: none;">
                    <div id="office_energy_chart" style="width: 100%; height: 400px;"></div>
                </div>
            </div>
        </div>
        
        <div class="page">
            <h3 class="page-title">Cost</h3>
            <div class="chart-carousel">
                <div class="chart-toggle">
                    <button class="toggle-btn active" onclick="showChart('cost', 'building')">Building</button>
                    <button class="toggle-btn" onclick="showChart('cost', 'office')">Office</button>
                </div>
                <div id="building_cost_container" class="chart-container">
                    <div id="energy_cost_chart" style="width: 100%; height: 400px;"></div>
                </div>
                <div id="office_cost_container" class="chart-container" style="display: none;">
                    <div id="office_cost_chart" style="width: 100%; height: 400px;"></div>
                </div>
            </div>
        </div>
        </div>
        
        <!-- Section 4: ODCV -->
        <div class="section section-white">
            <h2 class="section-header">HVAC Analysis</h2>
            
            <div class="page">
                <h3 class="page-title">Electricity Disaggregation</h3>
                <div id="hvac_pct_chart" style="width: 100%; height: 400px;"></div>
            </div>
            
            <div class="page">
                <h3 class="page-title">Savings Potential</h3>
                <div id="odcv_savings_chart" style="width: 100%; height: 400px;"></div>
            </div>
        </div>
        
{f'''        <!-- Air Quality Section -->
        <div class="section section-gray">
            <h2 class="section-header">Air Quality</h2>
            
            <div class="page">
                <h3 class="page-title">Outdoor Pollution (PM2.5)</h3>''' if chart_dates else ""}
            
            <div class="iaq-summary" style="margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;">
                <div class="iaq-stat-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; text-align: center;">
                    <div class="iaq-stat">
                        <div class="iaq-label" style="font-size: 12px; color: #6c757d; margin-bottom: 4px;">Max</div>
                        <div class="iaq-value" style="font-size: 24px; font-weight: bold; color: #c41e3a;">{max_pm25:.1f} μg/m³</div>
                        <div class="iaq-category" style="font-size: 11px; color: #6c757d; margin-top: 4px;">Daily Average</div>
                    </div>
                    <div class="iaq-stat">
                        <div class="iaq-label" style="font-size: 12px; color: #6c757d; margin-bottom: 4px;">Average</div>
                        <div class="iaq-value" style="font-size: 24px; font-weight: bold; color: {aqi_color};">{avg_pm25:.1f} μg/m³</div>
                        <div class="iaq-category" style="font-size: 11px; color: #6c757d; margin-top: 4px;">Daily Average</div>
                    </div>
                    <div class="iaq-stat">
                        <div class="iaq-label" style="font-size: 12px; color: #6c757d; margin-bottom: 4px;">Good</div>
                        <div class="iaq-value" style="font-size: 24px; font-weight: bold; color: #00e400;">12 μg/m³</div>
                        <div class="iaq-category" style="font-size: 11px; color: #6c757d; margin-top: 4px;">EPA Threshold</div>
                    </div>
                </div>
            </div>
            
            <div id="pm25_chart" style="width: 100%; height: 400px;"></div>
            </div>
        </div>''' if chart_dates else ""}}
        
    </div>
    
    <script>
    // Unit conversion functions
    function kBtuToKwh(kbtu) {{ return kbtu / 3.412; }}
    function kBtuToTherms(kbtu) {{ return kbtu / 100; }}
    function kBtuToLbs(kbtu) {{ return kbtu / 1.194; }}
    
    // Toggle chart function
    function showChart(type, view) {{
        let buildingContainer, officeContainer;
        
        if (type === 'usage') {{
            buildingContainer = document.getElementById('building_usage_container');
            officeContainer = document.getElementById('office_usage_container');
        }} else if (type === 'cost') {{
            buildingContainer = document.getElementById('building_cost_container');
            officeContainer = document.getElementById('office_cost_container');
        }}
        
        const buttons = event.target.parentElement.querySelectorAll('.toggle-btn');
        
        buttons.forEach(btn => {{
            btn.style.background = '#f0f0f0';
            btn.style.color = '#333';
            btn.style.border = '1px solid #ddd';
            btn.classList.remove('active');
        }});
        
        event.target.classList.add('active');
        event.target.style.background = '#0066cc';
        event.target.style.color = 'white';
        event.target.style.border = 'none';
        
        if (view === 'building') {{
            buildingContainer.style.display = 'block';
            officeContainer.style.display = 'none';
        }} else {{
            buildingContainer.style.display = 'none';
            officeContainer.style.display = 'block';
            
            // Resize the office chart after making it visible
            // This fixes the "squished" chart issue
            setTimeout(() => {{
                if (type === 'usage' && window.Plotly) {{
                    Plotly.Plots.resize('office_energy_chart');
                }} else if (type === 'cost' && window.Plotly) {{
                    Plotly.Plots.resize('office_cost_chart');
                }}
            }}, 10);  // Small delay to ensure DOM update
        }}
    }}
    
    let carouselIndex = {{}};
    let hiddenSlides = {{}};
    
    // Handle missing images by hiding slides
    function handleImageError(img, bbl, imageType) {{
        const slide = img.closest('.carousel-slide');
        const track = slide.parentElement;
        const allSlides = Array.from(track.querySelectorAll('.carousel-slide'));
        const slideIndex = allSlides.indexOf(slide);
        
        // Hide the slide
        slide.style.display = 'none';
        
        // Track hidden slides
        if (!hiddenSlides[bbl]) hiddenSlides[bbl] = [];
        hiddenSlides[bbl].push(slideIndex);
        
        // Update dots
        updateCarouselDots(bbl);
        
        // If current slide is hidden, move to next visible
        if (carouselIndex[bbl] === slideIndex) {{
            moveCarousel(bbl, 1);
        }}
        
        console.log(`Image not found: ${{bbl}}_${{imageType}}.jpg`);
    }}
    
    // Update dots to only show for visible slides
    function updateCarouselDots(bbl) {{
        const track = document.getElementById(`carousel-${{bbl}}`);
        const slides = Array.from(track.querySelectorAll('.carousel-slide'));
        const dotsContainer = document.getElementById(`carousel-dots-${{bbl}}`);
        
        // Clear existing dots
        dotsContainer.innerHTML = '';
        
        // Add dots only for visible slides
        slides.forEach((slide, index) => {{
            if (slide.style.display !== 'none') {{
                const dot = document.createElement('span');
                dot.className = 'dot';
                if (index === carouselIndex[bbl]) dot.classList.add('active');
                dot.onclick = () => goToSlide(bbl, index);
                dotsContainer.appendChild(dot);
            }}
        }});
    }}
    
    function moveCarousel(bbl, direction) {{
        const track = document.getElementById(bbl.includes('carousel') ? bbl : `carousel-${{bbl}}`);
        const slides = Array.from(track.querySelectorAll('.carousel-slide'));
        const visibleSlides = slides.filter(s => s.style.display !== 'none');
        
        if (visibleSlides.length === 0) return;
        
        if (!carouselIndex[bbl]) carouselIndex[bbl] = 0;
        
        // Find next visible slide
        let currentIndex = carouselIndex[bbl];
        let attempts = 0;
        do {{
            currentIndex += direction;
            if (currentIndex < 0) currentIndex = slides.length - 1;
            if (currentIndex >= slides.length) currentIndex = 0;
            attempts++;
        }} while (slides[currentIndex].style.display === 'none' && attempts < slides.length);
        
        carouselIndex[bbl] = currentIndex;
        track.style.transform = `translateX(-${{currentIndex * 100}}%)`;
        
        // Update title based on current slide
        const currentSlide = slides[currentIndex];
        const imageType = currentSlide.getAttribute('data-image-type');
        const actualBbl = bbl.includes('carousel') ? bbl.replace('carousel-', '') : bbl;
        const titleElement = document.getElementById(`image-gallery-title-${{actualBbl}}`);
        if (titleElement) {{
            const imageTypeMap = {{
                'hero': 'Marketing',
                'roadview': 'Streetview (Cyclomedia)',
                'street': 'Streetview (Google)',
                'satellite': 'Satellite (Unannotated)',
                'equipment': 'Satellite (Annotated)',
                'double': 'Side-by-Side',
                'stack': 'Stacking Diagram'
            }};
            titleElement.innerHTML = `Static: <span style="color: #555;">${{imageTypeMap[imageType] || 'Unknown'}}</span>`;
        }}
        
        // Update dots for visible slides only
        updateCarouselDots(bbl.includes('carousel') ? bbl.replace('carousel-', '') : bbl);
    }}
    
    function goToSlide(bbl, index) {{
        const track = document.getElementById(`carousel-${{bbl}}`);
        const slides = Array.from(track.querySelectorAll('.carousel-slide'));
        
        // Make sure target slide is visible
        if (slides[index] && slides[index].style.display !== 'none') {{
            carouselIndex[bbl] = index;
            track.style.transform = `translateX(-${{index * 100}}%)`;
            
            // Update title based on current slide
            const currentSlide = slides[index];
            const imageType = currentSlide.getAttribute('data-image-type');
            const titleElement = document.getElementById(`image-gallery-title-${{bbl}}`);
            if (titleElement) {{
                const imageTypeMap = {{
                    'hero': 'Marketing',
                    'roadview': 'Streetview (Cyclomedia)',
                    'street': 'Streetview (Google)',
                    'satellite': 'Satellite (Unannotated)',
                    'equipment': 'Satellite (Annotated)',
                    'double': 'Side-by-Side',
                    'stack': 'Stacking Diagram'
                }};
                titleElement.innerHTML = `Static: <span style="color: #555;">${{imageTypeMap[imageType] || 'Unknown'}}</span>`;
            }}
            
            updateCarouselDots(bbl);
        }}
    }}
    
    function toggleFullscreen(button) {{
        const container = button.parentElement;
        const img = container.querySelector('img');
        
        if (!document.fullscreenElement) {{
            if (container.requestFullscreen) {{
                container.requestFullscreen();
            }} else if (container.webkitRequestFullscreen) {{
                container.webkitRequestFullscreen();
            }}
            button.innerHTML = '\u2715';
        }} else {{
            if (document.exitFullscreen) {{
                document.exitFullscreen();
            }}
            button.innerHTML = '\u26f6';
        }}
    }}
    
    function downloadImage(button) {{
        const img = button.parentElement.querySelector('img');
        const link = document.createElement('a');
        link.href = img.src;
        link.download = img.src.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }}
    
    // Enhanced Interactive carousel with smooth transitions
    let interactiveIndex = 0;
    
    function moveInteractiveCarousel(bbl, direction) {{
        const carousel = document.getElementById('interactive-carousel-' + bbl);
        const dots = carousel.parentElement.querySelectorAll('.dot');
        const totalViews = 2;
        
        interactiveIndex += direction;
        
        // Handle wrap-around
        if (interactiveIndex < 0) interactiveIndex = totalViews - 1;
        if (interactiveIndex >= totalViews) interactiveIndex = 0;
        
        // Smooth transition with enhanced transform
        carousel.style.transform = `translateX(-${{interactiveIndex * 100}}%)`;
        
        // Update dot indicators with smooth animation
        dots.forEach((dot, i) => {{
            dot.classList.toggle('active', i === interactiveIndex);
        }});
        
        // Add subtle button feedback animation
        const buttons = carousel.parentElement.querySelectorAll('.carousel-btn');
        buttons.forEach(btn => {{
            btn.style.transform = 'scale(0.95)';
            setTimeout(() => btn.style.transform = 'scale(1)', 100);
        }});
        
        // Update title based on current slide
        const currentSlide = carousel.children[interactiveIndex];
        const slideType = currentSlide.getAttribute('data-type');
        const titleElement = document.getElementById(`interactive-views-title-${{bbl}}`);
        if (titleElement) {{
            const typeMap = {{
                'video': 'Drone Footage',
                'pano': '360 Panorama'
            }};
            titleElement.innerHTML = `Dynamic: <span style="color: #555;">${{typeMap[slideType] || 'Unknown'}}</span>`;
        }}
        
        // Auto-play video when navigating to aerial slide
        if (slideType === 'video' && interactiveIndex === 0) {{
            const video = document.querySelector(`#aerial-video-${{bbl}} video`);
            if (video) {{
                video.play().catch(e => console.log('Autoplay prevented on carousel navigation:', e));
            }}
        }}
        
        // Handle panorama initialization and rotation
        if (slideType === 'pano') {{
            const viewerEl = document.getElementById(`viewer-${{bbl}}`);
            if (viewerEl && viewerEl.pannellumViewer) {{
                // Start auto rotation when user navigates to panorama
                viewerEl.pannellumViewer.startAutoRotate(-2);
            }}
        }}
        
        // Trigger loading animation for iframes
        const iframe = currentSlide.querySelector('iframe');
        if (iframe && !iframe.classList.contains('loaded')) {{
            setTimeout(() => iframe.classList.add('loaded'), 500);
        }}
    }}
    
    function goToInteractiveSlide(bbl, index) {{
        const direction = index - interactiveIndex;
        interactiveIndex = index;
        moveInteractiveCarousel(bbl, 0);
    }}
    
    // Enhanced fullscreen functionality
    function toggleFullscreen(button) {{
        const container = button.closest('.carousel-slide, .carousel-container');
        const iframe = container.querySelector('iframe, video');
        
        if (!document.fullscreenElement) {{
            if (iframe && iframe.requestFullscreen) {{
                iframe.requestFullscreen();
            }} else if (container.requestFullscreen) {{
                container.requestFullscreen();
            }}
            button.textContent = '⛷';
        }} else {{
            if (document.exitFullscreen) {{
                document.exitFullscreen();
                button.textContent = '⛶';
            }}
        }}
    }}
    
    // Energy chart
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const elecData = {{
        x: months,
        y: {elec_usage},
        name: 'Electricity',
        type: 'scatter',
        mode: 'lines+markers',
        line: {{color: '#0066cc', width: 3}},
        marker: {{size: 8}},
        hovertemplate: '%{{x}}<br>Elec: %{{y:,.0f}} kBtu<br>(%{{customdata:,.0f}} kWh)<extra></extra>',
        customdata: {elec_usage}.map(v => kBtuToKwh(v))
    }};
    
    const gasData = {{
        x: months,
        y: {gas_usage},
        name: 'Gas',
        type: 'scatter',
        mode: 'lines+markers',
        line: {{color: '#ff6600', width: 3}},
        marker: {{size: 8}},
        hovertemplate: '%{{x}}<br>Gas: %{{y:,.0f}} kBtu<br>(%{{customdata:,.0f}} Therms)<extra></extra>',
        customdata: {gas_usage}.map(v => kBtuToTherms(v))
    }};
    
    const steamData = {{
        x: months,
        y: {steam_usage},
        name: 'Steam',
        type: 'scatter',
        mode: 'lines+markers',
        line: {{color: '#ffc107', width: 3}},
        marker: {{size: 8}},
        hovertemplate: '%{{x}}<br>Steam: %{{y:,.0f}} kBtu<br>(%{{customdata:,.0f}} lbs)<extra></extra>',
        customdata: {steam_usage}.map(v => kBtuToLbs(v))
    }};
    
    const layout = {{
        title: {{
            text: 'Monthly Usage (2023)',
            font: {{size: 20}}
        }},
        yaxis: {{
            title: 'Usage (kBtu)',
            showgrid: false
        }},
        xaxis: {{
            showgrid: false
        }},
        font: {{family: 'Arial, sans-serif'}},
        plot_bgcolor: '#ffffff',
        paper_bgcolor: 'white',
        hovermode: 'x unified'
    }};
    
    // Building usage chart - only show fuels with usage
    const buildingUsageData = [];
    if ({elec_usage}.some(v => v > 0)) buildingUsageData.push(elecData);
    if ({gas_usage}.some(v => v > 0)) buildingUsageData.push(gasData);
    if ({steam_usage}.some(v => v > 0)) buildingUsageData.push(steamData);
    
    Plotly.newPlot('energy_chart', buildingUsageData, layout, {{
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
        displaylogo: false,
        displayModeBar: true
    }});
    
    // Office Energy Chart
    const officeElecData = {{
        x: months,
        y: {office_elec_usage},
        name: 'Electricity',
        type: 'bar',
        marker: {{color: '#0066cc'}}
    }};
    
    const officeGasData = {{
        x: months,
        y: {office_gas_usage},
        name: 'Gas',
        type: 'bar',
        marker: {{color: '#ff6600'}}
    }};
    
    const officeSteamData = {{
        x: months,
        y: {office_steam_usage},
        name: 'Steam',
        type: 'bar',
        marker: {{color: '#ffc107'}}
    }};
    
    const officeLayout = {{
        title: {{
            text: 'Monthly Office Usage (2023)',
            font: {{size: 20}}
        }},
        yaxis: {{
            title: 'Usage (kBtu)',
            showgrid: false
        }},
        xaxis: {{
            showgrid: false,
            range: [-0.5, 11.5],  // Force x-axis to show all 12 months with padding
            fixedrange: true
        }},
        barmode: 'group',
        font: {{family: 'Arial, sans-serif'}},
        plot_bgcolor: '#ffffff',
        paper_bgcolor: 'white',
        hovermode: 'x unified'
    }};
    
    // Office usage chart - only show fuels with usage
    const officeUsageData = [];
    if ({office_elec_usage}.some(v => v > 0)) officeUsageData.push(officeElecData);
    if ({office_gas_usage}.some(v => v > 0)) officeUsageData.push(officeGasData);
    if ({office_steam_usage}.some(v => v > 0)) officeUsageData.push(officeSteamData);
    
    Plotly.newPlot('office_energy_chart', officeUsageData, officeLayout, {{
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
        displaylogo: false,
        displayModeBar: true
    }});
    
    // Energy Cost Chart
    const elecCost = {{
        x: months, 
        y: {elec_cost}, 
        name: 'Electricity', 
        type: 'scatter', 
        mode: 'lines+markers', 
        line: {{color: '#0066cc', width: 3}},
        marker: {{size: 8}}
    }};
    
    const gasCost = {{
        x: months, 
        y: {gas_cost}, 
        name: 'Gas', 
        type: 'scatter', 
        mode: 'lines+markers', 
        line: {{color: '#ff6600', width: 3}},
        marker: {{size: 8}}
    }};
    
    const steamCostData = {{
        x: months, 
        y: {steam_cost}, 
        name: 'Steam', 
        type: 'scatter', 
        mode: 'lines+markers', 
        line: {{color: '#ffc107', width: 3}},
        marker: {{size: 8}}
    }};
    
    const costLayout = {{
        title: {{
            text: 'Monthly Cost (2023)',
            font: {{size: 20}}
        }},
        yaxis: {{
            title: '',
            tickformat: '$,.0f',
            showgrid: false
        }},
        xaxis: {{
            showgrid: false
        }},
        font: {{family: 'Inter, sans-serif'}},
        plot_bgcolor: '#ffffff',
        paper_bgcolor: 'white',
        hovermode: 'x unified'
    }};

    // Building cost chart - only show fuels with costs
    const buildingCostData = [];
    if ({elec_cost}.some(v => v > 0)) buildingCostData.push(elecCost);
    if ({gas_cost}.some(v => v > 0)) buildingCostData.push(gasCost);
    if ({steam_cost}.some(v => v > 0)) buildingCostData.push(steamCostData);
    
    Plotly.newPlot('energy_cost_chart', buildingCostData, costLayout, {{
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
        displaylogo: false,
        displayModeBar: true
    }});

    // Add annual cost caption below the chart
    document.getElementById('energy_cost_chart').insertAdjacentHTML('afterend', 
        '<div style="text-align: center; margin-top: 10px; font-size: 16px; color: #666;">Annual Cost: $' + ({annual_building_cost:.0f}).toLocaleString() + '</div>'
    );
    
    // Office Cost Chart
    const officeElecCost = {{
        x: months, 
        y: {office_elec_cost}, 
        name: 'Electricity', 
        type: 'bar', 
        marker: {{color: '#0066cc'}}
    }};
    
    const officeGasCost = {{
        x: months, 
        y: {office_gas_cost}, 
        name: 'Gas', 
        type: 'bar', 
        marker: {{color: '#ff6600'}}
    }};
    
    const officeSteamCostData = {{
        x: months, 
        y: {office_steam_cost}, 
        name: 'Steam', 
        type: 'bar', 
        marker: {{color: '#ffc107'}}
    }};
    
    const officeCostLayout = {{
        title: {{
            text: 'Office Space Monthly Cost (2023)',
            font: {{size: 20}}
        }},
        yaxis: {{
            title: '',
            tickformat: '$,.0f',
            showgrid: false
        }},
        xaxis: {{
            showgrid: false,
            range: [-0.5, 11.5],  // Force x-axis to show all 12 months with padding
            fixedrange: true
        }},
        barmode: 'group',
        font: {{family: 'Inter, sans-serif'}},
        plot_bgcolor: '#ffffff',
        paper_bgcolor: 'white',
        hovermode: 'x unified'
    }};

    // Office cost chart - only show fuels with costs
    const officeCostData = [];
    if ({office_elec_cost}.some(v => v > 0)) officeCostData.push(officeElecCost);
    if ({office_gas_cost}.some(v => v > 0)) officeCostData.push(officeGasCost);
    if ({office_steam_cost}.some(v => v > 0)) officeCostData.push(officeSteamCostData);
    
    Plotly.newPlot('office_cost_chart', officeCostData, officeCostLayout, {{
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
        displaylogo: false,
        displayModeBar: true
    }});

    // Add annual cost caption below the chart
    document.getElementById('office_cost_chart').insertAdjacentHTML('afterend', 
        '<div style="text-align: center; margin-top: 10px; font-size: 16px; color: #666;">Annual Cost: $' + ({annual_office_cost:.0f}).toLocaleString() + '</div>'
    );
    
    // HVAC Percentage Chart
    const hvacData = {{
        x: months,
        y: {hvac_pct},
        type: 'scatter',
        mode: 'lines+markers',
        fill: 'tozeroy',
        line: {{color: '#0066cc', width: 3}},
        fillcolor: 'rgba(0, 102, 204, 0.2)',
        marker: {{size: 8}},
        name: 'HVAC %'
    }};
    
    const hvacLayout = {{
        title: {{
            text: 'HVAC as % of Total Electricity Usage',
            font: {{size: 20}}
        }},
        yaxis: {{
            title: '',
            tickformat: '.0%',
            showgrid: false,
            rangemode: 'tozero'  // Auto-scale but start at 0
        }},
        xaxis: {{
            showgrid: false
        }},
        font: {{family: 'Arial, sans-serif'}},
        plot_bgcolor: '#ffffff',
        paper_bgcolor: 'white',
        hovermode: 'x unified'
    }};
    
    Plotly.newPlot('hvac_pct_chart', [hvacData], hvacLayout, {{
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
        displaylogo: false,
        displayModeBar: true
    }});

    // Add annual average caption below the chart
    document.getElementById('hvac_pct_chart').insertAdjacentHTML('afterend', 
        '<div style="text-align: center; margin-top: 10px; font-size: 16px; color: #666;">Annual Average: {annual_avg_hvac_pct * 100:.1f}%</div>'
    );
    
    // ODCV Savings Chart
    const odcvElecSave = {{x: months, y: {odcv_elec_savings}, name: 'Elec', type: 'bar', marker: {{color: '#0066cc'}}}};
    const odcvGasSave = {{x: months, y: {odcv_gas_savings}, name: 'Gas', type: 'bar', marker: {{color: '#ff6600'}}}};
    const odcvSteamSave = {{x: months, y: {odcv_steam_savings}, name: 'Steam', type: 'bar', marker: {{color: '#ffc107'}}}};
    
    const totalSavings = {total_odcv_savings};
    
    // ODCV savings chart - only show fuels with savings
    const odcvSavingsData = [];
    if ({odcv_elec_savings}.some(v => v > 0)) odcvSavingsData.push(odcvElecSave);
    if ({odcv_gas_savings}.some(v => v > 0)) odcvSavingsData.push(odcvGasSave);
    if ({odcv_steam_savings}.some(v => v > 0)) odcvSavingsData.push(odcvSteamSave);
    
    Plotly.newPlot('odcv_savings_chart', odcvSavingsData, {{
        title: {{
            text: 'Monthly ODCV Savings',
            font: {{size: 20}}
        }},
        yaxis: {{
            title: '',
            tickformat: '$,.0f',
            showgrid: false
        }},
        xaxis: {{
            showgrid: false
        }},
        barmode: 'stack',
        font: {{family: 'Arial, sans-serif'}},
        plot_bgcolor: '#ffffff',
        paper_bgcolor: 'white',
        hovermode: 'x unified'
    }}, {{
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
        displaylogo: false,
        displayModeBar: true
    }});

    // Add annual savings caption below the chart
    document.getElementById('odcv_savings_chart').insertAdjacentHTML('afterend', 
        '<div style="text-align: center; margin-top: 10px; font-size: 16px; color: #666;">Annual Savings: $' + totalSavings.toFixed(0).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',') + '</div>'
    );
    
    // PM2.5 Chart - Business Hours Only
    const pm25Data = {{
        x: {json.dumps(chart_dates)},
        y: {json.dumps(chart_values)},
        type: 'scatter',
        mode: 'lines',
        line: {{color: '#0066cc', width: 3}},
        name: 'Daily Average PM2.5',
        hovertemplate: '%{{x|%b %d, %Y}}<br>PM2.5: %{{y:.1f}} μg/m³<extra></extra>'
    }};
    
    // EPA Good threshold line
    const goodThreshold = {{
        x: {json.dumps(chart_dates)},
        y: Array({len(chart_dates)}).fill(12),
        mode: 'lines',
        line: {{color: '#00e400', dash: 'dash', width: 2}},
        name: 'Good AQ Threshold (EPA)',
        hoverinfo: 'skip'
    }};

    Plotly.newPlot('pm25_chart', [pm25Data, goodThreshold], {{
        title: {{
            text: 'Neighborhood PM2.5 Levels ({len(chart_dates) if chart_dates else 0}-Day History)',
            y: 0.95
        }},
        yaxis: {{
            title: 'PM2.5 (μg/m³)',
            showgrid: false,
            zeroline: false,
            range: [0, {max_pm25 * 1.1 if max_pm25 > 0 else 50}]
        }},
        xaxis: {{
            title: '',
            showgrid: false,
            type: 'date',
            tickformat: '%b %d',
            dtick: 86400000 * {max(1, len(chart_dates) // 10) if chart_dates else 3},  // Dynamic tick interval
            tickangle: -45,
            showticklabels: true,
            range: [{json.dumps(chart_dates[0] if chart_dates else '')}, {json.dumps(chart_dates[-1] if chart_dates else '')}]
        }},
        legend: {{
            orientation: 'h',
            x: 0.5,
            xanchor: 'center',
            y: -0.12,
            yanchor: 'top',
            bgcolor: 'transparent',
            borderwidth: 0
        }},
        margin: {{t: 50, r: 50, b: 80, l: 60}},
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        font: {{family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'}},
        hovermode: 'x unified'
    }}, {{
        modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
        displaylogo: false,
        displayModeBar: true
    }});
    
    // Initialize 360° panorama with Manhattan grid logic
    document.addEventListener('DOMContentLoaded', () => {{
        // Manhattan grid even/odd logic for yaw
        function getBuildingYaw(address) {{
            const match = address.match(/\\b(\\d+)/);
            if (!match) return 119;
            
            const buildingNumber = parseInt(match[1]);
            const isEven = buildingNumber % 2 === 0;
            const addressLower = address.toLowerCase();
            
            // Manhattan grid is rotated ~29° clockwise from true north
            const northOffset = -29;  // Was -2.45, now proper grid rotation
            
            if (addressLower.includes('street') || addressLower.includes(' st')) {{
                // STREETS: Even = South side, Odd = North side
                return isEven ? (29 + northOffset) : (209 + northOffset);
            }} else if (addressLower.includes('avenue') || addressLower.includes(' ave')) {{
                // AVENUES: Even = West side, Odd = East side
                return isEven ? (299 + northOffset) : (119 + northOffset);
            }} else if (addressLower.includes('broadway')) {{
                // Broadway runs diagonal
                return isEven ? (330 + northOffset) : (150 + northOffset);
            }}
            
            // Default (assume street)
            return isEven ? (29 + northOffset) : (209 + northOffset);
        }}
        
        // Function to initialize panorama
        function initPanorama() {{
            const viewerEl = document.getElementById('viewer-{bbl}');
            if (!viewerEl || viewerEl._pannellumInitialized) return;
            
            const buildingHeight = {building_height};
            const address = "{main_address}";
            
            // Calculate yaw based on address
            const yaw = getBuildingYaw(address);
            
            // Calculate pitch based on building height
            // We're at street level looking at buildings
            // Based on: 737ft building = 40.10665551348826° pitch (optimal viewing angle)
            // This gives a proportional pitch for all building heights
            const pitch = Math.min(buildingHeight * (40.10665551348826 / 737), 60);  // Max 60° for very tall buildings
            
            console.log(`Panorama {bbl}: Address="${{address}}", Height=${{buildingHeight}}ft, Yaw=${{yaw}}°, Pitch=${{pitch}}°`);
            
            try {{
                const viewer = pannellum.viewer('viewer-{bbl}', {{
                    "type": "equirectangular",
                    "panorama": "https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_360.jpg",
                    "autoLoad": true,
                    "autoRotate": 0,  // Will be started when user navigates to this slide
                    "pitch": pitch,
                    "yaw": yaw,
                    "hfov": 120,
                    "maxHfov": 120,
                    "minHfov": 30,
                    "showZoomCtrl": true,
                    "showFullscreenCtrl": true,
                    "mouseZoom": false,
                    "minPitch": -85,
                    "maxPitch": 90
                }});
                viewerEl._pannellumInitialized = true;
                viewerEl.pannellumViewer = viewer;  // Store viewer instance
                window[`panoramaViewer_{bbl}`] = viewer;  // Also store globally for easy access
                console.log('Panorama initialized successfully for BBL {bbl}');
            }} catch (e) {{
                console.error('Failed to initialize panorama:', e);
            }}
        }}
        
        // Don't initialize immediately - wait for user to navigate to panorama slide
        
        // Reinitialize when carousel shows panorama
        const originalMoveCarousel = window.moveInteractiveCarousel;
        window.moveInteractiveCarousel = function(bbl, direction) {{
            if (originalMoveCarousel) originalMoveCarousel(bbl, direction);
            if (interactiveIndex === 1) {{
                setTimeout(() => {{
                    initPanorama();
                    // Ensure rotation starts after panorama loads
                    setTimeout(() => {{
                        const viewerEl = document.getElementById('viewer-{bbl}');
                        if (viewerEl && viewerEl.pannellumViewer) {{
                            viewerEl.pannellumViewer.startAutoRotate(-2);
                        }}
                    }}, 500);
                }}, 100);
            }}
        }};
    }});
    
    // Tenant table sorting
    let tenantSortDir = {{}};
    function sortTenantTable(col) {{
        // Find the tenant table (there should only be one per page)
        const table = document.querySelector('[id^="tenantTable-"]');
        if (!table) return;
        
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Toggle sort direction
        tenantSortDir[col] = !tenantSortDir[col];
        
        rows.sort((a, b) => {{
            let aVal, bVal;
            
            if (col === 3) {{
                // SF Occupied - parse number from formatted string
                aVal = parseInt(a.cells[col].textContent.replace(/,/g, '') || '0');
                bVal = parseInt(b.cells[col].textContent.replace(/,/g, '') || '0');
            }} else if (col === 4 || col === 5) {{
                // Dates - convert to sortable format
                aVal = a.cells[col].textContent.trim();
                bVal = b.cells[col].textContent.trim();
                // Handle N/A values
                if (aVal === 'N/A') aVal = '';
                if (bVal === 'N/A') bVal = '';
                // Convert Mon-YY to YYYY-MM for sorting
                if (aVal && aVal !== 'N/A') {{
                    const [month, year] = aVal.split('-');
                    const monthNum = new Date(month + ' 1, 2000').getMonth() + 1;
                    aVal = `20${{year}}-${{monthNum.toString().padStart(2, '0')}}`;
                }}
                if (bVal && bVal !== 'N/A') {{
                    const [month, year] = bVal.split('-');
                    const monthNum = new Date(month + ' 1, 2000').getMonth() + 1;
                    bVal = `20${{year}}-${{monthNum.toString().padStart(2, '0')}}`;
                }}
            }} else {{
                // Text columns (Tenant, Industry, Floor)
                aVal = a.cells[col].textContent.toLowerCase().trim();
                bVal = b.cells[col].textContent.toLowerCase().trim();
            }}
            
            if (tenantSortDir[col]) {{
                return aVal > bVal ? 1 : -1;
            }} else {{
                return aVal < bVal ? 1 : -1;
            }}
        }});
        
        // Clear and rebuild tbody
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
        
        // Update sort indicators
        const headers = table.querySelectorAll('th');
        headers.forEach((th, idx) => {{
            const indicator = th.querySelector('.sort-indicator');
            if (indicator) {{
                indicator.textContent = idx === col ? (tenantSortDir[col] ? '↑' : '↓') : '↕';
            }}
        }});
    }}
    
    </script>
    </div>
    
    <div style="text-align: center; color: black; font-size: 14px; padding: 20px 0; font-family: 'Inter', sans-serif;">
        Build: {datetime.now(pytz.timezone('America/Mexico_City')).strftime('%I:%M:%S %p CST')}{' | ' + sys.argv[1] if len(sys.argv) > 1 else ''}
    </div>
</body>
</html>
"""
    
            # Save it
            with open(f"{bbl}.html", 'w') as f:
                f.write(html)
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"✓ Created {i + 1} building pages...")
    
    except KeyError as e:
        print(f"⚠️  Missing column for {bbl}: {e}")
        continue
    except Exception as e:
        print(f"❌ Error processing {bbl}: {e}")
        import traceback
        traceback.print_exc()
        continue

print("✓ All building pages done!")