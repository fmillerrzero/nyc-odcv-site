#!/usr/bin/env python3
"""
Connect to existing Chrome session where you're already logged in
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
    """Convert artifact name to valid filename"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.replace('-_', '_').replace('_-', '_')
    return name[:100]

def random_delay(min_seconds=3, max_seconds=7):
    """Add random delay to avoid bot detection"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

print("\n" + "="*60)
print("CONNECTING TO YOUR EXISTING CHROME BROWSER")
print("="*60)
print("Make sure Chrome is running with remote debugging enabled.")
print("If not, close Chrome and run this command in Terminal:")
print()
print("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
print()
print("Then log in to Claude and come back here.")
print("="*60)

response = input("\nIs Chrome running with remote debugging? (y/n): ")
if response.lower() != 'y':
    print("\nPlease restart Chrome with the command above first.")
    exit()

# Connect to existing Chrome
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

try:
    driver = webdriver.Chrome(options=chrome_options)
    print("✓ Connected to existing Chrome browser!")
except:
    print("✗ Could not connect. Make sure Chrome is running with --remote-debugging-port=9222")
    exit()

csv_path = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv'
output_dir = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifacts'

os.makedirs(output_dir, exist_ok=True)

# Read artifact data
artifacts = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['artifact_url'] != 'N/A':
            artifacts.append(row)

print(f"\nFound {len(artifacts)} artifacts to download")
print("Starting download with delays...\n")

successful = 0
failed = 0

for i, artifact in enumerate(artifacts, 1):
    artifact_name = artifact['artifact_name']
    artifact_id = artifact['artifact_ID']
    url = artifact['artifact_url']
    
    print(f"[{i}/{len(artifacts)}] Processing: {artifact_name}")
    
    try:
        driver.get(url)
        print(f"  Waiting for page to load...")
        random_delay(5, 8)
        
        # Try to find code content
        code_content = None
        selectors = [
            "pre code",
            ".code-block",
            "div[class*='artifact']",
            "div[class*='code']",
            "pre"
        ]
        
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
            # Determine file extension
            if 'import ' in code_content or 'def ' in code_content:
                ext = '.py'
            elif 'function ' in code_content or 'const ' in code_content:
                ext = '.js'
            elif '<html' in code_content.lower():
                ext = '.html'
            else:
                ext = '.txt'
            
            filename = f"{sanitize_filename(artifact_name)}_{artifact_id}{ext}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code_content)
            
            print(f"  ✓ Saved: {filename} ({len(code_content)} chars)")
            successful += 1
        else:
            print(f"  ✗ Could not find code content")
            failed += 1
        
        # Random delay before next
        if i < len(artifacts):
            delay = random.uniform(3, 7)
            print(f"  Waiting {delay:.1f} seconds...")
            time.sleep(delay)
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        failed += 1

print(f"\n{'='*60}")
print(f"Download complete!")
print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(f"Files saved to: {output_dir}")
print(f"{'='*60}")