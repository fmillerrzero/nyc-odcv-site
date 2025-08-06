#!/bin/bash

# Deploy building reports to GitHub Pages
# This script copies HTML reports from the Building reports folder to the repo root

echo "🚀 Deploying building reports to GitHub..."

# Change to the repo directory
cd /Users/forrestmiller/Desktop/New

# Copy all HTML files from Building reports to repo root
echo "📋 Copying building reports..."
cp "/Users/forrestmiller/Desktop/New/Building reports/"*.html .

# Check if any files were copied
if ls *.html 1> /dev/null 2>&1; then
    # Count the files
    count=$(ls -1 *.html | grep -E '^[0-9]+\.html$' | wc -l)
    echo "✅ Copied $count building report(s)"
    
    # Add to git (including any deletions)
    echo "📦 Adding files to git..."
    git add *.html
    git add -u  # This stages deletions
    
    # Commit and push
    echo "💾 Committing changes..."
    git commit -m "Update building reports

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
    
    echo "📤 Pushing to GitHub..."
    git push origin main
    
    echo "✨ Deployment complete! Reports are now live on GitHub Pages."
else
    echo "⚠️  No building reports found in Building reports folder"
    exit 1
fi