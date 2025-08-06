#!/usr/bin/env python3
"""
Connect to the already open browser and download
"""

import csv
import os
import time
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name[:100]

def random_delay(min_seconds=3, max_seconds=7):
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

print("Connecting to existing Chrome session...")

# Connect to the browser that's already open
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

# First kill the old script and restart Chrome with debugging
os.system("pkill -f download_final.py")
time.sleep(1)

# Open Chrome with remote debugging
os.system("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 &")
time.sleep(3)

driver = webdriver.Chrome(options=chrome_options)

csv_path = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv'
output_dir = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifacts'
os.makedirs(output_dir, exist_ok=True)

# Read artifacts
artifacts = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['artifact_url'] != 'N/A':
            artifacts.append(row)

print(f"Found {len(artifacts)} artifacts\n")

successful = 0
failed = 0

for i, artifact in enumerate(artifacts, 1):
    artifact_name = artifact['artifact_name']
    artifact_id = artifact['artifact_ID']
    url = artifact['artifact_url']
    
    print(f"[{i}/{len(artifacts)}] {artifact_name}")
    
    try:
        driver.get(url)
        random_delay(5, 8)
        
        code_content = None
        selectors = ["pre code", ".code-block", "div[class*='artifact']", "pre"]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    texts = [elem.text for elem in elements if elem.text.strip()]
                    if texts:
                        code_content = max(texts, key=len)
                        if len(code_content) > 100:
                            break
            except:
                continue
        
        if code_content and len(code_content) > 100:
            ext = '.py' if 'def ' in code_content else '.txt'
            filename = f"{sanitize_filename(artifact_name)}_{artifact_id}{ext}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code_content)
            
            print(f"  ✓ Saved ({len(code_content)} chars)")
            successful += 1
        else:
            print(f"  ✗ No code found")
            failed += 1
        
        if i < len(artifacts):
            time.sleep(random.uniform(3, 7))
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        failed += 1

print(f"\nDone! {successful} saved, {failed} failed")
print(f"Files in: {output_dir}")