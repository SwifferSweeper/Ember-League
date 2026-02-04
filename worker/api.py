import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from cloudflare_workers import Request, Response

# Import database functions
from database import (
    execute_query, execute_update, get_session, set_session, delete_session,
    create_session, hash_password, verify_password, get_current_timestamp,
    json_response, error_response, validate_request_json, require_admin
)

# Import Riot client
from riot_client import get_riot_client

# Import configuration
from config import config

# Helper functions for stats calculation

def calculate_kda(kills: int, deaths: int, assists: int) -> float:
    """Calculate KDA ratio."""
    if deaths == 0:
        return kills + assists
    return (kills + assists) / deaths

def calculate_win_rate(wins: int, total_games: int) -> float:
    """Calculate win rate percentage."""
    if total_games == 0:
        return 0.0
    return (wins / total_games) * 100

def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# API Routes

async def handle_teams(request: Request, session: Dict[str, Any]) -> Response:
    """Handle teams API requests."""
    if request.method == "GET":
        # Get all teams
        teams = execute_query("SELECT * FROM teams ORDER BY name")
        for team in teams:
            team["players"] = execute_query(
                "SELECT * FROM players WHERE id IN (" +
                ",".join([str(p) for p in team["players"]]) +
                ")"
            )
        return json_response([dict(t) for t in teams])
    
    elif request.method == "POST":
        # Create new team
        data = validate_request_json(request)
        if not data or not data.get("team_name"):
            return error_response("Team name is required", 400)
        
        team_name = data["team_name"][:100]  # Limit length
        
        # Check if team exists
        existing = execute_query("SELECT * FROM teams WHERE name = ?", (team_name,))
        if existing:
            return error_response("Team name already exists", 400)
        
        # Create team
        team_id = execute_update(
            "INSERT INTO teams (name, created_at) VALUES (?, ?)",
            (team_name, get_current_timestamp())
        )
        
        # Create players and add to team
        players = data.get("players", [])
        for player_data in players:
            game_name = player_data.get("game_name", "")[:50]
            tag_line = player_data.get("tag_line", "")[:50]
            region = player_data.get("region", "na1")[:10]
            
            if not game_name or not tag_line:
                continue
            
            # Get PUUID from Riot API
            puuid = None
            riot_client = get_riot_client()
            if riot_client:
                try:
                    puuid = riot_client.get_puuid_from_riot_id(game_name, tag_line, region)
                except:
                    pass
            
            # Check if player exists
            player = execute_query(
                "SELECT * FROM players WHERE game_name = ? AND tag_line = ?",
                (game_name, tag_line)
            )
            
            if not player:
                player_id = execute_update(
                    "INSERT INTO players (puuid, game_name, tag_line, region, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (puuid, game_name, tag_line, region, get_current_timestamp())
                )
            else:
                player_id = player[0]["id"]
                # Update PUUID if we got one
                if puuid and not player[0]["puuid"]:
                    execute_update(
                        "UPDATE players SET puuid = ? WHERE id = ?",
                        (puuid, player_id)
                    )
            
            # Add player to team
            execute_update(
                "INSERT INTO team_players (team_id, player_id) VALUES (?, ?)",
                (team_id, player_id)
            )
        
        return json_response({"message": "Team created successfully", "team_id": team_id}, 201)
    
    return error_response("Method not allowed", 405)

async def handle_team_detail(request: Request, session: Dict[str, Any], team_id: int) -> Response:
    """Handle team detail API requests."""
    if request.method == "GET":
        # Get team details
        team = execute_query("SELECT * FROM teams WHERE id = ?", (team_id,))
        if not team:
            return error_response("Team not found", 404)
        
        team = team[0]
        team["players"] = execute_query(
            "SELECT * FROM players WHERE id IN (" +
            ",".join([str(p) for p in team["players"]]) +
            ")"
        )
        
        # Get team stats
        stats = {
            "wins": 0,
            "losses": 0,
            "total_games": 0,
            "win_rate": 0.0,
            "avg_kda": 0.0
        }
        
        return json_response({"team": team, "players": team["players"], "stats": stats})
    
    elif request.method == "PUT":
        # Update team
        if not session.get("admin_id"):
            return error_response("Admin access required", 403)
        
        data = validate_request_json(request)
        if not data or not data.get("team_name"):
            return error_response("Team name is required", 400)
        
        team_name = data["team_name"][:100]
        
        # Check if name exists (excluding current team)
        existing = execute_query(
            "SELECT * FROM teams WHERE name = ? AND id != ?",
            (team_name, team_id)
        )
        if existing:
            return error_response("Team name already exists", 400)
        
        # Update team
        execute_update(
            "UPDATE teams SET name = ? WHERE id = ?",
            (team_name, team_id)
        )
        
        return json_response({"message": "Team updated successfully"})
    
    elif request.method == "DELETE":
        # Delete team
        if not session.get("admin_id"):
            return error_response("Admin access required", 403)
        
        # Get player IDs that are only on this team
        players_to_delete = []
        team_players = execute_query(
            "SELECT player_id FROM team_players WHERE team_id = ?",
            (team_id,)
        )
        
        for player in team_players:
            other_teams = execute_query(
                "SELECT * FROM team_players WHERE player_id = ? AND team_id != ?",
                (player["player_id"], team_id)
            )
            if not other_teams:
                players_to_delete.append(player["player_id"])
        
        # Delete team first (removes associations)
        execute_update("DELETE FROM teams WHERE id = ?", (team_id,))
        
        # Delete players that are no longer on any team
        for player_id in players_to_delete:
            execute_update("DELETE FROM players WHERE id = ?", (player_id,))
        
        return json_response({"message": "Team deleted successfully"})
    
    return error_response("Method not allowed", 405)

async def handle_players(request: Request, session: Dict[str, Any]) -> Response:
    """Handle players API requests."""
    if request.method == "GET":
        # Get all players
        players = execute_query("SELECT * FROM players ORDER BY game_name")
        return json_response([dict(p) for p in players])
    
    return error_response("Method not allowed", 405)

async def handle_matches(request: Request, session: Dict[str, Any]) -> Response:
    """Handle matches API requests."""
    if request.method == "GET":
        # Get all matches
        matches = execute_query("SELECT * FROM matches ORDER BY created_at DESC LIMIT 50")
        return json_response([dict(m) for m in matches])
    
    return error_response("Method not allowed", 405)

async def handle_match_detail(request: Request, session: Dict[str, Any], match_id: str) -> Response:
    """Handle match detail API requests."""
    if request.method == "GET":
        # Get match details
        match = execute_query("SELECT * FROM matches WHERE match_id = ?", (match_id,))
        if not match:
            return error_response("Match not found", 404)
        
        match = match[0]
        participants = execute_query(
            "SELECT * FROM match_participants WHERE match_id = ?",
            (match["id"],)
        )
        
        # Get player names for participants
        players = {}
        for p in participants:
            player = execute_query(
                "SELECT * FROM players WHERE puuid = ?",
                (p["puuid"],)
            )
            if player:
                players[p["puuid"]] = player[0]
        
        return json_response({"match": match, "participants": participants, "players": players})
    
    return error_response("Method not allowed", 405)

async def handle_collect_matches(request: Request, session: Dict[str, Any]) -> Response:
    """Handle match collection API requests."""
    if request.method == "POST":
        # Trigger match collection
        riot_client = get_riot_client()
        if not riot_client:
            return error_response("Riot API not configured", 400)
        
        # Collect matches for all players
        new_matches = 0
        players = execute_query("SELECT * FROM players WHERE puuid IS NOT NULL")
        
        for player in players:
            # Get recent matches from Riot API
            try:
                matches = riot_client.get_matchlist(player["puuid"], player["region"])
                for match in matches:
                    # Check if match already exists
                    existing = execute_query(
                        "SELECT * FROM matches WHERE match_id = ?",
                        (match["metadata"]["matchId"],)
                    )
                    if not existing:
                        # Insert match
                        match_id = execute_update(
                            "INSERT INTO matches (match_id, game_mode, queue_id, "
                            "duration, created_at, game_version, platform_id) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                match["metadata"]["matchId"],
                                match["info"]["gameMode"],
                                match["info"]["queueId"],
                                match["info"]["gameDuration"],
                                match["info"]["gameStartTimestamp"],
                                match["info"]["gameVersion"],
                                match["info"]["platformId"]
                            )
                        )
                        
                        # Insert participants
                        for participant in match["info"]["participants"]:
                            execute_update(
                                "INSERT INTO match_participants "
                                "(match_id, puuid, champion_id, kills, deaths, assists, "
                                "win, team_id, individual_position, champion_name) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    match_id,
                                    participant["puuid"],
                                    participant["championId"],
                                    participant["kills"],
                                    participant["deaths"],
                                    participant["assists"],
                                    participant["win"],
                                    participant["teamId"],
                                    participant["individualPosition"],
                                    participant["championName"]
                                )
                            )
                        
                        new_matches += 1
            except Exception as e:
                print(f"Error collecting matches for {player['game_name']}: {e}")
        
        return json_response({"message": "Collection complete", "new_matches": new_matches})
    
    return error_response("Method not allowed", 405)

async def handle_admin_login(request: Request, session: Dict[str, Any]) -> Response:
    """Handle admin login."""
    if request.method == "POST":
        data = validate_request_json(request)
        if not data or not data.get("username") or not data.get("password"):
            return error_response("Username and password are required", 400)
        
        username = data["username"][:50]
        password = data["password"]
        
        # Get admin from database
        admin = execute_query("SELECT * FROM admins WHERE username = ?", (username,))
        if not admin:
            return error_response("Invalid username or password", 401)
        
        admin = admin[0]
        if not verify_password(admin["password"], password):
            return error_response("Invalid username or password", 401)
        
        # Create session
        session_id = create_session()
        session_data = {
            "admin_id": admin["id"],
            "username": admin["username"],
            "created_at": get_current_timestamp()
        }
        set_session(session_id, session_data)
        
        return json_response({"message": "Login successful", "session_id": session_id})
    
    return error_response("Method not allowed", 405)

async def handle_admin_logout(request: Request, session: Dict[str, Any]) -> Response:
    """Handle admin logout."""
    if request.method == "POST":
        session_id = request.headers.get("x-session-id")
        if session_id:
            delete_session(session_id)
        
        return json_response({"message": "Logged out successfully"})
    
    return error_response("Method not allowed", 405)

# Main request handler
async def handle_request(request: Request) -> Response:
    """Main request handler for Cloudflare Workers."""
    try:
        # Parse the request path
        path = request.url.split("?")[0]
        path_parts = path.split("/")
        
        # Get session
        session_id = request.headers.get("x-session-id")
        session = {}
        if session_id:
            session = get_session(session_id) or {}
        
        # Handle API routes
        if path.startswith("/api"):
            if path == "/api/teams":
                return await handle_teams(request, session)
            elif path.startswith("/api/teams/") and "/" in path[len("/api/teams/"):]:
                team_id = int(path.split("/")[3])
                return await handle_team_detail(request, session, team_id)
            elif path == "/api/players":
                return await handle_players(request, session)
            elif path == "/api/matches":
                return await handle_matches(request, session)
            elif path.startswith("/api/matches/"):
                match_id = path.split("/")[3]
                return await handle_match_detail(request, session, match_id)
            elif path == "/api/collect":
                return await handle_collect_matches(request, session)
            elif path == "/api/admin/login":
                return await handle_admin_login(request, session)
            elif path == "/api/admin/logout":
                return await handle_admin_logout(request, session)
            
            return error_response("Endpoint not found", 404)
        
        # Handle static files
        if path.startswith("/static/"):
            # Serve static files from R2 or return 404
            return Response(status=404)
        
        # Handle HTML pages
        if path == "/" or path == "":
            # Serve index.html
            return Response(
                body=open("league_tracker/templates/index.html").read(),
                headers={"Content-Type": "text/html"}
            )
        
        # Handle other HTML pages
        if path.startswith("/templates/"):
            template_path = path[len("/templates/"):]
            if Path(f"league_tracker/templates/{template_path}").exists():
                return Response(
                    body=open(f"league_tracker/templates/{template_path}").read(),
                    headers={"Content-Type": "text/html"}
                )
        
        return error_response("Endpoint not found", 404)
        
    except Exception as e:
        print(f"Error handling request: {e}")
        return error_response("Internal server error", 500)

# Main entry point
async def fetch(request: Request, env: Dict[str, Any], ctx: Dict[str, Any]) -> Response:
    """Main entry point for Cloudflare Workers."""
    return await handle_request(request)