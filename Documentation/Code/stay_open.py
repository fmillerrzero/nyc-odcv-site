#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import os

# Open Chrome with detach option so it stays open
options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=options)
driver.get("https://claude.ai")

print("BROWSER IS OPEN")
print("LOG IN NOW")
print("Waiting 60 seconds for you to login...")

time.sleep(60)

print("\nStarting downloads...")

# Read CSV
artifacts = []
with open('/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['artifact_url'] != 'N/A':
            artifacts.append(row)

output_dir = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifacts_new'
os.makedirs(output_dir, exist_ok=True)

# Download slowly
for i, artifact in enumerate(artifacts[:10], 1):  # First 10 only
    print(f"[{i}/10] {artifact['artifact_name']}")
    
    try:
        driver.get(artifact['artifact_url'])
        time.sleep(8)
        
        # Get code
        pre_elements = driver.find_elements(By.TAG_NAME, "pre")
        if pre_elements:
            code = pre_elements[0].text
            if code and len(code) > 50:
                filename = f"{artifact['artifact_ID']}.txt"
                with open(os.path.join(output_dir, filename), 'w') as f:
                    f.write(code)
                print(f"  Saved ({len(code)} chars)")
            else:
                print("  No code")
        else:
            print("  No pre tag")
            
        time.sleep(5)
        
    except Exception as e:
        print(f"  Error: {e}")
        break

print("\nDONE - Browser stays open")