#!/usr/bin/env python3
"""
Recover games from saved screenshots by re-extracting with AI
"""
import anthropic
import os
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

screenshot_dir = Path("screenshots/Season_1/April")
screenshots = sorted(screenshot_dir.glob("*.jpg")) + sorted(screenshot_dir.glob("*.JPG"))

print(f"🔍 Found {len(screenshots)} screenshots to recover")
print()

# Expected roster from the app
roster = [
    {"id": "p1", "name": "AubreyArchAngel", "position": ""},
    {"id": "p2", "name": "HoldMyBir", "position": ""},
    {"id": "p3", "name": "KingxMarsh", "position": ""},
    {"id": "p4", "name": "SkyWalkerX007", "position": ""},
    {"id": "p5", "name": "Bari_JB", "position": ""}
]


def normalize_name(name):
    return ''.join(ch for ch in str(name).lower() if ch.isalnum())

games = []

for screenshot_path in screenshots:
    print(f"📸 Processing: {screenshot_path.name}")

    # Read and encode image
    with open(screenshot_path, 'rb') as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')

    # Extract with Claude
    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": """Extract NBA 2K26 Rec stats. Return JSON with:
{
  "our_team": [{"name":"Player","pts":0,"reb":0,"ast":0,"stl":0,"blk":0,"to":0,"fgm":0,"fga":0,"tpm":0,"tpa":0,"ftm":0,"fta":0,"fouls":0,"min":0}],
  "opp_team": [{"pts":0,"fgm":0,"fga":0,"tpm":0,"tpa":0}],
  "our_score":0,
  "opp_score":0,
  "result":"W"
}
Extract BOTH teams (5 players each), in order. Names required for both teams."""
                    }
                ]
            }]
        )

        result_text = response.content[0].text.strip()
        # Clean markdown
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        data = json.loads(result_text)

        # Auto-detect which team is ours by matching roster names
        roster_names = {normalize_name(p["name"]) for p in roster if p.get("name")}

        our_team_matches = sum(
            1 for p in data.get("our_team", [])
            if normalize_name(p.get("name", "")) in roster_names
        )
        opp_team_matches = sum(1 for p in data.get("opp_team", [])
                               if normalize_name(p.get("name", "")) in roster_names)

        # Swap if backwards
        if opp_team_matches > our_team_matches:
            data["our_team"], data["opp_team"] = data["opp_team"], data["our_team"]
            data["our_score"], data["opp_score"] = data["opp_score"], data["our_score"]
            data["result"] = "L" if data["result"] == "W" else "W" if data["result"] == "L" else data["result"]

        # Build game object
        # Extract date from filename (game_20260415_183638.jpg -> 2026-04-15)
        if "game_" in screenshot_path.stem:
            date_str = screenshot_path.stem.split("_")[1]
            game_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            game_date = "2026-04-15"  # Fallback for manual screenshots

        # Map players to roster and build playerStats
        extracted_index_by_name = {}
        for idx, ep in enumerate(data.get("our_team", [])):
            ep_name = normalize_name(ep.get("name", ""))
            if ep_name and ep_name not in extracted_index_by_name:
                extracted_index_by_name[ep_name] = idx

        used_extracted_indexes = set()
        player_stats = []
        for i, roster_player in enumerate(roster):
            # Prefer exact normalized name matching, then fallback to same index.
            extracted_player = None
            matched_idx = extracted_index_by_name.get(normalize_name(roster_player.get("name", "")))

            if matched_idx is not None and matched_idx < len(data.get("our_team", [])):
                extracted_player = data["our_team"][matched_idx]
                used_extracted_indexes.add(matched_idx)
            elif i < len(data.get("our_team", [])) and i not in used_extracted_indexes:
                extracted_player = data["our_team"][i]
                used_extracted_indexes.add(i)

            if extracted_player:
                # Calculate opponent stats for this position
                opp_at_position = data["opp_team"][i] if i < len(data["opp_team"]) else {}
                pa = opp_at_position.get("pts", 0)

                stats = {
                    "playerId": roster_player["id"],
                    "played": True,
                    "pts": extracted_player.get("pts", 0),
                    "reb": extracted_player.get("reb", 0),
                    "ast": extracted_player.get("ast", 0),
                    "to": extracted_player.get("to", 0),
                    "fgm": extracted_player.get("fgm", 0),
                    "fga": extracted_player.get("fga", 0),
                    "tpm": extracted_player.get("tpm", 0),
                    "tpa": extracted_player.get("tpa", 0),
                    "stl": extracted_player.get("stl", 0),
                    "blk": extracted_player.get("blk", 0),
                    "ftm": extracted_player.get("ftm", 0),
                    "fta": extracted_player.get("fta", 0),
                    "fouls": extracted_player.get("fouls", 0),
                    "min": extracted_player.get("min", 0),
                    "pa": pa,
                    "pd": extracted_player.get("pts", 0) - pa,
                    "fgpct": round(extracted_player["fgm"]/extracted_player["fga"]*100, 1) if extracted_player.get("fga", 0) > 0 else None,
                    "tppct": round(extracted_player["tpm"]/extracted_player["tpa"]*100, 1) if extracted_player.get("tpa", 0) > 0 else None,
                    "ftpct": round(extracted_player["ftm"]/extracted_player["fta"]*100, 1) if extracted_player.get("fta", 0) > 0 else None,
                    "oppFgm": opp_at_position.get("fgm", 0),
                    "oppFga": opp_at_position.get("fga", 0),
                    "oppFgpct": round(opp_at_position["fgm"]/opp_at_position["fga"]*100, 1) if opp_at_position.get("fga", 0) > 0 else None,
                    "oppTpm": opp_at_position.get("tpm", 0),
                    "oppTpa": opp_at_position.get("tpa", 0),
                    "oppTppct": round(opp_at_position["tpm"]/opp_at_position["tpa"]*100, 1) if opp_at_position.get("tpa", 0) > 0 else None,
                }
                player_stats.append(stats)
            else:
                player_stats.append(None)

        # Build opponent stats array
        opp_stats = []
        for i in range(5):
            if i < len(data["opp_team"]):
                opp_stats.append({
                    "pts": data["opp_team"][i].get("pts", 0),
                    "fgm": data["opp_team"][i].get("fgm", 0),
                    "fga": data["opp_team"][i].get("fga", 0),
                    "tpm": data["opp_team"][i].get("tpm", 0),
                    "tpa": data["opp_team"][i].get("tpa", 0),
                })
            else:
                opp_stats.append({"pts": 0, "fgm": 0, "fga": 0, "tpm": 0, "tpa": 0})

        game = {
            "id": int(datetime.now().timestamp() * 1000) + len(games),
            "date": game_date,
            "result": data.get("result", "L"),
            "ourScore": data.get("our_score", 0),
            "oppScore": data.get("opp_score", 0),
            "playerStats": player_stats,
            "oppStats": opp_stats,
            "screenshotPath": f"screenshots/Season_1/April/{screenshot_path.name}"
        }

        games.append(game)
        print(f"  ✅ {data['result']} {data['our_score']}-{data['opp_score']} on {game_date}")

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        continue

    print()

# Build final state object
state = {
    "roster": roster,
    "games": games
}

# Save to JSON file
output_file = "recovered_games.json"
with open(output_file, 'w') as f:
    json.dump(state, f, indent=2)

print(f"✅ Recovered {len(games)} games!")
print(f"📁 Saved to: {output_file}")
print()
print("To restore:")
print("1. Go to Roster tab in the app")
print("2. Click 📤 Import Data")
print(f"3. Select {output_file}")
