import pandas as pd

# Read the existing links CSV and scoring CSV
links_df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv')
scoring_df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/odcv_scoring.csv')
buildings_df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/buildings_BIG.csv')

# Get list of BBLs already in links file
existing_bbls = set(links_df['bbl'].tolist())

# Create a mapping of BBL to building info
bbl_to_info = {}
for _, row in buildings_df.iterrows():
    bbl_to_info[row['bbl']] = {
        'address': row['address'],
        'owner': row['ownername']
    }

# Start from the last rank in the existing file
last_rank = len(links_df)

# Add missing buildings from scoring file
new_rows = []
for _, row in scoring_df.iterrows():
    bbl = row['bbl']
    if bbl not in existing_bbls:
        rank = last_rank + 1
        last_rank = rank
        
        # Get address and owner from buildings_df
        if bbl in bbl_to_info:
            address = bbl_to_info[bbl]['address']
            owner = bbl_to_info[bbl]['owner']
        else:
            # Fallback to scoring data if not in buildings
            address = row.get('address', '')
            owner = row.get('ownername', '')
        
        new_row = {
            'rank': float(rank),
            'bbl': bbl,
            'address': address,
            'owner': owner,
            'url': '',  # Empty for now
            'source': ''  # Empty for now
        }
        new_rows.append(new_row)

# Create new dataframe with additional rows
new_df = pd.DataFrame(new_rows)

# Concatenate with existing dataframe
final_df = pd.concat([links_df, new_df], ignore_index=True)

# Save the updated CSV
final_df.to_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv', index=False)

print(f"Added {len(new_rows)} buildings to the CSV")
print(f"Total buildings now: {len(final_df)}")
print(f"First 5 new entries:")
for i in range(min(5, len(new_rows))):
    print(f"  Rank {new_rows[i]['rank']}: {new_rows[i]['address']} - {new_rows[i]['owner']}")