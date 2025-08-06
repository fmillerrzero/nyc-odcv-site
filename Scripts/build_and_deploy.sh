#!/bin/bash

# Complete build and deploy process
echo "🏗️  Starting complete build and deploy process..."

# Change to the repo directory
cd /Users/forrestmiller/Desktop/New

# Step 1: Generate building reports
echo "📊 Generating building reports..."
python3 Scripts/building.py

# Check if building.py succeeded
if [ $? -eq 0 ]; then
    echo "✅ Building reports generated successfully"
else
    echo "❌ Error generating building reports"
    exit 1
fi

# Step 2: Generate homepage (if needed)
if [ -f "Scripts/homepage.py" ]; then
    echo "🏠 Generating homepage..."
    python3 Scripts/homepage.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Homepage generated successfully"
    else
        echo "⚠️  Warning: Homepage generation failed"
    fi
fi

# Step 3: Copy reports from Building reports folder to repo root
echo "📋 Copying building reports to repo root..."
cp "/Users/forrestmiller/Desktop/New/Building reports/"*.html .

# Count the files
count=$(ls -1 *.html | grep -E '^[0-9]+\.html$' | wc -l)
echo "✅ Copied $count building report(s)"

# Step 4: Add all changes to git
echo "📦 Adding all changes to git..."
git add .
git add -u  # This stages any deletions

# Step 5: Commit changes
echo "💾 Committing changes..."
git commit -m "Update building reports and site

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

# Step 6: Push to GitHub
echo "📤 Pushing to GitHub..."
git push origin main

echo "✨ Build and deploy complete! Your site is now live on GitHub Pages."
echo "🌐 Visit: https://fmillerrzero.github.io/nyc-odcv-site/"