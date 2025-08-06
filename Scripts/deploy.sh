#!/bin/bash

# Full deployment script for NYC ODCV site
# Repository: https://github.com/fmillerrzero/nyc-odcv-site

set -e  # Exit on any error

echo "🚀 NYC ODCV Site Deployment Script"
echo "=================================="
echo ""

# Change to the repo directory
cd /Users/forrestmiller/Desktop/New

# Check git status first
echo "📊 Checking git status..."
git status --short

echo ""
echo "Select deployment option:"
echo "  1) Homepage only (index.html)"
echo "  2) Homepage + All building reports"
echo "  3) Everything (Homepage + Reports + Images + CSVs)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🏠 Deploying homepage only..."
        
        # Generate homepage
        echo "📝 Generating homepage..."
        python3 Scripts/homepage.py
        
        # Add and commit homepage
        git add index.html
        
        # Check if there are changes
        if git diff --cached --quiet; then
            echo "✅ No changes to homepage"
        else
            git commit -m "Update homepage
            
🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
            echo "📤 Pushing to GitHub..."
            git push origin main
            echo "✨ Homepage deployed!"
        fi
        ;;
        
    2)
        echo ""
        echo "🏢 Deploying homepage + building reports..."
        
        # Generate homepage
        echo "📝 Generating homepage..."
        python3 Scripts/homepage.py
        
        # Generate building reports
        echo "📋 Generating building reports (this may take a few minutes)..."
        python3 Scripts/building.py
        
        # Copy reports from Building reports folder
        echo "📦 Copying building reports..."
        cp "Building reports/"*.html .
        
        # Count reports
        report_count=$(ls -1 *.html | grep -E '^[0-9]+\.html$' | wc -l)
        echo "✅ Generated $report_count building reports"
        
        # Add all HTML files
        git add *.html
        
        # Check if there are changes
        if git diff --cached --quiet; then
            echo "✅ No changes to deploy"
        else
            git commit -m "Update homepage and building reports
            
🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
            echo "📤 Pushing to GitHub..."
            git push origin main
            echo "✨ Homepage and reports deployed!"
        fi
        ;;
        
    3)
        echo ""
        echo "🌐 Deploying everything..."
        
        # Generate homepage
        echo "📝 Generating homepage..."
        python3 Scripts/homepage.py
        
        # Generate building reports
        echo "📋 Generating building reports (this may take a few minutes)..."
        python3 Scripts/building.py
        
        # Copy reports from Building reports folder
        echo "📦 Copying building reports..."
        cp "Building reports/"*.html .
        
        # Count reports
        report_count=$(ls -1 *.html | grep -E '^[0-9]+\.html$' | wc -l)
        echo "✅ Generated $report_count building reports"
        
        # Add all HTML files
        git add *.html
        
        # Check for updated images
        echo "🖼️ Checking for new/updated images..."
        git add images/
        
        # Check for updated CSVs
        echo "📊 Checking for updated CSV files..."
        git add data/*.csv
        
        # Check for updated logos
        echo "🎨 Checking for updated logos..."
        git add Logos/
        
        # Show what will be committed
        echo ""
        echo "📋 Files to be committed:"
        git status --short
        
        # Check if there are changes
        if git diff --cached --quiet; then
            echo "✅ No changes to deploy"
        else
            # Get counts
            html_changes=$(git diff --cached --name-only | grep -c '\.html$' || true)
            image_changes=$(git diff --cached --name-only | grep -c '^images/' || true)
            csv_changes=$(git diff --cached --name-only | grep -c '\.csv$' || true)
            
            git commit -m "Update site - Homepage, reports, and assets

- HTML files: $html_changes changes
- Images: $image_changes changes  
- CSV data: $csv_changes changes

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
            
            echo "📤 Pushing to GitHub..."
            git push origin main
            echo "✨ Full deployment complete!"
        fi
        ;;
        
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "🌐 Site URL: https://fmillerrzero.github.io/nyc-odcv-site/"
echo ""