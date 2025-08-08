import pandas as pd

# Read the CSV file
df = pd.read_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv')

# Fill in missing rank values sequentially
for idx in range(len(df)):
    if pd.isna(df.at[idx, 'rank']) or df.at[idx, 'rank'] == '':
        # Continue from the last valid rank
        if idx > 0:
            last_rank = idx  # Since indices start at 0, this gives us the next rank
            df.at[idx, 'rank'] = float(last_rank + 1)
            print(f"Filled rank {last_rank + 1} for row {idx + 1}")

# Ensure all ranks are sequential
for idx in range(len(df)):
    df.at[idx, 'rank'] = float(idx + 1)

# Save the updated CSV
df.to_csv('/Users/forrestmiller/Desktop/New/data/TOP_250_BUILDING_LINKS_FINAL_CORRECTED.csv', index=False)
print(f"\nFixed rank column - all {len(df)} rows now have sequential rank numbers.")