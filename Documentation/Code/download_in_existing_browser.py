#!/usr/bin/env python3
"""
Use the EXISTING browser window where you're already logged in
Just paste artifact URLs into the current browser
"""

import csv
import os
import time
import random
import pyautogui
import pyperclip

def random_delay(min_seconds=3, max_seconds=7):
    """Add random delay to avoid bot detection"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

print("\n" + "="*60)
print("IMPORTANT: This will use your EXISTING browser window")
print("Make sure the Claude browser window is active/focused!")
print("="*60)
print("Press Enter when ready to start downloading...")
input()

csv_path = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv'

# Read artifact data
artifacts = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['artifact_url'] != 'N/A':
            artifacts.append(row)

print(f"\nFound {len(artifacts)} artifacts")
print("I will paste each URL into your browser")
print("Starting in 3 seconds...\n")
time.sleep(3)

for i, artifact in enumerate(artifacts, 1):
    artifact_name = artifact['artifact_name']
    url = artifact['artifact_url']
    
    print(f"[{i}/{len(artifacts)}] {artifact_name}")
    print(f"  Navigating to: {url}")
    
    # Copy URL to clipboard
    pyperclip.copy(url)
    
    # Cmd+L to focus address bar, then paste
    pyautogui.hotkey('cmd', 'l')
    time.sleep(0.5)
    pyautogui.hotkey('cmd', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    # Wait for page to load
    print(f"  Waiting 5-8 seconds for page to load...")
    random_delay(5, 8)
    
    print(f"  Page should be loaded. Moving to next...")
    
    if i < len(artifacts):
        delay = random.uniform(3, 5)
        print(f"  Waiting {delay:.1f} seconds before next artifact...")
        time.sleep(delay)

print("\n" + "="*60)
print("Navigation complete!")
print("All artifact pages have been visited")
print("="*60)