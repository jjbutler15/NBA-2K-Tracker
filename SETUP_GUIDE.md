# Quick Setup Guide

## Where is my API key stored?

✅ **Your API key is stored LOCALLY on your computer** - NOT in the browser!

- **Option A:** In a `.env` file (recommended)
- **Option B:** As an environment variable

🔒 **Security:** Your API key never touches the browser or gets sent anywhere except to Anthropic's API for processing screenshots.

---

## Step-by-Step Setup

### 1. Get Your API Key

1. Go to https://console.anthropic.com
2. Sign in or create an account
3. Navigate to "API Keys"
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)

### 2. Store Your API Key Locally

**Recommended: Use a .env file**

```bash
# In the project folder, run:
cp .env.example .env
```

Then edit the `.env` file and replace the placeholder:

```
# Before:
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# After:
ANTHROPIC_API_KEY=sk-ant-api03-abc123xyz789...
```

**Alternative: Set as environment variable**

```bash
# macOS/Linux
export ANTHROPIC_API_KEY='sk-ant-api03-abc123...'

# Windows PowerShell
$env:ANTHROPIC_API_KEY='sk-ant-api03-abc123...'
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Server

**Easy way:**
```bash
./start.sh
```

**Manual way:**
```bash
python server.py
```

### 5. Open the App

Open `nba2k26_tracker.html` in your browser (just double-click it)

---

## How It Works

```
┌─────────────┐
│   Browser   │  ← You interact here (upload screenshots)
│  (HTML app) │
└──────┬──────┘
       │
       │ Sends image
       ▼
┌─────────────┐
│ Flask Server│  ← Runs on your computer (localhost:5000)
│ (server.py) │  ← Reads API key from .env or environment
└──────┬──────┘
       │
       │ Sends request with API key
       ▼
┌─────────────┐
│ Anthropic   │  ← AI processes screenshot
│     API     │  ← Returns extracted stats
└─────────────┘
```

**Key Point:** The browser NEVER sees your API key. It only sees the extracted stats result.

---

## Verify It's Working

1. Start the server: `./start.sh`
2. You should see: `✅ API key configured`
3. Open `nba2k26_tracker.html` in browser
4. Go to "➕ Log Game" tab
5. Check server status - should show: `✅ Server is running`

---

## Troubleshooting

### "API key not configured" error

**If using .env file:**
- Make sure you created `.env` (not `.env.example`)
- Check that the file is in the same folder as `server.py`
- Make sure there are no spaces around the `=` sign
- Restart the server after editing `.env`

**If using environment variable:**
- The variable only lasts for the current terminal session
- You need to set it again if you close the terminal
- Consider using the `.env` file instead for persistence

### "Server not running" error in browser

- Make sure `server.py` is running in a terminal
- Check for error messages in the terminal
- Try restarting the server

### Still having issues?

Check the terminal where `server.py` is running for error messages.

---

## Security Notes

✅ **Safe:**
- Storing API key in `.env` file on your computer
- The `.env` file is in `.gitignore` (won't be committed to git)
- Key is only used server-side

❌ **Never do this:**
- Don't commit `.env` to git
- Don't share your API key with others
- Don't store it in the browser/HTML file

---

**You're all set! 🎉**

The API key is safely stored on your computer and the app is ready to use.
