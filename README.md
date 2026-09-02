# NBA 2K26 Stats Tracker

A web-based statistics tracker for NBA 2K26 Rec Center games with AI-powered screenshot extraction.

## Features

- 📊 **Track team & player stats** - Points, rebounds, assists, shooting %, and more
- 📈 **Visual charts** - Win/loss trends, player comparisons, shooting percentages
- 🤖 **AI Screenshot Extraction** - Upload box score screenshots and auto-extract stats using Claude
- 💾 **Local storage** - All data saved in your browser
- 📱 **Responsive design** - Works on desktop and mobile

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install flask flask-cors anthropic
```

### 2. Set Your Anthropic API Key (Stored Locally)

Get your API key from https://console.anthropic.com

**Option A: Use a .env file (Recommended - persistent)**

```bash
# Copy the template
cp .env.example .env

# Edit .env and add your API key
# Replace sk-ant-your-api-key-here with your actual key
nano .env
# or open .env in any text editor
```

Your `.env` file should look like:
```
ANTHROPIC_API_KEY=sk-ant-api03-abc123...
```

**Option B: Set environment variable (Temporary - for current session)**

**macOS/Linux:**
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY='your-api-key-here'
```

**Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
```

> **Note:** Option A is recommended because the key persists between sessions. Option B requires re-entering the key each time you open a new terminal.

### 3. Run the App

**Easiest way - One command runs everything:**

```bash
./run.sh
```

This will:
- ✅ Start the Flask backend (port 5000)
- ✅ Start a web server for the frontend (port 8000)
- ✅ Automatically open in your browser

Then visit: **http://localhost:8000/nba2k26_tracker.html**

**Alternative - Manual setup:**

Terminal 1 (Backend):
```bash
python server.py
```

Terminal 2 (Frontend):
```bash
python -m http.server 8000
```

Then visit: http://localhost:8000/nba2k26_tracker.html

### 5. Check Server Status

In the app, go to the "➕ Log Game" tab. You should see:
- ✅ Server is running

If you see ❌ Server not running:
- Make sure `server.py` is running in your terminal
- Check that it's on port 5000
- Try refreshing the page

## How to Use

### Setup Your Roster (First Time)
1. Click **👥 Roster** tab
2. Enter your 5 squad members' gamertags and positions
3. Click **💾 Save Roster**

### Log a Game Manually
1. Click **➕ Log Game** tab
2. Enter game date, result (W/L/OT), and scores
3. Fill in each player's stats
4. Fill in opponent team totals
5. Click **💾 Save Game**

### Log a Game with AI (Recommended)
1. Click **➕ Log Game** tab
2. Upload your 2K box score screenshot (drag & drop or click to browse)
3. Click **⚡ Extract Stats with AI**
4. Review the extracted stats (AI fills them in automatically)
5. Make any corrections needed
6. Click **💾 Save Game**

### View Stats
- **📊 Dashboard** - See team record, KPIs, player averages, and totals
- **📈 Charts** - Visual analytics (win/loss trends, PPG, shooting %, etc.)
- **📋 History** - Browse all logged games with detailed stats

## Troubleshooting

### "Server not running" error
- Make sure you started `server.py` in a terminal
- Check that nothing else is using port 5000
- Restart the server if needed

### "Invalid API key" error
- Check that your `ANTHROPIC_API_KEY` environment variable is set correctly
- Make sure your API key starts with `sk-ant-`
- Restart the terminal and server after setting the env variable

### AI extraction gives wrong stats
- Make sure your screenshot is clear and shows the full box score table
- Try uploading a higher quality image
- You can always manually edit the extracted stats before saving

### Charts not showing
- You need to log at least one game first
- Make sure you have Chart.js loaded (requires internet connection)

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Charts**: Chart.js
- **Backend**: Python Flask
- **AI**: Anthropic Claude Sonnet 4

## Privacy & Data

- All game data is stored locally in your browser (localStorage)
- No data is sent to any server except the AI extraction (which only sends the screenshot)
- Your API key is stored as an environment variable (never in the browser)

## Cost

- The AI screenshot extraction uses Anthropic's Claude API
- Cost is approximately $0.01-0.02 per screenshot
- You can always log games manually (completely free)

## Support

Issues or questions? Check:
- Anthropic API docs: https://docs.anthropic.com
- This README for setup instructions
- Console logs in your browser (F12 → Console tab)

---

**Made for the squad 🏀**
