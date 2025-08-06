#!/usr/bin/env python3
"""
Simple script to open browser for Claude login
"""

from selenium import webdriver
import time

print("Opening Chrome browser...")
options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
# Keep browser open after script ends
options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

print("\n" + "="*60)
print("BROWSER IS NOW OPEN")
print("="*60)
print("1. Please log in to Claude in the browser window")
print("2. After logging in, tell me you're ready")
print("3. Then I'll run the download script")
print("="*60)

driver.get("https://claude.ai")

print("\nBrowser is open at Claude.ai")
print("Please log in and tell me when you're ready!")
print("\nThe browser will stay open.")