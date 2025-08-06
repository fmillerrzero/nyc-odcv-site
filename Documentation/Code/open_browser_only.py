#!/usr/bin/env python3
"""
Just open the browser and wait
"""

from selenium import webdriver

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
print("2. After you're FULLY LOGGED IN, tell me 'ready'")
print("3. ONLY THEN will I run the download script")
print("="*60)

driver.get("https://claude.ai")

print("\n*** I'M WAITING FOR YOU TO LOG IN ***")
print("*** TELL ME WHEN YOU'RE READY ***")