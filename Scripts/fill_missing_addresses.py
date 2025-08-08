import pandas as pd

# Read both CSV files
links_df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv')
buildings_df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/buildings_BIG.csv')

# Create a dictionary of BBL to address from buildings data
bbl_to_address = {}
for _, row in buildings_df.iterrows():
    bbl_to_address[row['bbl']] = row['address']

# Fill in missing addresses
count = 0
for idx, row in links_df.iterrows():
    if pd.isna(row['address']) or row['address'] == '':
        bbl = row['bbl']
        if bbl in bbl_to_address:
            links_df.at[idx, 'address'] = bbl_to_address[bbl]
            print(f"Filled address for BBL {bbl}: {bbl_to_address[bbl]}")
            count += 1

# Save the updated CSV
links_df.to_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv', index=False)
print(f"\nCSV file has been updated with {count} missing addresses.")