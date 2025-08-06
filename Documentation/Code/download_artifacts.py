#!/usr/bin/env python3
"""
Download Claude artifacts using Selenium to handle authentication and dynamic content.

This script will:
1. Open a browser window
2. Allow you to log in to Claude manually
3. Then automatically visit each artifact URL and save the code
"""

import csv
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def sanitize_filename(name):
    """Convert artifact name to valid filename"""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.replace('-_', '_').replace('_-', '_')
    return name[:100]  # Limit length

def download_artifacts():
    # Read the CSV file
    csv_path = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv'
    output_dir = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifacts'
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read artifact data
    artifacts = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['artifact_url'] != 'N/A':
                artifacts.append(row)
    
    print(f"Found {len(artifacts)} artifacts to download")
    
    # Initialize Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # First, go to Claude and wait for manual login
        print("\n" + "="*60)
        print("MANUAL LOGIN REQUIRED")
        print("="*60)
        print("1. The browser will open Claude.ai")
        print("2. Please log in to your account")
        print("3. After logging in, press Enter here to continue...")
        print("="*60)
        
        driver.get("https://claude.ai")
        input("\nPress Enter after you've logged in to Claude...")
        
        print("\nStarting artifact download...")
        
        # Process each artifact
        for i, artifact in enumerate(artifacts, 1):
            artifact_name = artifact['artifact_name']
            artifact_id = artifact['artifact_ID']
            url = artifact['artifact_url']
            
            print(f"\n[{i}/{len(artifacts)}] Processing: {artifact_name}")
            print(f"  URL: {url}")
            
            try:
                # Navigate to the artifact URL
                driver.get(url)
                time.sleep(3)  # Wait for page to load
                
                # Try multiple selectors to find the code content
                code_content = None
                
                # Common selectors for code blocks in Claude
                selectors = [
                    "pre code",  # Standard code block
                    ".code-block",  # Alternative code block class
                    "div[data-artifact-id]",  # Artifact container
                    ".artifact-content",  # Artifact content class
                    "pre",  # Plain pre tag
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            # Get the longest text (likely the main code)
                            texts = [elem.text for elem in elements if elem.text.strip()]
                            if texts:
                                code_content = max(texts, key=len)
                                break
                    except:
                        continue
                
                if code_content:
                    # Determine file extension based on content
                    if 'import ' in code_content or 'def ' in code_content or 'class ' in code_content:
                        ext = '.py'
                    elif 'function ' in code_content or 'const ' in code_content or 'var ' in code_content:
                        ext = '.js'
                    elif '<html' in code_content.lower() or '<!doctype' in code_content.lower():
                        ext = '.html'
                    elif '{' in code_content and '}' in code_content:
                        ext = '.json'
                    else:
                        ext = '.txt'
                    
                    # Save the artifact
                    filename = f"{sanitize_filename(artifact_name)}_{artifact_id}{ext}"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(code_content)
                    
                    print(f"  ✓ Saved: {filename}")
                else:
                    print(f"  ✗ Could not find code content")
                
            except TimeoutException:
                print(f"  ✗ Timeout loading page")
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
            
            # Small delay between requests
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"Download complete! Files saved to:")
        print(f"{output_dir}")
        print(f"{'='*60}")
        
    finally:
        input("\nPress Enter to close the browser...")
        driver.quit()

if __name__ == "__main__":
    print("Claude Artifact Downloader")
    print("="*60)
    print("This script requires Chrome and ChromeDriver to be installed.")
    print("If you don't have them:")
    print("1. Install Chrome browser")
    print("2. Run: pip install selenium")
    print("3. Run: brew install chromedriver (on Mac)")
    print("="*60)
    
    response = input("\nDo you have Chrome and ChromeDriver installed? (y/n): ")
    if response.lower() == 'y':
        download_artifacts()
    else:
        print("\nPlease install the requirements first:")
        print("pip install selenium")
        print("brew install chromedriver  # on Mac")
        print("Or download ChromeDriver from: https://chromedriver.chromium.org/")