#!/usr/bin/env python3
"""
Download artifacts - keeps browser open
"""

import csv
import os
import time
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By

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

# Open browser
print("Opening Chrome browser...")
options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# Go to Claude
driver.get("https://claude.ai")

print("\n" + "="*60)
print("BROWSER IS OPEN - PLEASE LOG IN TO CLAUDE")
print("="*60)
print("The browser will stay open.")
print("After you log in, tell me 'ready' and I'll continue")
print("="*60)

# Keep the script running so browser stays open
while True:
    time.sleep(1)