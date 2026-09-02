#!/bin/bash

# Recover essential command lookup when PATH is empty/misconfigured.
if [ -z "${PATH:-}" ]; then
    PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    export PATH
fi

# Default to direct local networking for the Flask app.
# Set KEEP_PROXY=1 before running if you intentionally need proxy variables.
if [ "${KEEP_PROXY:-0}" != "1" ]; then
    unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy
fi

echo "🏀 NBA 2K26 Stats Tracker"
echo "========================="
echo ""

# Check for .env file
if [ -f ".env" ]; then
    echo "✅ Found .env file"
    set -a
    . ./.env
    set +a
else
    echo "❌ ERROR: No .env file found!"
    echo "Please run: cp .env.example .env"
    echo "Then edit .env and add your API key"
    exit 1
fi

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY not set in .env"
    exit 1
fi

echo "✅ API key configured"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check dependencies
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo "🚀 Starting server..."
echo ""
echo "📡 Server: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo "========================="
echo ""

# Start Flask server
python3 server.py &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 2

echo "🌐 Opening browser..."
open http://localhost:8000 2>/dev/null || \
xdg-open http://localhost:8000 2>/dev/null || \
echo "Please open: http://localhost:8000"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping server..."
    kill $FLASK_PID 2>/dev/null
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Keep script running
wait
