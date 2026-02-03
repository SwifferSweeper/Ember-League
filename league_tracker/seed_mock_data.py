"""
Seed script to create mock match data between Ember GOATS and T3G
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app import create_app, db
from src.database import Team, Player, Match, MatchParticipant

def seed_mock_data():
    app = create_app()
    
    with app.app_context():
        # Get existing teams
        ember_goats = Team.query.filter_by(name="Ember GOATS").first()
        if not ember_goats:
            print("Error: Ember GOATS team not found!")
            return
        
        t3g = Team.query.filter_by(name="T3G").first()
        if not t3g:
            print("Error: T3G team not found!")
            return
        
        print(f"Found teams: {ember_goats.name} (ID: {ember_goats.id}), {t3g.name} (ID: {t3g.id})")
        
        # Get players from each team
        ember_players = list(ember_goats.players)
        t3g_players = list(t3g.players)
        
        if len(ember_players) < 5:
            print(f"Warning: Ember GOATS has only {len(ember_players)} players")
        if len(t3g_players) < 5:
            print(f"Warning: T3G has only {len(t3g_players)} players")
        
        print(f"Ember GOATS players: {[p.display_name for p in ember_players]}")
        print(f"T3G players: {[p.display_name for p in t3g_players]}")
        
        # Create a mock match
        match_time = datetime.now() - timedelta(hours=2)
        match_id = f"NA1_{int(match_time.timestamp())}"
        
        match = Match.query.filter_by(match_id=match_id).first()
        if match:
            print(f"Match {match_id} already exists!")
        else:
            match = Match(
                match_id=match_id,
                game_duration=1850,  # ~31 minutes
                game_version="14.1.1",
                game_creation=int(match_time.timestamp() * 1000),
                queue_id=0,
                home_team_id=ember_goats.id,
                away_team_id=t3g.id
            )
            db.session.add(match)
            db.session.commit()
            print(f"Created match: {match_id}")
        
        # Add participants - Ember GOATS wins (Blue side)
        ember_participants = []
        for i, player in enumerate(ember_players[:5]):
            ember_participants.append({
                "puuid": player.puuid,
                "champion_id": 516 + i,  # Different champions
                "champion_name": ["Ornn", "Khazix", "Ahri", "Ashe", "Karma"][i],
                "team_id": 100,
                "win": True,
                "kills": [3, 8, 10, 6, 2][i],
                "deaths": [1, 2, 1, 2, 1][i],
                "assists": [8, 5, 6, 12, 15][i],
                "total_damage_dealt": [25000, 18000, 28000, 32000, 12000][i],
                "gold_earned": [12000, 14500, 15500, 14000, 9500][i],
                "cs": [180, 120, 210, 245, 45][i],
                "vision_score": [25, 35, 28, 42, 55][i],
                "item_0": [1055, 6672, 6653, 6673, 3504][i],
                "item_1": [3068, 3006, 3020, 3006, 3067][i],
                "item_2": [1033, 3134, 3031, 3036, 0][i],
                "item_3": 0, "item_4": 0, "item_5": 0, "item_6": 3362,
            })
        
        t3g_participants = []
        for i, player in enumerate(t3g_players[:5]):
            t3g_participants.append({
                "puuid": player.puuid,
                "champion_id": 39 + i,
                "champion_name": ["Irelia", "Nidalee", "Sylas", "Ezreal", "Thresh"][i],
                "team_id": 200,
                "win": False,
                "kills": [4, 5, 3, 2, 1][i],
                "deaths": [4, 5, 6, 5, 5][i],
                "assists": [3, 2, 4, 6, 8][i],
                "total_damage_dealt": [22000, 15000, 18000, 24000, 8000][i],
                "gold_earned": [12500, 11000, 10500, 12000, 8500][i],
                "cs": [175, 100, 185, 220, 35][i],
                "vision_score": [18, 22, 20, 30, 48][i],
                "item_0": [6632, 6691, 6653, 6672, 3857][i],
                "item_1": [3078, 3006, 3020, 3006, 3111][i],
                "item_2": [3047, 0, 0, 3078, 0][i],
                "item_3": 0, "item_4": 0, "item_5": 0, "item_6": 3362,
            })
        
        # Add participants
        for p_data in ember_participants + t3g_participants:
            # Calculate KDA
            kills = p_data["kills"]
            deaths = p_data["deaths"]
            assists = p_data["assists"]
            kda = round((kills + assists) / deaths, 2) if deaths > 0 else float(kills + assists)
            
            # Check if participant already exists
            existing = MatchParticipant.query.filter_by(
                match_id=match.id, puuid=p_data["puuid"]
            ).first()
            
            if not existing:
                participant = MatchParticipant(
                    match_id=match.id,
                    **{k: v for k, v in p_data.items() if k != "match_id"}
                )
                participant.kda = kda
                db.session.add(participant)
        
        db.session.commit()
        print(f"Added participants to match {match_id}")
        
        print("\nMock match data created successfully!")
        print(f"   Match ID: {match_id}")
        print(f"   Teams: Ember GOATS vs T3G")
        print(f"   Result: Ember GOATS Victory")

if __name__ == "__main__":
    seed_mock_data()
