#!/usr/bin/env python3

import csv

# Read CSV
html_content = ""
with open('/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_dates.csv', 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader, 1):
        if row['artifact_url'] != 'N/A':
            html_content += f"""
    <div class="artifact">
        <strong>{i}. {row['artifact_name']}</strong><br>
        <small>ID: {row['artifact_ID']} | {row['date']}</small><br>
        <a href="{row['artifact_url']}" target="_blank">Open Artifact →</a>
    </div>
"""

# Read existing HTML and append artifacts
with open('/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_urls.html', 'r') as f:
    html = f.read()

# Insert before closing body tag
html = html.replace('</body>', html_content + '\n</body>')

# Save updated HTML
with open('/Users/forrestmiller/Desktop/New/Documentation/Code/artifact_urls.html', 'w') as f:
    f.write(html)

print("Created artifact_urls.html with all links!")
print("Open it in your browser and click through the links manually.")