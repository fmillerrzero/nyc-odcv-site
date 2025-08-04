import pandas as pd
from datetime import datetime
import pytz
import sys
from html import escape

# Read what we need
scoring = pd.read_csv('data/odcv_scoring.csv')
buildings = pd.read_csv('data/buildings_BIG.csv')
ll97 = pd.read_csv('data/LL97_BIG.csv')
addresses = pd.read_csv('data/all_building_addresses.csv')
system = pd.read_csv('data/system_BIG.csv')

# Read aerial videos data
aerial_videos = {}
try:
    aerial_df = pd.read_csv('data/aerial_videos.csv')
    for _, row in aerial_df.iterrows():
        if row['status'] == 'active' and pd.notna(row['video_id']):
            aerial_videos[int(row['bbl'])] = row['video_id']
    print(f"Loaded {len(aerial_videos)} aerial videos")
except:
    print("No aerial videos file found")

# Logo mapping and escaping functions
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

def attr_escape(text):
    if pd.isna(text):
        return ""
    return escape(str(text)).replace('"', '&quot;').replace("'", '&#39;')

# Calculate stats
total_odcv_savings = scoring['Total_ODCV_Savings_Annual_USD'].sum()
total_penalties_2026 = ll97['penalty_2026_dollars'].sum()
total_savings = total_odcv_savings + total_penalties_2026  # ODCV + penalty avoidance
total_buildings = len(scoring)
urgent = len(ll97[ll97['penalty_2026_dollars'] > 0])
bas_yes = len(system[system['Has Building Automation'] == 'yes'])

# Make the HTML
html = f"""<!DOCTYPE html>
<html>
<head>
    <title>NYC ODCV Opportunity Rankings | R-Zero</title>
    <link rel="icon" type="image/png" href="https://rzero.com/wp-content/themes/rzero/build/images/favicons/favicon.png">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="description" content="NYC building ODCV savings rankings - 585 buildings analyzed for energy efficiency opportunities">
    <meta name="keywords" content="ODCV, NYC buildings, energy efficiency, LL97 compliance, building automation">
    <style>
        :root {{
            --rzero-primary: #0066cc;
            --rzero-primary-dark: #0052a3;
            --rzero-light-blue: #f0f7fa;
            --rzero-background: #ffffff;
        }}
        
        body {{ 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #ffffff; 
        }}
        
        .container {{ max-width: 1400px; margin: 0 auto; padding: 0 7.5%; }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 118, 157, 0.08);
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .logo-header {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        h1 {{ 
            color: var(--rzero-primary); 
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
        }}
        
        .subtitle {{ 
            color: #666; 
            margin: 10px 0 0 0;
            font-size: 1.1em;
        }}
        
        .stats {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }}
        
        .stat {{ text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
        .stat-card {{ padding: 15px; }}
        .stat-value {{ font-size: 1.8em; font-weight: bold; color: var(--rzero-primary); }}
        .stat-label {{ font-size: 0.9em; color: #666; }}
        .big {{ font-size: 2.5em; font-weight: bold; color: var(--rzero-primary); }}
        
        .clickable-link {{ color: var(--rzero-primary); text-decoration: none; cursor: pointer; }}
        .clickable-link:hover {{ text-decoration: underline; }}
        .portfolio-box {{ 
            background: white;
            border: 1px solid rgba(0, 118, 157, 0.2);
            padding: 30px; 
            border-radius: 12px; 
            margin-bottom: 30px; 
        }}
        
        .portfolio-box h2 {{ 
            color: var(--rzero-primary); 
            margin-top: 0; 
        }}
        
        .portfolio-tile:not(.selected):hover {{
            background-color: rgba(0, 118, 157, 0.08) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 118, 157, 0.2);
        }}
        
        .portfolio-tile.selected {{
            background-color: rgba(0, 118, 157, 0.15) !important;
            border: 3px solid var(--rzero-primary) !important;
            box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.3), 0 8px 20px rgba(0, 118, 157, 0.4) !important;
            transform: translateY(-3px) scale(1.02);
            position: relative;
        }}
        
        /* Aggressively prevent any checkmarks */
        .portfolio-tile.selected::after,
        .portfolio-tile.selected::before,
        .portfolio-tile::after,
        .portfolio-tile::before,
        .portfolio-tile *::after,
        .portfolio-tile *::before {{
            display: none !important;
            content: none !important;
            visibility: hidden !important;
        }}
        
        /* Enhanced Savings Styling from Prospector */
        .savings-high {{
            color: #1b5e20;
            font-weight: 700;
            position: relative;
        }}
        
        .savings-high::before {{
            content: '★';
            position: absolute;
            left: -15px;
            color: #ffc107;
        }}
        
        .savings-medium {{
            color: #f57c00;
            font-weight: 600;
        }}
        
        .savings-low {{
            color: #616161;
        }}
        
        tr:nth-child(-n+10) .savings-high {{
            background: linear-gradient(90deg, transparent 0%, rgba(76, 175, 80, 0.1) 50%, transparent 100%);
            padding: 4px 8px;
            border-radius: 4px;
        }}
        
        .clickable-row {{ cursor: pointer; }}
        .clickable-row:hover {{ background-color: rgba(0, 118, 157, 0.05); }}
        .rzero-badge {{ display: inline-block; background: var(--rzero-primary); color: white; padding: 3px 8px; border-radius: 20px; font-size: 0.75em; font-weight: 600; }}
        
        /* Enhanced styling from Prospector */
        .info-box {{ 
            background: #f8f8f8;
            border: 1px solid #ddd;
            padding: 15px; 
            margin-bottom: 20px;
            border-radius: 8px;
        }}
        
        .info-box h2 {{ 
            color: var(--rzero-primary); 
            margin-top: 0; 
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        details summary {{
            list-style: none;
            cursor: pointer;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        details summary::-webkit-details-marker {{
            display: none;
        }}

        details[open] summary span:last-child {{
            transform: rotate(180deg);
            display: inline-block;
        }}

        details summary span:last-child {{
            transition: transform 0.3s ease;
            display: inline-block;
        }}
        
        .portfolio-box {{ 
            background: white;
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        .table-wrapper::-webkit-scrollbar {{ width: 12px; }}
        .table-wrapper::-webkit-scrollbar-track {{ background: #f1f1f1; border-radius: 6px; }}
        .table-wrapper::-webkit-scrollbar-thumb {{ background: var(--rzero-primary); border-radius: 6px; }}
        .table-wrapper::-webkit-scrollbar-thumb:hover {{ background: var(--rzero-primary-dark); }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; vertical-align: middle; }}
        tbody tr:hover {{ background: rgba(0, 118, 157, 0.02); transition: background 0.2s ease; }}
        
        table {{ 
            width: 100%; 
            background: white; 
            border-collapse: collapse; 
            box-shadow: 0 4px 20px rgba(0, 118, 157, 0.08);
            border-radius: 12px;
            overflow: hidden;
        }}
        
        th {{ 
            background: var(--rzero-primary); 
            color: white; 
            padding: 10px 8px; 
            text-align: left; 
            cursor: pointer; 
            font-weight: 600;
        }}
        
        th:hover {{ background: var(--rzero-primary-dark); }}
        .thumb-cell {{ width: 80px; padding: 5px !important; text-align: center; }}
        tr:nth-child(even) {{ background-color: rgba(0, 118, 157, 0.01); }}
        
        @media (max-width: 768px) {{
            .stats {{ grid-template-columns: 1fr; }}
            .container {{ padding: 0 5%; }}
            th {{ font-size: 12px; padding: 8px 4px; }}
            td {{ font-size: 12px; padding: 6px 4px; }}
            .portfolio-tile {{ min-height: 80px !important; }}
            #backToTop {{ bottom: 20px; right: 20px; }}
        }}
        
        /* Hide sort indicators by default */
        .sort-indicator {{ opacity: 0.5; }}
        th:hover .sort-indicator {{ opacity: 1; }}
        
        td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f5f5f5; }}
        a {{ color: var(--rzero-primary); text-decoration: none; font-weight: 500; }}
        a:hover {{ text-decoration: underline; }}
        .building-thumb {{ width: 70px; height: 70px; object-fit: cover; border-radius: 8px; cursor: pointer; }}
        .no-thumb {{ 
            width: 70px; 
            height: 70px; 
            background: #f8f9fa; 
            border: 1px solid rgba(0, 118, 157, 0.2);
            border-radius: 8px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: #999;
            font-size: 10px;
            text-align: center;
        }}
        
        @media print {{
            .header {{ background: white !important; box-shadow: none !important; }}
            .portfolio-box, #occupancyChartSlim, #backToTop, button {{ display: none !important; }}
            .table-wrapper {{ max-height: none !important; overflow: visible !important; }}
            table {{ box-shadow: none !important; }}
            th {{ background: #f0f0f0 !important; color: black !important; }}
            a {{ color: black !important; text-decoration: none !important; }}
            .building-thumb {{ max-width: 50px !important; max-height: 50px !important; }}
        }}
        
        .yes {{ color: #38a169; font-weight: bold; }}
        .no {{ color: #c41e3a; font-weight: bold; }}
        .urgent {{ color: #c41e3a; font-weight: bold; }}
        .bas {{ color: #38a169; font-weight: 600; }}
        .no-bas {{ color: #c41e3a; font-weight: 600; }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-header">
                <a href="https://rzero.com" target="_blank">
                    <img src="https://rzero.com/wp-content/uploads/2021/10/rzero-logo-pad.svg" alt="R-Zero Logo" style="width: 200px; height: 50px;">
                </a>
            </div>
            <h1>Prospector: NYC</h1>
            <p class="subtitle">ODCV Opportunity Rankings</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" style="color: #2e7d32;">${total_savings/1000000:.1f}M</div>
                <div class="stat-label">Year One Savings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #c41e3a;">{urgent}</div>
                <div class="stat-label">Buildings facing ${total_penalties_2026/1000000:.1f}M 2026 LL97 Penalties</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{bas_yes}</div>
                <div class="stat-label">Buildings with BMS</div>
            </div>
        </div>
        
"""

# Add portfolio section
owner_counts = buildings['ownername'].value_counts().head(3)
portfolio_html = '''
        <div class="portfolio-box">
            <h2>Top Portfolios</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
'''

for owner, count in owner_counts.items():
    if pd.notna(owner):  # Skip NaN owners
        # Get total savings for this owner
        owner_bbls = buildings[buildings['ownername'] == owner]['bbl']
        total = scoring[scoring['bbl'].isin(owner_bbls)]['Total_ODCV_Savings_Annual_USD'].sum()
        
        # Get penalty avoidance too
        penalty_avoid = ll97[ll97['bbl'].isin(owner_bbls)]['penalty_2026_dollars'].sum()
        total_with_penalty = total + penalty_avoid
        
        logo_file = find_logo_file(owner)
        if logo_file:
            # Special styling for Vornado logo - matching the working version sizes
            logo_style = (
                "position: absolute; top: 10px; right: 15px; max-height: 60px; max-width: 120px; opacity: 0.8;"
                if "Vornado" in owner else
                "position: absolute; top: 15px; right: 15px; max-height: 40px; max-width: 80px; opacity: 0.8;"
            )
            logo_html = f'<img src="https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/Logos/{logo_file}" alt="{escape(owner)}" style="{logo_style}">'
        else:
            logo_html = ''
        
        portfolio_html += f'''                <div class="portfolio-tile" onclick="filterByOwner('{escape(owner).replace("'", "\\'")}')" style="background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid rgba(0, 118, 157, 0.2); cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; min-height: 100px;">
                    {logo_html}
                    <strong style="color: var(--rzero-primary); display: block; margin-bottom: 5px;">{escape(owner)}</strong>
                    <span style="color: #666;">{count} buildings • ${total_with_penalty/1000000:.1f}M savings</span>
                </div>
'''

portfolio_html += '''            </div>
        </div>
'''

html += f"""
        {portfolio_html}
        
        <div style="background: #f8f8f8; border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 8px;">
            <details>
                <summary style="cursor: pointer; font-size: 1.5em; color: var(--rzero-primary); font-weight: 600; padding: 10px 0; list-style: none;">
                    NYC Office Occupancy <span style="font-size: 0.8em; transition: transform 0.3s; display: inline-block;">▼</span>
                </summary>
                <div style="margin-top: 15px;">
                    <div style="display: flex; gap: 25px; font-size: 0.95em; margin-bottom: 20px; justify-content: center;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <div style="width: 20px; height: 3px; background: #5B6FED; border-radius: 2px;"></div>
                            <span>NYC: <strong>76%</strong></span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <div style="width: 20px; height: 3px; background: #FF6B6B; border-radius: 2px;"></div>
                            <span>US Avg: <strong>66%</strong></span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <div style="width: 20px; height: 3px; background: #4ECDC4; border-radius: 2px;"></div>
                            <span>SF: <strong>47%</strong></span>
                        </div>
                    </div>
                    <div style="height: 220px; position: relative;">
                        <canvas id="occupancyChartSlim"></canvas>
                    </div>
                </div>
            </details>
        </div>
        
        <div style="background: #f8f8f8; border: 1px solid #ddd; padding: 15px; margin-bottom: 20px;">
            <details>
                <summary style="cursor: pointer; font-size: 1.5em; color: var(--rzero-primary); font-weight: 600; padding: 10px 0;">
                    Behind the Rankings <span style="font-size: 0.8em; transition: transform 0.3s; display: inline-block;">▼</span>
                </summary>
                <div style="margin-top: 15px;">
                    <p>Buildings are ranked by <strong>SALES READINESS</strong>, not just savings amount. The scoring system (110 points total):</p>
                    <ul style="line-height: 1.8;">
                        <li><strong>Financial Impact (40 pts):</strong> ODCV savings & LL97 penalty avoidance</li>
                        <li><strong>BAS Infrastructure (30 pts):</strong> No BAS = 0 points (major barrier to sale)</li>
                        <li><strong>Owner Portfolio (20 pts):</strong> Large portfolios score higher (one pitch → multiple buildings)</li>
                        <li><strong>Implementation Ease (10 pts):</strong> Fewer tenants + larger floors = easier installation</li>
                        <li><strong>Prestige Factors (10 pts):</strong> LEED certification, Energy Star ambitions, Class A buildings</li>
                    </ul>
                    <p style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 15px; border: 1px solid #ffeeba;">
                        <strong>Example:</strong> A building with $1.4M savings but no BAS ranks #123, while a $539K building with perfect infrastructure ranks #1. Focus on the ready buyers!
                    </p>
                </div>
            </details>
        </div>
        
        <div style="display: flex; gap: 10px; margin-bottom: 20px; align-items: center;">
            <input type="text" id="search" onkeyup="filterTable()" placeholder="Search by address, owner, property manager" style="flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
            <button id="clearFilterBtn" onclick="clearAllFilters()" style="background: #e0e0e0; color: #999; border: none; padding: 10px 25px; border-radius: 8px; cursor: not-allowed; font-size: 16px; font-weight: 600; transition: all 0.2s;" disabled>
                Clear Filter
            </button>
            <button onclick="exportToCSV()" style="background: #38a169; color: white; border: none; padding: 10px 25px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600;">
                Export CSV
            </button>
        </div>
        
        <div id="resultCounter" style="background: #f8f9fa; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; color: #666;">
            Showing <span id="visibleCount">{total_buildings}</span> of <span id="totalCount">{total_buildings}</span> buildings
        </div>
        
        <div class="table-wrapper" style="overflow-x: auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 118, 157, 0.08); position: relative; max-height: calc(100vh - 200px); overflow-y: auto;">
        <table id="buildingTable" style="width: 100%; background: white; border-collapse: collapse; min-width: 900px;">
        <thead style="position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
        <tr>
            <th class="thumb-cell">Image</th>
            <th onclick="sortTable(1)" style="cursor: pointer;">Rank <span class="sort-indicator">↕</span></th>
            <th onclick="sortTable(2)" style="cursor: pointer;">Building <span class="sort-indicator">↕</span></th>
            <th onclick="sortTable(3)" style="cursor: pointer;">Owner <span class="sort-indicator">↕</span></th>
            <th onclick="sortTable(4)" style="cursor: pointer;">Manager <span class="sort-indicator">↕</span></th>
            <th onclick="sortTable(5)" style="cursor: pointer;">2026 ODCV Savings <span class="sort-indicator">↕</span></th>
            <th onclick="sortTable(6)" style="cursor: pointer;">Score <span class="sort-indicator">↕</span></th>
            <th>Details</th>
        </tr>
        </thead>
        <tbody>
"""

# Add each building
for i, row in scoring.iterrows():
    bbl = row['bbl']
    
    # Get all addresses for search
    address_info = addresses[addresses['bbl'] == bbl]
    if not address_info.empty:
        # Build search text with all addresses
        search_terms = []
        main_address = address_info.iloc[0]['main_address']
        search_terms.append(str(main_address).lower())
        
        # Add all alternate addresses
        for col in address_info.columns:
            if col.startswith('alternate_address_') and not col.endswith('_range'):
                alt_addr = address_info.iloc[0][col]
                if pd.notna(alt_addr) and alt_addr:
                    search_terms.append(str(alt_addr).lower())
        
        address = main_address
    else:
        address = row['address']
        search_terms = [str(address).lower()]
    
    # Get building info with proper error handling
    building_info = buildings[buildings['bbl'] == bbl]
    if not building_info.empty:
        owner = building_info.iloc[0]['ownername'] if pd.notna(building_info.iloc[0]['ownername']) else 'Unknown'
        manager = building_info.iloc[0].get('property_manager', 'Unknown')
        if pd.isna(manager):
            manager = 'Unknown'
    else:
        owner = 'Unknown'
        manager = 'Unknown'
    
    # Get penalty data safely
    penalty_info = ll97[ll97['bbl'] == bbl]
    penalty_2026 = penalty_info.iloc[0]['penalty_2026_dollars'] if not penalty_info.empty else 0
    
    # Add owner, manager, BBL to search terms
    search_terms.append(str(owner).lower())
    search_terms.append(str(manager).lower())
    search_terms.append(str(bbl))
    
    # Also add the owner without "Realty" or "Trust" for easier searching
    owner_simple = owner.replace(' Realty Trust', '').replace(' Realty', '').replace(' Trust', '')
    search_terms.append(owner_simple.lower())
    
    search_text = ' | '.join(search_terms)
    
    # GitHub thumbnail URL
    thumb_url = f"https://raw.githubusercontent.com/fmillerrzero/nyc-odcv-site/main/images/{bbl}/{bbl}_hero_thumbnail.jpg"
    thumb = f'''<img src="{thumb_url}" 
                     alt="{address.split(",")[0]}" 
                     class="building-thumb" 
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
                     onclick="window.location.href='{bbl}.html'">
                <div class="no-thumb" style="display:none;" onclick="window.location.href='{bbl}.html'">No image</div>'''
    
    # Get penalty for this building
    ll97_data = ll97[ll97['bbl'] == bbl]
    penalty_2026 = ll97_data['penalty_2026_dollars'].iloc[0] if not ll97_data.empty else 0
    
    # Calculate combined savings (ODCV + penalty avoidance) - same as building report banner
    odcv_savings = row['Total_ODCV_Savings_Annual_USD']
    savings = odcv_savings + penalty_2026  # Combined total
    if savings >= 500000:
        savings_class = 'savings-high'
    elif savings >= 100000:
        savings_class = 'savings-medium'
    else:
        savings_class = 'savings-low'
    
    # Add rank badge for top 10
    rank = int(row['final_rank'])
    if rank <= 10:
        rank_display = f'<span class="rzero-badge">#{rank}</span>'
    else:
        rank_display = str(rank)
    
    html += f"""
        <tr data-search="{search_text.replace('"', '&quot;')}" data-occupancy="70" class="clickable-row" onclick="if (!event.target.closest('a')) window.location.href='{bbl}.html'">
            <td>{thumb}</td>
            <td>{rank_display}</td>
            <td>{address.split(',')[0]}</td>
            <td><a href="javascript:void(0)" onclick="event.stopPropagation(); filterByOwner('{owner.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"')}')" class="clickable-link">{owner}</a></td>
            <td><a href="javascript:void(0)" onclick="event.stopPropagation(); filterByManager('{manager.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"')}')" class="clickable-link">{manager}</a></td>
            <td class="{savings_class}" data-value="{savings}">${savings:,.0f}</td>
            <td>{row['total_score']:.1f}</td>
            <td style="text-align: center;">
                <span style="color: var(--rzero-primary);">→</span>
            </td>
        </tr>
    """

html += """
        </tbody>
        </table>
        </div>
    </div>
    
    <script>
    // Global variable to track filter state
    var activeOwnerFilter = null;
    
    // Define filter functions early so they're available for onclick handlers
    function filterByOwner(ownerName) {
        // Check if this owner is already selected
        const isAlreadySelected = activeOwnerFilter === ownerName;
        
        if (isAlreadySelected) {
            // Unselect: clear filter and show all buildings
            activeOwnerFilter = null;
            
            // Clear search bar
            document.getElementById('search').value = '';
            
            // Remove selection styling
            document.querySelectorAll('.portfolio-tile').forEach(tile => {
                tile.classList.remove('selected');
            });
            
            // Show all rows
            const rows = document.querySelectorAll('#buildingTable tbody tr');
            rows.forEach(row => {
                row.style.display = '';
            });
            updateResultCounter(rows.length);
        } else {
            // Select: apply filter
            activeOwnerFilter = ownerName;
            
            // Populate search bar with owner name
            document.getElementById('search').value = ownerName;
            
            // Remove previous selection styling
            document.querySelectorAll('.portfolio-tile').forEach(tile => {
                tile.classList.remove('selected');
            });
            
            // Add selection styling to clicked tile
            document.querySelectorAll('.portfolio-tile').forEach(tile => {
                if (tile.querySelector('strong') && tile.querySelector('strong').textContent === ownerName) {
                    tile.classList.add('selected');
                }
            });
            
            // Filter rows
            const rows = document.querySelectorAll('#buildingTable tbody tr');
            let visibleCount = 0;
            rows.forEach(row => {
                const ownerCell = row.cells[3];
                const isMatch = ownerCell && ownerCell.textContent.trim() === ownerName;
                row.style.display = isMatch ? '' : 'none';
                if (isMatch) visibleCount++;
            });
            updateResultCounter(visibleCount);
        }
        
        updateClearButtonState();
    }
    
    function filterByManager(managerName) {
        // Update active filter to track manager filters too
        activeOwnerFilter = managerName;
        
        // Populate search bar with manager name
        document.getElementById('search').value = managerName;
        
        // Remove active styling from portfolio tiles
        document.querySelectorAll('.portfolio-tile').forEach(tile => {
            tile.classList.remove('selected');
        });
        
        const rows = document.querySelectorAll('#buildingTable tbody tr');
        let visibleCount = 0;
        rows.forEach(row => {
            const managerCell = row.cells[4];
            const isMatch = managerCell && managerCell.textContent.trim() === managerName;
            row.style.display = isMatch ? '' : 'none';
            if (isMatch) visibleCount++;
        });
        updateResultCounter(visibleCount);
        updateClearButtonState();
    }
    
    // Search functionality
    function filterTable() {
        const input = document.getElementById('search').value.toLowerCase();
        const rows = document.querySelectorAll('#buildingTable tbody tr');
        let visibleCount = 0;
        
        rows.forEach(row => {
            const searchText = row.getAttribute('data-search');
            const matchesSearch = searchText && searchText.includes(input);
            row.style.display = matchesSearch ? '' : 'none';
            if (matchesSearch) visibleCount++;
        });
        
        updateResultCounter(visibleCount);
        updateClearButtonState();
    }
    
    // Update result counter
    function updateResultCounter(count) {
        document.getElementById('visibleCount').textContent = count;
    }
    
    function updateClearButtonState() {
        const btn = document.getElementById('clearFilterBtn');
        const searchBox = document.getElementById('search');
        const hasActiveFilter = (searchBox.value.trim() !== '') || (activeOwnerFilter !== null);
        
        if (hasActiveFilter) {
            btn.disabled = false;
            btn.style.background = '#c41e3a';
            btn.style.color = 'white';
            btn.style.cursor = 'pointer';
            btn.onmouseover = function() { this.style.background='#a01729'; };
            btn.onmouseout = function() { this.style.background='#c41e3a'; };
        } else {
            btn.disabled = true;
            btn.style.background = '#e0e0e0';
            btn.style.color = '#999';
            btn.style.cursor = 'not-allowed';
            btn.onmouseover = null;
            btn.onmouseout = null;
        }
    }
    
    function clearAllFilters() {
        // Clear search box
        document.getElementById('search').value = '';
        
        // Reset active filter
        activeOwnerFilter = null;
        
        // Show all rows
        const rows = document.querySelectorAll('#buildingTable tbody tr');
        rows.forEach(row => {
            row.style.display = '';
        });
        
        // Remove active styling from portfolio tiles
        document.querySelectorAll('.portfolio-tile').forEach(tile => {
            tile.classList.remove('selected');
        });
        
        // Update result counter
        updateResultCounter(rows.length);
        
        // Update button state
        updateClearButtonState();
    }
    
    // Helper to escape quotes in JavaScript strings
    function jsEscape(str) {
        return str.replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'").replace(/"/g, '\\\\"');
    }
    
    // Export to CSV functionality
    function exportToCSV() {
        const table = document.getElementById('buildingTable');
        const rows = Array.from(table.querySelectorAll('tbody tr')).filter(row => row.style.display !== 'none');
        
        let csv = 'Rank,Building,Owner,Manager,2026 ODCV Savings,Score\\n';
        
        rows.forEach(row => {
            const cells = row.cells;
            const rank = cells[1].textContent.replace('#', '');
            const building = cells[2].textContent;
            const owner = cells[3].textContent;
            const manager = cells[4].textContent;
            const savings = cells[5].getAttribute('data-value');
            const score = cells[6].textContent;
            
            csv += `"${rank}","${building}","${owner}","${manager}","${savings}","${score}"\n`;
        });
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'nyc_odcv_rankings.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    
    // Sortable table functionality
    let sortDir = {};
    function sortTable(col) {
        const tbody = document.querySelector('#buildingTable tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        sortDir[col] = !sortDir[col];
        
        rows.sort((a, b) => {
            let aVal, bVal;
            
            // Use data-value for savings column
            if (col === 5) {
                aVal = parseFloat(a.cells[col].getAttribute('data-value') || 0);
                bVal = parseFloat(b.cells[col].getAttribute('data-value') || 0);
            } else if (col === 1 || col === 6) {
                // Numeric columns
                aVal = parseFloat(a.cells[col].textContent.replace(/[#$,]/g, '') || 0);
                bVal = parseFloat(b.cells[col].textContent.replace(/[#$,]/g, '') || 0);
            } else {
                // Text columns
                aVal = (a.cells[col].textContent || '').toLowerCase();
                bVal = (b.cells[col].textContent || '').toLowerCase();
            }
            
            if (sortDir[col]) {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });
        
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
        
        // Update header arrows
        document.querySelectorAll('th').forEach((th, idx) => {
            if (idx > 0 && idx < 7) {
                th.innerHTML = th.innerHTML.replace(/[↑↓↕]/g, idx === col ? (sortDir[col] ? '↑' : '↓') : '↕');
            }
        });
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        updateClearButtonState();
        
        // Initialize any portfolio tiles that might be pre-selected
        const urlParams = new URLSearchParams(window.location.search);
        const ownerParam = urlParams.get('owner');
        if (ownerParam) {
            filterByOwner(ownerParam);
        }
        
        // Initialize occupancy chart
        const ctx = document.getElementById('occupancyChartSlim').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan 20', 'Jul 20', 'Jan 21', 'Jul 21', 'Jan 22', 'Jul 22', 'Jan 23', 'Jul 23', 'Jan 24', 'Jul 24', 'Jan 25', 'Jun 25'],
                datasets: [{
                    label: 'NYC',
                    data: [100, 17, 18, 31, 30, 53, 55, 64, 66, 74, 75, 76],
                    borderColor: '#5B6FED',
                    backgroundColor: '#5B6FED',
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5
                }, {
                    label: 'National',
                    data: [100, 18, 18, 32, 32, 49, 51, 60, 62, 69, 70, 66],
                    borderColor: '#FF6B6B',
                    backgroundColor: '#FF6B6B',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5
                }, {
                    label: 'SF',
                    data: [100, 13, 10, 18, 20, 32, 34, 42, 44, 48, 49, 47],
                    borderColor: '#4ECDC4',
                    backgroundColor: '#4ECDC4',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#ddd',
                        borderWidth: 1,
                        cornerRadius: 4,
                        padding: 8,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 11
                            }
                        }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        ticks: {
                            stepSize: 25,
                            callback: function(value) {
                                return value + '%';
                            },
                            font: {
                                size: 11
                            },
                            color: '#666'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    });
    
    // Back to top functionality
    function scrollToTop() {
        window.scrollTo({top: 0, behavior: 'smooth'});
    }
    
    // Show/hide back to top button
    window.onscroll = function() {
        const btn = document.getElementById('backToTop');
        if (document.body.scrollTop > 200 || document.documentElement.scrollTop > 200) {
            btn.style.display = 'block';
        } else {
            btn.style.display = 'none';
        }
    };
    
    
    // Fetch ALL aerial video URLs and store in sessionStorage
    async function fetchAllAerialVideos() {
        const API_KEY = 'AIzaSyDQdR4xY0a_qmEsYairsp6r6tXwh5qx_ho';
        console.log('Fetching all aerial video URLs...');
        
        // Complete mapping from aerial_videos.csv
        const aerialVideos = {"""

# Add all the aerial videos from the Python data
for bbl, video_id in aerial_videos.items():
    html += f"""
            {bbl}: '{video_id}',"""

html = html.rstrip(',')  # Remove trailing comma
html += """
        };
        
        const videoUrls = {};
        const entries = Object.entries(aerialVideos);
        console.log(`Fetching ${entries.length} video URLs...`);
        
        // Process in batches to avoid overwhelming the API
        const batchSize = 10;
        for (let i = 0; i < entries.length; i += batchSize) {
            const batch = entries.slice(i, i + batchSize);
            
            await Promise.all(batch.map(async ([bbl, videoId]) => {
                try {
                    const response = await fetch(`https://aerialview.googleapis.com/v1/videos:lookupVideo?key=${API_KEY}&videoId=${videoId}`);
                    const data = await response.json();
                    
                    if (data.state === 'ACTIVE' && data.uris) {
                        const videoUri = data.uris.MP4_HIGH?.landscapeUri || 
                                       data.uris.MP4_HIGH?.portraitUri || 
                                       data.uris.MP4_MEDIUM?.landscapeUri;
                        
                        if (videoUri) {
                            videoUrls[bbl] = videoUri;
                            console.log(`Fetched video URL for BBL ${bbl}`);
                        }
                    }
                } catch (error) {
                    console.error(`Failed to fetch video for BBL ${bbl}:`, error);
                }
            }));
            
            // Small delay between batches
            if (i + batchSize < entries.length) {
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }
        
        // Store in sessionStorage
        sessionStorage.setItem('aerialVideoUrls', JSON.stringify(videoUrls));
        console.log(`Stored ${Object.keys(videoUrls).length} video URLs in sessionStorage`);
    }
    
    // Call on page load
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(fetchAllAerialVideos, 1000);
    });
    </script>
    
    <!-- Back to Top Button -->
    <button id="backToTop" onclick="scrollToTop()" style="
        position: fixed;
        bottom: 80px;
        right: 30px;
        width: 50px;
        height: 50px;
        background: var(--rzero-primary);
        color: white;
        border: none;
        border-radius: 50%;
        font-size: 20px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 1000;
        display: none;
    ">
        <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24">
            <path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/>
        </svg>
    </button>
    
    <div style="text-align: center; color: black; font-size: 14px; padding: 20px 0;">
        Build: {datetime.now(pytz.timezone('America/Mexico_City')).strftime('%I:%M:%S %p CST')}{' | ' + sys.argv[1] if len(sys.argv) > 1 else ''}
    </div>
</body>
</html>
"""

# Ensure all required data is loaded
print(f"✓ Loaded {len(scoring)} buildings from scoring")
print(f"✓ Loaded {len(buildings)} buildings from buildings_BIG")
print(f"✓ Loaded {len(ll97)} buildings from LL97")
print(f"✓ Loaded {len(system)} buildings from system_BIG")
print(f"✓ Total savings: ${total_savings/1000000:.1f}M")
print(f"✓ Buildings with BMS: {bas_yes}")
print(f"✓ Homepage done!")

# Save it
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✓ Homepage saved to index.html")
print(f"✓ Ready to deploy to GitHub!")