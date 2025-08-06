#!/usr/bin/env python3
"""
Step 1: Open browser and wait for login
"""

from selenium import webdriver

print("Opening Chrome browser...")
options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

print("\n" + "="*60)
print("BROWSER IS NOW OPEN")
print("="*60)
print("1. Please log in to Claude in the browser window")
print("2. After logging in, tell me 'ready'")
print("3. Then I'll run the download script")
print("="*60)

driver.get("https://claude.ai")

# Keep browser open
print("\nBrowser is open. Waiting for you to log in...")
print("The browser will stay open. Tell me when you're logged in!")

# Save driver session info for next script
import pickle
with open('/tmp/driver_session.pkl', 'wb') as f:
    pickle.dump({
        'session_id': driver.session_id,
        'executor_url': driver.command_executor._url
    }, f)

# Keep script running
import time
while True:
    time.sleep(10)