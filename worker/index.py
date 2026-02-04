import json
from cloudflare_workers import Request, Response

# Import the main API handler
from riot_client import get_riot_client

# Import configuration
from config import config

# Main entry point for Cloudflare Workers
async def fetch(request: Request, env: dict, ctx: dict) -> Response:
    """Main entry point for Cloudflare Workers."""
    
    # Store env bindings in Flask app config for later use
    config.CLOUDFLARE_ENV = env
    config.CLOUDFLARE_CTX = ctx
    
    # Call the main API handler
    return await fetch(request, env, ctx)

# Export for Cloudflare Workers
__all__ = ["fetch"]

# Scheduled function for background tasks
async def scheduled(event: dict, env: dict, ctx: dict) -> None:
    """Scheduled function for background tasks like match collection."""
    
    # Check if auto-collect is enabled
    if not config.AUTO_COLLECT_ENABLED:
        print("Auto-collect is disabled")
        return
    
    # Get Riot client
    riot_client = get_riot_client()
    if not riot_client:
        print("Riot API not configured")
        return
    
    # Collect matches for all players
    print("Starting scheduled match collection...")
    
    # Get database connection
    conn = env["DB"].connection()
    cursor = conn.cursor()
    
    # Get all players with PUUID
    cursor.execute("SELECT * FROM players WHERE puuid IS NOT NULL")
    players = cursor.fetchall()
    
    new_matches = 0
    for player in players:
        try:
            # Get recent matches from Riot API
            match_ids = riot_client.get_matchlist(player["puuid"], player["region"])
            for match_id in match_ids:
                # Check if match already exists
                cursor.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,))
                if not cursor.fetchone():
                    # Insert match (simplified for this example)
                    cursor.execute("""
                        INSERT INTO matches (match_id, game_mode, queue_id, 
                        duration, created_at, game_version, platform_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        match_id,
                        "unknown",
                        0,
                        0,
                        "1970-01-01T00:00:00Z",
                        "unknown",
                        "unknown"
                    ))
                    new_matches += 1
        except Exception as e:
            print(f"Error collecting matches for {player['game_name']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"Scheduled collection complete. New matches: {new_matches}")

# Export scheduled function
__all__ += ["scheduled"]