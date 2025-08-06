#!/usr/bin/env python3
"""
Simple artifact downloader - run this AFTER logging in
"""

import csv
import os
import time
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name[:100]

print("Opening NEW Chrome browser...")
options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=options)

# Navigate to Claude
driver.get("https://claude.ai")

print("\n" + "="*60)
print("BROWSER IS OPEN")
print("PLEASE LOG IN TO CLAUDE NOW")
print("="*60)
print("\nWaiting 30 seconds for you to log in...")
time.sleep(30)

print("\nStarting downloads...")

csv_path = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv'
output_dir = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifacts'
os.makedirs(output_dir, exist_ok=True)

artifacts = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['artifact_url'] != 'N/A':
            artifacts.append(row)

print(f"Downloading {len(artifacts)} artifacts...\n")

for i, artifact in enumerate(artifacts[:5], 1):  # Just first 5 as test
    print(f"[{i}/5] {artifact['artifact_name']}")
    
    try:
        driver.get(artifact['artifact_url'])
        time.sleep(5)
        
        # Try to find code
        code = None
        for selector in ["pre code", "pre", ".code-block"]:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                texts = [e.text for e in elements if e.text.strip()]
                if texts:
                    code = max(texts, key=len)
                    if len(code) > 100:
                        break
        
        if code:
            filename = f"{sanitize_filename(artifact['artifact_name'])}.txt"
            with open(os.path.join(output_dir, filename), 'w') as f:
                f.write(code)
            print(f"  ✓ Saved")
        else:
            print(f"  ✗ No code found")
        
        time.sleep(3)
        
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\nTest complete! Check the artifacts folder")
input("Press Enter to close browser...")
driver.quit()