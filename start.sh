#!/bin/bash

echo "🏀 NBA 2K26 Stats Tracker - Startup Script"
echo "=========================================="
echo ""

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ Found .env file"
    # Load .env file
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  No .env file found"
fi

# Check if API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "❌ ERROR: ANTHROPIC_API_KEY not configured!"
    echo ""
    echo "Please choose one option:"
    echo ""
    echo "Option A (Recommended - Persistent):"
    echo "  1. Copy the template: cp .env.example .env"
    echo "  2. Edit .env and add your API key"
    echo "  3. Run this script again"
    echo ""
    echo "Option B (Temporary - This session only):"
    echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
    echo "  Then run this script again"
    echo ""
    echo "Get your API key from: https://console.anthropic.com"
    echo ""
    exit 1
fi

echo "✅ API key configured"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Check if dependencies are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "🚀 Starting Flask backend server..."
echo "📡 Server will run at http://localhost:5000"
echo "🌐 Open nba2k26_tracker.html in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

python3 server.py
