#!/usr/bin/env python3
import os
import re
import time
import requests
from datetime import datetime

# === CONFIG ===
OUTPUT_BASE = "/Users/forrestmiller/Desktop/new logos"
API_KEY = "9067cce44a4c4420272a960a5b4e07156032362dcee6bf2ea214cd3ef292abcd"
SERPAPI_URL = "https://serpapi.com/search"

# === ORGANIZATIONS ===
ORGANIZATIONS = [
    "Okada & Company",
    "Koeppel Rosen",
    "Adams & Company",
    "Resolution Real Estate",
    "Jack Resnick & Sons",
    "Adams & Company",
    "Williams Equities",
    "LSL Advisors",
    "Samco Properties",
    "Jack Resnick & Sons",
    "ABS Partners",
    "Avison Young",
    "Rosen Equities",
    "Dezer Properties",
    "Savitt Partners",
    "Himmel + Meringoff",
    "Abner Properties",
    "Sioni Group",
    "Joseph P. Day",
    "Savanna Real Estate Fund"
]

# === HELPERS ===
def sanitize_filename(text):
    """Sanitize text for filenames"""
    # Replace special characters with underscores
    filename = re.sub(r'[^\w\-_. ]', '_', str(text))
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    return filename.strip('_')

def download_image_smart(img_url, filepath):
    """Download image with smart headers"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    try:
        response = requests.get(img_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return True
    except:
        return False

def search_and_download_logo(organization):
    """Search for logo with white/transparent background"""
    
    # Try multiple search queries for better results
    search_queries = [
        f"{organization} real estate logo",
        f"{organization} logo png",
        f"{organization} company logo"
    ]
    
    for query in search_queries:
        params = {
            "engine": "google_images",
            "q": query,
            "api_key": API_KEY,
            "hl": "en",
            "gl": "us",
            "num": 10
        }
        
        try:
            print(f"  🔍 Searching: {query}")
            response = requests.get(SERPAPI_URL, params=params, timeout=30)
            response.raise_for_status()
            
            results = response.json()
            images = results.get("images_results", [])
            
            if not images:
                continue
            
            # Look for PNG images (more likely to have transparent background)
            png_images = [img for img in images if 'png' in img.get('original', '').lower()]
            
            # If no PNGs, use all images
            if not png_images:
                png_images = images
            
            # Try to download the first suitable image
            for img in png_images[:5]:  # Try first 5 images
                img_url = img.get("original", "")
                
                if not img_url:
                    continue
                
                # Determine file extension
                extension = '.png' if 'png' in img_url.lower() else '.jpg'
                filename = sanitize_filename(organization) + extension
                filepath = os.path.join(OUTPUT_BASE, filename)
                
                # Try to download
                if download_image_smart(img_url, filepath):
                    print(f"  ✅ Saved: {filename}")
                    return True
            
        except Exception as e:
            print(f"  ❌ Search error: {str(e)[:50]}...")
            continue
    
    return False

# === MAIN PROCESS ===
def main():
    print("=" * 60)
    print("ORGANIZATION LOGO DOWNLOADER")
    print("=" * 60)
    print("Looking for white/transparent background logos...")
    
    # Create output directory
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    
    print(f"\n🚀 Processing {len(ORGANIZATIONS)} organizations...")
    print(f"⏱️  Estimated time: {len(ORGANIZATIONS) * 5 // 60 + 1} minutes")
    
    successful = 0
    failed = []
    
    for i, org in enumerate(ORGANIZATIONS):
        print(f"\n[{i+1}/{len(ORGANIZATIONS)}] {org}")
        
        # Search and download logo
        if search_and_download_logo(org):
            successful += 1
        else:
            failed.append(org)
            print(f"  ⚠️  No suitable logo found")
        
        # Brief pause between searches
        time.sleep(1)
        
        # Progress update every 10 organizations
        if (i + 1) % 10 == 0:
            print(f"\n--- Progress: {i+1}/{len(ORGANIZATIONS)} ({successful} successful) ---\n")
    
    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {successful} logos")
    print(f"❌ Failed: {len(failed)} organizations")
    
    if failed:
        print(f"\n📄 Failed organizations:")
        for org in failed[:10]:  # Show first 10
            print(f"  - {org}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")
    
    print(f"\n✨ Logos saved to: {OUTPUT_BASE}")
    print(f"🏁 Completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()