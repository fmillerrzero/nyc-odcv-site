import pandas as pd

# Read both CSV files
links_df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv')
buildings_df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/buildings_BIG.csv')

# Create a dictionary of BBL to owner from buildings data
bbl_to_owner = {}
for _, row in buildings_df.iterrows():
    bbl_to_owner[row['bbl']] = row['ownername']

# Fill in missing owners
for idx, row in links_df.iterrows():
    if pd.isna(row['owner']) or row['owner'] == '':
        bbl = row['bbl']
        if bbl in bbl_to_owner:
            links_df.at[idx, 'owner'] = bbl_to_owner[bbl]
            print(f"Filled owner for BBL {bbl}: {bbl_to_owner[bbl]}")

# Save the updated CSV
links_df.to_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv', index=False)
print("\nCSV file has been updated with missing owner names.")