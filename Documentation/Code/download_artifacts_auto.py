#!/usr/bin/env python3
"""
Download Claude artifacts - automatic version without prompts
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
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.replace('-_', '_').replace('_-', '_')
    return name[:100]

def download_artifacts():
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
    
    print(f"Found {len(artifacts)} artifacts to download")
    
    # Initialize Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("\n" + "="*60)
        print("IMPORTANT: Please log in to Claude in the browser window")
        print("The script will wait 30 seconds for you to log in")
        print("="*60)
        
        driver.get("https://claude.ai")
        print("\nWaiting 30 seconds for login...")
        time.sleep(30)
        
        print("\nStarting artifact download...")
        
        # Process each artifact
        for i, artifact in enumerate(artifacts, 1):
            artifact_name = artifact['artifact_name']
            artifact_id = artifact['artifact_ID']
            url = artifact['artifact_url']
            
            print(f"\n[{i}/{len(artifacts)}] Processing: {artifact_name}")
            
            try:
                driver.get(url)
                time.sleep(3)
                
                # Try multiple selectors
                code_content = None
                selectors = [
                    "pre code",
                    ".code-block",
                    "div[data-artifact-id]",
                    ".artifact-content",
                    "pre"
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            texts = [elem.text for elem in elements if elem.text.strip()]
                            if texts:
                                code_content = max(texts, key=len)
                                break
                    except:
                        continue
                
                if code_content and len(code_content) > 50:
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
                    
                    print(f"  ✓ Saved: {filename}")
                else:
                    print(f"  ✗ Could not find code content")
                
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
            
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"Download complete!")
        print(f"Files saved to: {output_dir}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        print("\nPlease install ChromeDriver:")
        print("brew install chromedriver")
        return
    
    finally:
        if 'driver' in locals():
            print("\nClosing browser in 5 seconds...")
            time.sleep(5)
            driver.quit()

if __name__ == "__main__":
    download_artifacts()