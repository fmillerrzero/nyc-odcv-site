#!/usr/bin/env python3
"""
Alternative approach: Extract artifact code from the CSS file directly
since we already have all the artifact code embedded in artifact.css
"""

import csv
import os
import re
import html

def sanitize_filename(name):
    """Convert artifact name to valid filename"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.replace('-_', '_').replace('_-', '_')
    return name[:100]

def extract_artifacts_from_css():
    css_path = '/Users/forrestmiller/Desktop/artifact.css'
    csv_path = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv'
    output_dir = '/Users/forrestmiller/Desktop/New/Documentation/Code/artifacts'
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the CSV to get artifact mappings
    artifact_map = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['artifact_ID'] != 'N/A':
                artifact_map[row['artifact_ID']] = row['artifact_name']
    
    print(f"Looking for {len(artifact_map)} artifacts in CSS file...")
    
    # Read the entire CSS file
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find artifact blocks with their content
    # The pattern looks for artifactId= followed by content in <pre> or <code> tags
    saved_count = 0
    
    for artifact_id, artifact_name in artifact_map.items():
        print(f"\nSearching for: {artifact_name} (ID: {artifact_id})")
        
        # Find the artifact block
        pattern = f'artifactId={artifact_id}'
        idx = content.find(pattern)
        
        if idx != -1:
            # Look for code content after this artifact ID
            # Search in the next ~10000 characters for code blocks
            block = content[idx:idx+50000]
            
            # Try to extract code from various possible containers
            code_patterns = [
                r'<pre[^>]*>([^<]+)</pre>',
                r'<code[^>]*>([^<]+)</code>',
                r'>([^<]{100,})<',  # Long text between tags
            ]
            
            code_content = None
            for pattern in code_patterns:
                matches = re.findall(pattern, block, re.DOTALL)
                if matches:
                    # Get the longest match
                    code_content = max(matches, key=len)
                    # Unescape HTML entities
                    code_content = html.unescape(code_content)
                    # Clean up the content
                    code_content = code_content.strip()
                    
                    if len(code_content) > 50:  # Minimum reasonable code length
                        break
            
            if code_content:
                # Determine file extension
                if 'import ' in code_content or 'def ' in code_content or 'class ' in code_content:
                    ext = '.py'
                elif 'function ' in code_content or 'const ' in code_content or 'var ' in code_content:
                    ext = '.js'
                elif '<html' in code_content.lower() or '<!doctype' in code_content.lower():
                    ext = '.html'
                else:
                    ext = '.txt'
                
                # Save the file
                filename = f"{sanitize_filename(artifact_name)}_{artifact_id}{ext}"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code_content)
                
                print(f"  ✓ Saved: {filename} ({len(code_content)} chars)")
                saved_count += 1
            else:
                print(f"  ✗ Could not extract code content")
        else:
            print(f"  ✗ Artifact ID not found in CSS")
    
    print(f"\n{'='*60}")
    print(f"Extraction complete!")
    print(f"Saved {saved_count} out of {len(artifact_map)} artifacts")
    print(f"Files saved to: {output_dir}")
    print(f"{'='*60}")

if __name__ == "__main__":
    print("Claude Artifact Extractor (from CSS)")
    print("="*60)
    extract_artifacts_from_css()