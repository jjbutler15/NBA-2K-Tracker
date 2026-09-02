# 🚀 Quick Start

## One Command to Run Everything

```bash
cd "/Users/jabaributler/2k26 Rec Stats Tracker"
./run.sh
```

This will:
- ✅ Start the Flask backend server
- ✅ Start a web server for the HTML
- ✅ Automatically open your browser to http://localhost:8000/nba2k26_tracker.html

**Keep the terminal open** - both servers are running.

Press `Ctrl+C` to stop both servers when you're done.

---

## First Time Setup (One Time Only)

If you haven't set up your API key yet:

```bash
# Already done for you, but if you need to change it:
nano .env
# Edit the ANTHROPIC_API_KEY line
```

---

## What's Running

When you run `./run.sh`:

- **Backend Server** (`server.py`): http://localhost:5000
  - Handles AI extraction
  - Reads API key from `.env`
  
- **Frontend Server** (Python HTTP): http://localhost:8000
  - Serves the HTML/CSS/JavaScript
  - Connects to backend server

---

## Troubleshooting

### Permission denied on ./run.sh
```bash
chmod +x run.sh
./run.sh
```

### Port already in use
Something else is using port 5000 or 8000. Kill those processes:
```bash
lsof -ti:5000 | xargs kill
lsof -ti:8000 | xargs kill
```

### Server status shows red in browser
- Make sure `./run.sh` is running in the terminal
- Try refreshing the browser page
- Check terminal for error messages

---

## Ready to Use!

1. Run `./run.sh`
2. Browser opens automatically
3. Go to "👥 Roster" tab to set up your squad
4. Go to "➕ Log Game" tab to upload screenshots
5. Check server status is green ✅
6. Upload a 2K box score screenshot and click "Extract Stats"

🎉 You're all set!
