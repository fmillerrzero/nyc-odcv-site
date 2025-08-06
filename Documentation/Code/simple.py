#!/usr/bin/env python3

import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

# Open Chrome
driver = webdriver.Chrome()
driver.get("https://claude.ai")

print("LOG IN TO CLAUDE")
print("Waiting 60 seconds...")
time.sleep(60)

# Read CSV
artifacts = []
with open('/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['artifact_url'] != 'N/A':
            artifacts.append(row)

output_dir = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifacts'
os.makedirs(output_dir, exist_ok=True)

# Download each one slowly
for i, artifact in enumerate(artifacts, 1):
    print(f"[{i}/{len(artifacts)}] {artifact['artifact_name']}")
    
    driver.get(artifact['artifact_url'])
    time.sleep(10)  # Wait 10 seconds
    
    try:
        # Find code
        elements = driver.find_elements(By.TAG_NAME, "pre")
        if elements:
            code = elements[0].text
            if code:
                filename = f"{artifact['artifact_ID']}.txt"
                with open(os.path.join(output_dir, filename), 'w') as f:
                    f.write(code)
                print("  Saved")
        else:
            print("  No code")
    except:
        print("  Error")
    
    time.sleep(5)  # Wait 5 seconds before next

print("DONE")
time.sleep(999999)  # Keep browser open