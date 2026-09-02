# 📊 Data Storage Guide

## What Gets Stored Locally

Your 2K26 Stats Tracker stores all data **locally in your browser** using localStorage. Nothing is sent to any external database.

### ✅ Your Squad Data (Stored Permanently)

**Stored:**
- Player gamertags/names (the 5 members of your Rec squad)
- Player positions (PG, SG, SF, PF, C)
- Individual player stats for each game
- Player cumulative totals and averages

**Location:** Browser localStorage (persists forever until you clear browser data)

**Example:**
```json
{
  "roster": [
    {"id": "p1", "name": "YourGamertag1", "position": "PG"},
    {"id": "p2", "name": "YourGamertag2", "position": "SG"},
    {"id": "p3", "name": "YourGamertag3", "position": "SF"},
    {"id": "p4", "name": "YourGamertag4", "position": "PF"},
    {"id": "p5", "name": "YourGamertag5", "position": "C"}
  ]
}
```

---

### ❌ Opponent Data (NOT Stored Individually)

**NOT stored:**
- Opponent player names/gamertags
- Individual opponent player stats
- Opponent matchup details

**Only stored:**
- Aggregate opponent TEAM totals (PTS, REB, AST, etc.)
- Final opponent team score

**Example of what IS stored:**
```json
{
  "oppStats": {
    "pts": 72,
    "reb": 35,
    "ast": 18,
    "stl": 7,
    "blk": 4,
    "to": 12,
    "fgm": 28,
    "fga": 60,
    "tpm": 8,
    "tpa": 20
  }
}
```

**Why?** Privacy and simplicity. You're tracking YOUR squad's performance, not opponents' individual identities.

---

## Game Data Structure

Each game stores:

```json
{
  "id": 1713200000000,
  "date": "2026-04-15",
  "result": "W",
  "ourScore": 74,
  "oppScore": 68,
  "playerStats": [
    {
      "playerId": "p1",
      "played": true,
      "pts": 18,
      "reb": 5,
      "ast": 8,
      // ... full individual stats
    }
    // ... up to 5 players
  ],
  "oppStats": {
    // Only team totals, NO individual opponent data
    "pts": 68,
    "reb": 32,
    // ... etc
  }
}
```

---

## Where Is This Data?

**Location:** Browser's localStorage at key `rec2k26`

**To view your data:**
1. Open browser Developer Tools (F12)
2. Go to Application tab (Chrome) or Storage tab (Firefox)
3. Click "Local Storage"
4. Find `rec2k26`

**To backup your data:**
```javascript
// In browser console (F12 → Console tab)
localStorage.getItem('rec2k26')
// Copy the output and save to a file
```

**To restore data:**
```javascript
// In browser console
localStorage.setItem('rec2k26', 'paste-your-backup-json-here')
// Refresh the page
```

---

## Data Privacy

✅ **Private:**
- All data stays on YOUR computer
- Nothing sent to external servers (except screenshots to Anthropic API for extraction)
- No cloud storage, no database
- Opponent names are never stored

🔒 **Secure:**
- API key stored in `.env` file (not in browser)
- `.env` is gitignored (won't be committed)
- Only you can access your browser's localStorage

⚠️ **Backup Recommendation:**
Since data is in localStorage, if you:
- Clear browser data
- Uninstall browser
- Switch browsers

...your stats will be lost. Consider periodically backing up your localStorage data (see above).

---

## Can I Change Gamertags?

Yes! Your gamertags are editable:

1. Go to "👥 Roster" tab
2. Edit any gamertag
3. Click "💾 Save Roster"

The gamertags are permanent in the sense that they **persist locally**, but you can update them anytime. All historical game stats will still be linked to the player ID (p1, p2, etc.), so changing a name won't affect past games.

---

## Summary

| Data Type | Stored? | Details |
|-----------|---------|---------|
| Your squad gamertags | ✅ Yes | Permanent, editable |
| Your squad positions | ✅ Yes | Editable |
| Your squad stats | ✅ Yes | Every game, every stat |
| Opponent names | ❌ No | Never stored |
| Opponent individual stats | ❌ No | Never stored |
| Opponent team totals | ✅ Yes | Aggregate only |
| Game results | ✅ Yes | W/L/OT, scores, date |

**Bottom line:** You're tracking your squad's journey, not building a database of opponents. Clean, simple, private.
