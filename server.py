#!/usr/bin/env python3
"""
NBA 2K26 Stats Tracker - Flask Backend
Handles Anthropic API calls for screenshot extraction
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
import os
import base64
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import json
import re

# Load .env file if it exists
load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS for local development

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# Data persistence files
DATA_FILE = Path("data/rec_stats.json")
RECOVERED_FILE = Path("recovered_games.json")
SEASON_FOLDERS = {
    "2k26_s1": "Season_1",
    "2k27_s2": "Season_2",
}
DEFAULT_SEASON_ID = "2k27_s2"


def validate_extracted_box_score(parsed_data):
    """
    Validate extracted AI box score data and return reliability signals.
    """
    warnings = []
    critical = []

    our_team = parsed_data.get("our_team") or []
    opp_team = parsed_data.get("opp_team") or []

    if len(our_team) != 5:
        warnings.append(f"Expected 5 players for our_team, got {len(our_team)}")
    if len(opp_team) != 5:
        warnings.append(f"Expected 5 players for opp_team, got {len(opp_team)}")

    def check_team(team_label, players):
        for idx, player in enumerate(players):
            name = player.get("name", f"Player {idx + 1}")

            for stat_key in ["pts", "reb", "ast", "stl", "blk", "to", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "fouls", "min"]:
                value = player.get(stat_key, 0)
                if isinstance(value, (int, float)) and value < 0:
                    critical.append(f"{team_label}[{idx}] {name}: negative {stat_key}={value}")

            fgm = player.get("fgm", 0) or 0
            fga = player.get("fga", 0) or 0
            tpm = player.get("tpm", 0) or 0
            tpa = player.get("tpa", 0) or 0
            ftm = player.get("ftm", 0) or 0
            fta = player.get("fta", 0) or 0
            pts = player.get("pts", 0) or 0

            if fgm > fga:
                critical.append(f"{team_label}[{idx}] {name}: FGM ({fgm}) > FGA ({fga})")
            if tpm > tpa:
                critical.append(f"{team_label}[{idx}] {name}: 3PM ({tpm}) > 3PA ({tpa})")
            if ftm > fta:
                critical.append(f"{team_label}[{idx}] {name}: FTM ({ftm}) > FTA ({fta})")

            estimated_pts = (fgm - tpm) * 2 + tpm * 3 + ftm
            if abs(estimated_pts - pts) >= 4:
                warnings.append(
                    f"{team_label}[{idx}] {name}: points mismatch (listed {pts}, shooting implies {estimated_pts})"
                )

            if pts > 70:
                warnings.append(f"{team_label}[{idx}] {name}: unusually high points ({pts})")
            if fga > 60 or tpa > 30:
                warnings.append(f"{team_label}[{idx}] {name}: unusually high attempts (FGA {fga}, 3PA {tpa})")

    check_team("our_team", our_team)
    check_team("opp_team", opp_team)

    our_score = parsed_data.get("our_score")
    opp_score = parsed_data.get("opp_score")
    result = parsed_data.get("result")

    if isinstance(our_score, (int, float)) and our_team:
        our_sum = sum((p.get("pts", 0) or 0) for p in our_team)
        if abs(our_sum - our_score) >= 4:
            warnings.append(f"our_score mismatch (listed {our_score}, player sum {our_sum})")

    if isinstance(opp_score, (int, float)) and opp_team:
        opp_sum = sum((p.get("pts", 0) or 0) for p in opp_team)
        if abs(opp_sum - opp_score) >= 4:
            warnings.append(f"opp_score mismatch (listed {opp_score}, player sum {opp_sum})")

    if isinstance(our_score, (int, float)) and isinstance(opp_score, (int, float)):
        expected_result = "W" if our_score > opp_score else "L" if our_score < opp_score else "OT"
        if result in ["W", "L", "OT"] and result != expected_result:
            warnings.append(
                f"result mismatch (listed {result}, expected {expected_result} from {our_score}-{opp_score})"
            )

    # Confidence: heavily penalize critical integrity issues.
    confidence = max(0, 100 - (len(critical) * 20) - (len(warnings) * 6))

    return {
        "confidence": confidence,
        "hasCritical": len(critical) > 0,
        "criticalIssues": critical,
        "warnings": warnings,
    }

def sync_to_recovered_games(state_data):
    """
    Sync the current state to recovered_games.json
    This keeps a backup that matches the recovery script format
    """
    try:
        # Write to recovered_games.json
        with open(RECOVERED_FILE, 'w') as f:
            json.dump(state_data, f, indent=2)
        print(f"🔄 Synced to recovered_games.json: {len(state_data.get('games', []))} games")
    except Exception as e:
        print(f"⚠️  Failed to sync to recovered_games.json: {e}")


def load_tracker_state_for_query():
    """Load tracker state for stats queries."""
    if not DATA_FILE.exists():
        return {
            "roster": [
                {'id': 'p1', 'name': 'AubreyArchAngel', 'position': 'PG'},
                {'id': 'p2', 'name': 'HoldMyBir', 'position': 'SG'},
                {'id': 'p3', 'name': 'KingxMarsh', 'position': 'SF'},
                {'id': 'p4', 'name': 'SkyWalkerX007', 'position': 'PF'},
                {'id': 'p5', 'name': 'Bari_JB', 'position': 'C'}
            ],
            "games": []
        }

    with open(DATA_FILE, 'r') as f:
        return json.load(f)


def normalize_season_id(game=None):
    game = game or {}
    season_id = game.get("seasonId")
    if season_id in SEASON_FOLDERS:
        return season_id

    screenshot_path = game.get("screenshotPath") or ""
    if "Season_2" in screenshot_path:
        return "2k27_s2"

    return "2k26_s1"


def normalize_query_text(text):
    return re.sub(r'[^a-z0-9]', '', (text or '').lower())


def resolve_player_from_query(query_text, roster):
    """
    Resolve player by fuzzy matching a roster name in the query.
    Returns roster entry or None.
    """
    q_norm = normalize_query_text(query_text)
    best = None
    best_score = 0

    for player in roster:
        name = player.get('name', '')
        name_norm = normalize_query_text(name)
        if not name_norm:
            continue

        score = 0
        if name_norm in q_norm:
            score = len(name_norm)
        else:
            # Token-level partial fallback (e.g., holdmybir -> hold)
            for token in re.findall(r'[a-z0-9]+', name.lower()):
                token_norm = normalize_query_text(token)
                if token_norm and token_norm in q_norm:
                    score = max(score, len(token_norm))

        if score > best_score:
            best_score = score
            best = player

    return best if best_score >= 3 else None


def extract_stat_key(query_text):
    q = (query_text or '').lower()
    stat_aliases = [
        ('pts', ['point', 'points', 'pts', 'score', 'scored']),
        ('reb', ['rebound', 'rebounds', 'reb']),
        ('ast', ['assist', 'assists', 'ast']),
        ('stl', ['steal', 'steals', 'stl']),
        ('blk', ['block', 'blocks', 'blk']),
        ('to', ['turnover', 'turnovers', 'to']),
        ('pa', ['points allowed', 'allowed', 'pa']),
        ('pd', ['point differential', 'plus minus', 'plus-minus', 'pd']),
        ('fgm', ['fgm', 'field goals made']),
        ('fga', ['fga', 'field goals attempted', 'field goal attempts']),
        ('tpm', ['3pm', 'threes made', 'three pointers made']),
        ('tpa', ['3pa', 'threes attempted', 'three pointers attempted']),
        ('ftm', ['ftm', 'free throws made']),
        ('fta', ['fta', 'free throws attempted']),
        ('min', ['minutes', 'mins', 'min'])
    ]

    for key, words in stat_aliases:
        if any(word in q for word in words):
            return key

    return None


def extract_condition(query_text):
    """Extract comparator/value from natural language."""
    q = (query_text or '').lower()

    between_match = re.search(r'between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)', q)
    if between_match:
        lo = float(between_match.group(1))
        hi = float(between_match.group(2))
        return {'op': 'between', 'value': (min(lo, hi), max(lo, hi))}

    patterns = [
        ('lte', r'(?:at most|no more than|up to)\s*(\d+(?:\.\d+)?)'),
        ('lt', r'(?:fewer than|less than|under|below)\s*(\d+(?:\.\d+)?)'),
        ('gte', r'(?:at least|no less than|minimum of|min)\s*(\d+(?:\.\d+)?)'),
        ('gt', r'(?:more than|greater than|over|above)\s*(\d+(?:\.\d+)?)'),
        ('eq', r'(?:exactly|equal to|equals|=)\s*(\d+(?:\.\d+)?)')
    ]

    for op, pattern in patterns:
        match = re.search(pattern, q)
        if match:
            return {'op': op, 'value': float(match.group(1))}

    symbol_match = re.search(r'(<=|>=|<|>|=)\s*(\d+(?:\.\d+)?)', q)
    if symbol_match:
        symbol = symbol_match.group(1)
        num = float(symbol_match.group(2))
        op = {'<=': 'lte', '>=': 'gte', '<': 'lt', '>': 'gt', '=': 'eq'}.get(symbol)
        return {'op': op, 'value': num}

    return None


def evaluate_condition(value, condition):
    op = condition.get('op')
    comp = condition.get('value')

    if op == 'lt':
        return value < comp
    if op == 'lte':
        return value <= comp
    if op == 'gt':
        return value > comp
    if op == 'gte':
        return value >= comp
    if op == 'eq':
        return value == comp
    if op == 'between':
        return comp[0] <= value <= comp[1]
    return False


def condition_label(condition):
    op = condition.get('op')
    val = condition.get('value')

    if op == 'between':
        return f"between {val[0]:g} and {val[1]:g}"

    prefix = {
        'lt': 'less than',
        'lte': 'at most',
        'gt': 'more than',
        'gte': 'at least',
        'eq': 'exactly'
    }.get(op, 'matching')

    return f"{prefix} {val:g}"


def detect_matchup_points_allowed_query(query_text):
    """
    Detect intent to compare a player's points against points allowed (PTS vs PA).
    Returns comparator op string or None.
    """
    q = (query_text or '').lower()

    # Symbol forms like: pts > pa, points >= points allowed
    symbol_match = re.search(
        r'(?:pts?|points?)\s*(<=|>=|<|>|=)\s*(?:pa|(?:poi\w*|points?)\s*allowed)',
        q
    )
    if symbol_match:
        return {'<=': 'lte', '>=': 'gte', '<': 'lt', '>': 'gt', '=': 'eq'}.get(symbol_match.group(1))

    # Natural language forms
    if re.search(r'outscor\w+\s+(?:his|her|their)?\s*matchup', q):
        return 'gt'

    if re.search(r'more\s+points?\s+than\s+(?:his|her|their)?\s*(?:pa|(?:poi\w*|points?)\s*allowed|matchup)', q):
        return 'gt'

    if re.search(r'(?:fewer|less)\s+points?\s+than\s+(?:his|her|their)?\s*(?:pa|(?:poi\w*|points?)\s*allowed|matchup)', q):
        return 'lt'

    if re.search(r'(?:equal|same)\s+(?:points?|pts?)\s+as\s+(?:his|her|their)?\s*(?:pa|(?:poi\w*|points?)\s*allowed|matchup)', q):
        return 'eq'

    # Phrases that strongly imply points-vs-allowed comparison.
    if 'points allowed' in q or 'poins allowed' in q or 'pa' in q:
        if 'outscor' in q:
            return 'gt'

    return None


def extract_result_filter(query_text):
    """Extract optional game result filter from query text."""
    q = (query_text or '').lower()

    win_terms = ['win only', 'wins only', 'in wins', 'when they won', 'in a win', 'on wins']
    loss_terms = ['loss only', 'losses only', 'in losses', 'when they lost', 'in a loss', 'on losses']
    ot_terms = ['ot only', 'overtime only', 'in ot', 'in overtime']

    if any(term in q for term in win_terms):
        return 'W'
    if any(term in q for term in loss_terms):
        return 'L'
    if any(term in q for term in ot_terms):
        return 'OT'

    return None


def extract_matchup_margin_condition(query_text):
    """
    Extract optional margin condition for PTS vs PA queries.
    Example: "outscored by at least 5" -> {'op': 'gte', 'value': 5}
    """
    q = (query_text or '').lower()

    patterns = [
        ('gte', r'by\s+(?:at\s+least|no\s+less\s+than|minimum\s+of|min)\s*(\d+(?:\.\d+)?)'),
        ('gt', r'by\s+(?:more\s+than|over|above)\s*(\d+(?:\.\d+)?)'),
        ('lte', r'by\s+(?:at\s+most|no\s+more\s+than|up\s+to)\s*(\d+(?:\.\d+)?)'),
        ('lt', r'by\s+(?:less\s+than|under|below)\s*(\d+(?:\.\d+)?)'),
        ('eq', r'by\s+(?:exactly|equal\s+to)?\s*(\d+(?:\.\d+)?)')
    ]

    for op, pattern in patterns:
        match = re.search(pattern, q)
        if match:
            return {'op': op, 'value': float(match.group(1))}

    plus_match = re.search(r'by\s*(\d+(?:\.\d+)?)\s*\+', q)
    if plus_match:
        return {'op': 'gte', 'value': float(plus_match.group(1))}

    return None


def wants_expanded_match_list(query_text):
    q = (query_text or '').lower()
    triggers = [
        'which games',
        'what games',
        'list games',
        'show games',
        'were those',
        'full list',
        'show all'
    ]
    return any(trigger in q for trigger in triggers)


def extract_sort_mode(query_text):
    """Extract optional sorting preference for match samples."""
    q = (query_text or '').lower()

    if any(token in q for token in ['oldest', 'earliest', 'first games']):
        return 'date_asc'
    if any(token in q for token in ['newest', 'latest', 'recent', 'most recent']):
        return 'date_desc'
    if any(token in q for token in ['largest margin', 'biggest margin', 'highest diff', 'best diff']):
        return 'diff_desc'
    if any(token in q for token in ['smallest margin', 'lowest diff', 'closest margin']):
        return 'diff_asc'

    return None


def sort_rows(rows, mode):
    if mode == 'date_asc':
        return sorted(rows, key=lambda r: r.get('date') or '')
    if mode == 'diff_desc':
        return sorted(rows, key=lambda r: r.get('diff', 0), reverse=True)
    if mode == 'diff_asc':
        return sorted(rows, key=lambda r: r.get('diff', 0))
    # Default newest first.
    return sorted(rows, key=lambda r: r.get('date') or '', reverse=True)


@app.route('/api/stats-query', methods=['POST'])
def stats_query():
    """Answer natural-language stat questions from saved tracker data."""
    try:
        payload = request.get_json() or {}
        query_text = (payload.get('query') or '').strip()
        if not query_text:
            return jsonify({"error": "Missing query text"}), 400

        data = load_tracker_state_for_query()
        roster = data.get('roster', [])
        requested_season_id = payload.get('seasonId') or DEFAULT_SEASON_ID
        games = [
            game for game in data.get('games', [])
            if normalize_season_id(game) == requested_season_id
        ]

        if not games:
            return jsonify({
                "success": True,
                "answer": "No games are logged yet, so there are no stats to query.",
                "matches": 0,
                "samples": []
            })

        player = resolve_player_from_query(query_text, roster)
        stat_key = extract_stat_key(query_text)
        condition = extract_condition(query_text)
        matchup_op = detect_matchup_points_allowed_query(query_text)
        result_filter = extract_result_filter(query_text)
        matchup_margin = extract_matchup_margin_condition(query_text)
        list_all_matches = wants_expanded_match_list(query_text)
        sort_mode = extract_sort_mode(query_text) or 'date_desc'
        q_lower = query_text.lower()

        if not player:
            names = ', '.join([p.get('name', '') for p in roster if p.get('name')])
            return jsonify({
                "success": False,
                "error": "I couldn't match that player name in your roster.",
                "hint": f"Try including one of: {names}"
            }), 400

        # Special comparison intent: "outscored matchup" / PTS vs PA questions.
        if matchup_op:
            comparison_rows = []
            for game in games:
                p_stats = next((ps for ps in (game.get('playerStats') or []) if ps and ps.get('playerId') == player.get('id') and ps.get('played')), None)
                if not p_stats:
                    continue

                if result_filter and game.get('result') != result_filter:
                    continue

                pts = p_stats.get('pts', 0) or 0
                pa = p_stats.get('pa', 0) or 0
                diff = pts - pa

                comparison_rows.append({
                    'date': game.get('date'),
                    'result': game.get('result'),
                    'pts': pts,
                    'pa': pa,
                    'diff': diff,
                    'ourScore': game.get('ourScore'),
                    'oppScore': game.get('oppScore')
                })

            total_games = len(comparison_rows)
            if total_games == 0:
                return jsonify({
                    "success": True,
                    "answer": f"{player.get('name')} has no logged games yet.",
                    "matches": 0,
                    "samples": []
                })

            def compare_pts_pa(row):
                if matchup_op == 'gt':
                    return row['pts'] > row['pa']
                if matchup_op == 'gte':
                    return row['pts'] >= row['pa']
                if matchup_op == 'lt':
                    return row['pts'] < row['pa']
                if matchup_op == 'lte':
                    return row['pts'] <= row['pa']
                if matchup_op == 'eq':
                    return row['pts'] == row['pa']
                return False

            matches = [row for row in comparison_rows if compare_pts_pa(row)]

            if matchup_margin:
                margin_op = matchup_margin.get('op')
                margin_val = matchup_margin.get('value', 0)

                def margin_matches(row):
                    abs_diff = abs(row['diff'])
                    if margin_op == 'lt':
                        return abs_diff < margin_val
                    if margin_op == 'lte':
                        return abs_diff <= margin_val
                    if margin_op == 'gt':
                        return abs_diff > margin_val
                    if margin_op == 'gte':
                        return abs_diff >= margin_val
                    if margin_op == 'eq':
                        return abs_diff == margin_val
                    return True

                matches = [row for row in matches if margin_matches(row)]

            count = len(matches)

            comparator_text = {
                'gt': 'more points than they allowed',
                'gte': 'at least as many points as they allowed',
                'lt': 'fewer points than they allowed',
                'lte': 'no more points than they allowed',
                'eq': 'the same points as they allowed',
            }.get(matchup_op, 'a PTS-vs-PA condition')

            if matchup_margin:
                comparator_text = f"{comparator_text} by {condition_label(matchup_margin)}"

            if result_filter:
                filter_text = {'W': 'in wins', 'L': 'in losses', 'OT': 'in overtime games'}.get(result_filter, '')
                if filter_text:
                    comparator_text = f"{comparator_text} {filter_text}"

            answer = (
                f"{player.get('name')} had {comparator_text} in {count} of {total_games} games."
            )

            sorted_matches = sort_rows(matches, sort_mode)

            return jsonify({
                "success": True,
                "answer": answer,
                "matches": count,
                "meta": {
                    "playerName": player.get('name'),
                    "queryType": "pts_vs_pa",
                    "comparison": matchup_op,
                    "totalGames": total_games,
                    "resultFilter": result_filter,
                    "sortMode": sort_mode
                },
                "samples": sorted_matches
            })

        if not stat_key:
            return jsonify({
                "success": False,
                "error": "I couldn't detect which stat to query.",
                "hint": "Try points, rebounds, assists, steals, blocks, turnovers, points allowed, FG%, or 3P%."
            }), 400

        # Gather this player's game stat rows
        player_rows = []
        for game in games:
            p_stats = next((ps for ps in (game.get('playerStats') or []) if ps and ps.get('playerId') == player.get('id') and ps.get('played')), None)
            if p_stats:
                if result_filter and game.get('result') != result_filter:
                    continue
                player_rows.append({
                    'date': game.get('date'),
                    'result': game.get('result'),
                    'value': p_stats.get(stat_key, 0) or 0,
                    'ourScore': game.get('ourScore'),
                    'oppScore': game.get('oppScore')
                })

        total_games = len(player_rows)
        if total_games == 0:
            return jsonify({
                "success": True,
                "answer": f"{player.get('name')} has no logged games yet.",
                "matches": 0,
                "samples": []
            })

        wants_average = any(token in q_lower for token in ['average', 'avg', 'mean'])
        wants_max = any(token in q_lower for token in ['most', 'highest', 'max', 'career high'])
        wants_min = any(token in q_lower for token in ['least', 'lowest', 'min'])

        if wants_average and not condition:
            avg_value = sum(row['value'] for row in player_rows) / total_games
            answer = (
                f"{player.get('name')} averages {avg_value:.2f} {stat_key.upper()} "
                f"across {total_games} logged games."
            )
            return jsonify({
                "success": True,
                "answer": answer,
                "matches": total_games,
                "meta": {
                    "playerName": player.get('name'),
                    "statKey": stat_key,
                    "queryType": "average",
                    "totalGames": total_games,
                    "average": round(avg_value, 2),
                    "resultFilter": result_filter
                },
                "samples": sorted(player_rows, key=lambda r: r['value'], reverse=True)[:5]
            })

        if wants_max and not condition:
            top = max(player_rows, key=lambda r: r['value'])
            answer = (
                f"{player.get('name')}'s highest {stat_key.upper()} was {top['value']:g} "
                f"on {top['date'] or 'an unknown date'}."
            )
            return jsonify({
                "success": True,
                "answer": answer,
                "matches": 1,
                "meta": {
                    "playerName": player.get('name'),
                    "statKey": stat_key,
                    "queryType": "max",
                    "totalGames": total_games,
                    "value": top['value'],
                    "resultFilter": result_filter
                },
                "samples": [top]
            })

        if wants_min and not condition:
            low = min(player_rows, key=lambda r: r['value'])
            answer = (
                f"{player.get('name')}'s lowest {stat_key.upper()} was {low['value']:g} "
                f"on {low['date'] or 'an unknown date'}."
            )
            return jsonify({
                "success": True,
                "answer": answer,
                "matches": 1,
                "meta": {
                    "playerName": player.get('name'),
                    "statKey": stat_key,
                    "queryType": "min",
                    "totalGames": total_games,
                    "value": low['value'],
                    "resultFilter": result_filter
                },
                "samples": [low]
            })

        # Default mode for count-style questions: use explicit condition or infer simple threshold.
        if not condition:
            inferred = re.search(r'(\d+(?:\.\d+)?)', q_lower)
            if inferred and any(token in q_lower for token in ['how many', 'count', 'times']):
                condition = {'op': 'eq', 'value': float(inferred.group(1))}
            else:
                return jsonify({
                    "success": False,
                    "error": "I found the player and stat but couldn't detect a condition.",
                    "hint": "Try phrasing like 'fewer than 2', 'at least 10', or 'exactly 5'."
                }), 400

        matches = [row for row in player_rows if evaluate_condition(row['value'], condition)]
        count = len(matches)
        label = condition_label(condition)

        answer = (
            f"{player.get('name')} recorded {stat_key.upper()} {label} in {count} of {total_games} games."
        )

        return jsonify({
            "success": True,
            "answer": answer,
            "matches": count,
            "meta": {
                "playerName": player.get('name'),
                "statKey": stat_key,
                "queryType": "count",
                "condition": condition,
                "totalGames": total_games,
                "resultFilter": result_filter,
                "sortMode": sort_mode
            },
            "samples": sort_rows(matches, sort_mode)
        })

    except Exception as e:
        return jsonify({"error": f"Stats query failed: {str(e)}"}), 500

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'nba2k26_tracker.html')

@app.route('/nba2k26_tracker.html')
def tracker():
    """Serve the main HTML file"""
    return send_from_directory('.', 'nba2k26_tracker.html')

@app.route('/headshots/<path:filename>')
def serve_headshot(filename):
    """Serve player headshot images"""
    return send_from_directory('headshots', filename)

@app.route('/headshots/<path:filename>')
def headshots(filename):
    """Serve player headshots"""
    return send_from_directory('headshots', filename)

@app.route('/screenshots/<path:filepath>')
def serve_screenshot(filepath):
    """Serve game screenshots"""
    # filepath will be like "Season_1/April/game_20260415_180530.jpg"
    return send_from_directory('screenshots', filepath)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Server is running"})

@app.route('/api/save-screenshot', methods=['POST'])
def save_screenshot():
    """
    Save a screenshot to the filesystem
    Expects JSON: {"image": "base64_encoded_image_data"}
    Returns: {"success": true, "screenshotPath": "screenshots/..."}
    """
    try:
        data = request.get_json()

        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400

        image_b64 = data['image']
        season_id = data.get('seasonId') or DEFAULT_SEASON_ID
        season_folder = SEASON_FOLDERS.get(season_id, SEASON_FOLDERS[DEFAULT_SEASON_ID])

        # Save screenshot to appropriate month folder
        current_month = datetime.now().strftime("%B")  # e.g., "April"
        screenshot_dir = Path("screenshots") / season_folder / current_month
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_{timestamp}.jpg"
        filepath = screenshot_dir / filename

        # Decode and save image
        image_data = base64.b64decode(image_b64)
        with open(filepath, 'wb') as f:
            f.write(image_data)

        print(f"📸 Screenshot saved: {filepath}")

        # Store relative path for client
        screenshot_path = f"screenshots/{season_folder}/{current_month}/{filename}"

        return jsonify({
            "success": True,
            "screenshotPath": screenshot_path
        })

    except Exception as e:
        return jsonify({"error": f"Failed to save screenshot: {str(e)}"}), 500

@app.route('/api/save-state', methods=['POST'])
def save_state():
    """
    Save the entire application state to a file
    Expects JSON: {"roster": [...], "games": [...]}
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Ensure data directory exists
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Save to file
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"💾 State saved: {len(data.get('games', []))} games")

        # Also sync to recovered_games.json as backup
        sync_to_recovered_games(data)

        return jsonify({
            "success": True,
            "message": f"Saved {len(data.get('games', []))} games"
        })

    except Exception as e:
        return jsonify({"error": f"Failed to save state: {str(e)}"}), 500

@app.route('/api/load-state', methods=['GET'])
def load_state():
    """
    Load the application state from file
    Returns: {"roster": [...], "games": [...]}
    """
    try:
        # Check if file exists
        if not DATA_FILE.exists():
            # Return default state
            default_roster = [
                {'id':'p1', 'name':'AubreyArchAngel', 'position':'PG'},
                {'id':'p2', 'name':'HoldMyBir', 'position':'SG'},
                {'id':'p3', 'name':'KingxMarsh', 'position':'SF'},
                {'id':'p4', 'name':'SkyWalkerX007', 'position':'PF'},
                {'id':'p5', 'name':'Bari_JB', 'position':'C'}
            ]
            return jsonify({
                "roster": default_roster,
                "games": []
            })

        # Load from file
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)

        print(f"📂 State loaded: {len(data.get('games', []))} games")

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": f"Failed to load state: {str(e)}"}), 500

@app.route('/extract-stats', methods=['POST'])
def extract_stats():
    """
    Extract NBA 2K26 stats from a screenshot
    Expects JSON: {"image": "base64_encoded_image_data"}
    """
    try:
        data = request.get_json()

        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400

        image_b64 = data['image']

        # Call Claude API with vision
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
                        "text": """You are analyzing an NBA 2K26 Rec Center box score screenshot. Extract ALL visible player statistics with high accuracy.

NBA 2K26 BOX SCORE LAYOUT:
- You will see TWO separate tables: "Away Team" (top) and "Home Team" (bottom)
- Each table has exactly 5 player rows
- Players are listed in positional order from top to bottom (Position 1, 2, 3, 4, 5)

CRITICAL EXTRACTION RULES:
1. **READ EACH TABLE TOP-TO-BOTTOM, ROW BY ROW**
2. The FIRST row in a table = array index 0 (Position 1)
3. The SECOND row = array index 1 (Position 2)
4. The THIRD row = array index 2 (Position 3)
5. The FOURTH row = array index 3 (Position 4)
6. The FIFTH row = array index 4 (Position 5)
7. **DO NOT alphabetize, sort by stats, or reorder players in ANY way**
8. Extract players in the EXACT visual order you see them in the table

READING PLAYER DATA:
- Read ACROSS each row from left to right: NAME, then stats columns
- Match each stat to its column header (GRD, PTS, REB, AST, STL, BLK, FOULS, TO, FGM/FGA, 3PM/3PA, FTM/FTA)
- For shooting: "8/11" means fgm=8, fga=11
- YELLOW HIGHLIGHTED ROWS: Read extra carefully, background can obscure digits
- Player names are gamertags (like "HoldMyBir", "AubreyArchAngel", "KingxMarsh", etc.)

PROCESS:
Step 1: Find the FIRST table (Away Team or top table)
Step 2: Read ROW 1 (top row): Get name and all stats → This becomes our_team[0]
Step 3: Read ROW 2: Get name and all stats → This becomes our_team[1]
Step 4: Read ROW 3: Get name and all stats → This becomes our_team[2]
Step 5: Read ROW 4: Get name and all stats → This becomes our_team[3]
Step 6: Read ROW 5: Get name and all stats → This becomes our_team[4]
Step 7: Repeat for SECOND table (Home Team or bottom table) → opp_team[0-4]

Return ONLY a valid JSON object (no markdown, no code blocks, no explanation):
{
  "our_team": [
    {"name":"Player1Name","pts":12,"reb":5,"ast":3,"stl":1,"blk":0,"to":2,"fgm":4,"fga":8,"tpm":1,"tpa":3,"ftm":3,"fta":4,"fouls":2,"min":15},
    {"name":"Player2Name","pts":15,"reb":3,"ast":2,"stl":0,"blk":1,"to":1,"fgm":5,"fga":10,"tpm":2,"tpa":5,"ftm":3,"fta":4,"fouls":1,"min":15},
    {"name":"Player3Name","pts":8,"reb":7,"ast":1,"stl":2,"blk":0,"to":3,"fgm":3,"fga":7,"tpm":0,"tpa":2,"ftm":2,"fta":2,"fouls":3,"min":18},
    {"name":"Player4Name","pts":20,"reb":10,"ast":0,"stl":1,"blk":2,"to":2,"fgm":8,"fga":15,"tpm":1,"tpa":4,"ftm":3,"fta":5,"fouls":2,"min":20},
    {"name":"Player5Name","pts":11,"reb":4,"ast":5,"stl":3,"blk":0,"to":1,"fgm":4,"fga":9,"tpm":1,"tpa":3,"ftm":2,"fta":3,"fouls":1,"min":17}
  ],
  "opp_team": [
    {"name":"Opp1Name","pts":15,"reb":3,"ast":2,"stl":0,"blk":1,"to":1,"fgm":5,"fga":10,"tpm":2,"tpa":5,"ftm":3,"fta":4,"fouls":1,"min":15},
    {"name":"Opp2Name","pts":12,"reb":5,"ast":3,"stl":1,"blk":0,"to":2,"fgm":4,"fga":8,"tpm":1,"tpa":3,"ftm":3,"fta":4,"fouls":2,"min":15},
    {"name":"Opp3Name","pts":18,"reb":2,"ast":4,"stl":2,"blk":1,"to":0,"fgm":7,"fga":12,"tpm":2,"tpa":6,"ftm":2,"fta":2,"fouls":0,"min":19},
    {"name":"Opp4Name","pts":9,"reb":8,"ast":1,"stl":0,"blk":3,"to":2,"fgm":3,"fga":6,"tpm":0,"tpa":1,"ftm":3,"fta":4,"fouls":4,"min":16},
    {"name":"Opp5Name","pts":14,"reb":6,"ast":2,"stl":1,"blk":0,"to":1,"fgm":5,"fga":11,"tpm":1,"tpa":4,"ftm":3,"fta":3,"fouls":2,"min":18}
  ],
  "our_score":68,
  "opp_score":72,
  "result":"L"
}

CRITICAL - PLAYER ORDER:
- Extract BOTH teams with player names and ALL stats
- "our_team" = the FIRST team you see (could be top or bottom)
- "opp_team" = the SECOND team you see (could be top or bottom)
- BOTH arrays must have exactly 5 players with names IN THE EXACT ORDER THEY APPEAR
- The TOP player in the table = index 0, second player = index 1, third = index 2, fourth = index 3, fifth = index 4
- DO NOT alphabetize, sort by stats, or reorder in any way - maintain the exact visual order from the screenshot
- Use 0 for any stat not clearly visible
- "result" should be "W" for win, "L" for loss, or "OT" if it went to overtime
- Be precise with numbers"""
                    }
                ]
            }]
        )

        # Extract text from response
        result_text = ""
        for block in response.content:
            if block.type == "text":
                result_text = block.text
                break

        # Clean up response (remove markdown code blocks if present)
        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        # Parse JSON
        import json
        try:
            parsed_data = json.loads(result_text)

            validation = validate_extracted_box_score(parsed_data)

            # Log the extracted data for debugging
            print("=" * 60)
            print("AI EXTRACTION RESULT:")
            if parsed_data.get('our_team'):
                print("\nOUR TEAM (in order):")
                for idx, player in enumerate(parsed_data['our_team']):
                    print(f"  [{idx}] {player.get('name', 'Unknown')} - {player.get('pts', 0)} pts")
            if parsed_data.get('opp_team'):
                print("\nOPP TEAM (in order):")
                for idx, player in enumerate(parsed_data['opp_team']):
                    print(f"  [{idx}] {player.get('name', 'Unknown')} - {player.get('pts', 0)} pts")
            print("=" * 60)

            # Don't save screenshot yet - wait until game is saved
            # Just return the parsed data to the client
            return jsonify({
                "success": True,
                "data": parsed_data,
                "validation": validation,
            })
        except json.JSONDecodeError as e:
            return jsonify({
                "error": "Failed to parse AI response",
                "raw_response": result_text
            }), 500

    except anthropic.AuthenticationError:
        return jsonify({"error": "Invalid API key. Please check your ANTHROPIC_API_KEY environment variable."}), 401
    except anthropic.RateLimitError:
        return jsonify({"error": "Rate limit exceeded. Please try again in a moment."}), 429
    except anthropic.APIError as e:
        return jsonify({"error": f"API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  WARNING: ANTHROPIC_API_KEY environment variable not set!")
        print("Please set it with: export ANTHROPIC_API_KEY='your-api-key'")

    print("🏀 NBA 2K26 Stats Tracker")
    print("📡 Server running on http://localhost:8000")
    print("✅ CORS enabled for local development")

    app.run(debug=True, port=8000, host='0.0.0.0', use_debugger=False)
