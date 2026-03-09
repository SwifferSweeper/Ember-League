"""
Inhouse Stats Storage Module
============================
This module provides integration between the inhouse_stats_tracker and the 
PostgreSQL database. It can be used to store match stats directly to the database
instead of Google Sheets.

Usage:
    from league_tracker.src.utils.inhouse_storage import save_inhouse_stats
    
    # After extracting stats from a match:
    save_inhouse_stats(match_data, participants_data)
"""

from datetime import datetime
from league_tracker.src.database import db, InhouseMatch, InhouseParticipant


def save_inhouse_match(match_id, game_date, game_duration_min, queue_id=None):
    """
    Create or get an existing inhouse match record.
    
    Args:
        match_id: The Riot match ID (e.g., "NA1_1234567890")
        game_date: datetime object for when the game was played
        game_duration_min: Duration of the game in minutes
        queue_id: Optional queue ID (0 for custom games, 3130 for tournament)
    
    Returns:
        InhouseMatch object
    """
    # Check if match already exists
    existing = InhouseMatch.query.filter_by(match_id=match_id).first()
    if existing:
        return existing
    
    # Create new match record
    match = InhouseMatch(
        match_id=match_id,
        game_date=game_date,
        game_duration_min=game_duration_min,
        queue_id=queue_id
    )
    db.session.add(match)
    db.session.commit()
    
    return match


def save_inhouse_participant(match_id, participant_data):
    """
    Save a single participant's stats to the database.
    
    Args:
        match_id: The InhouseMatch ID (or match_id string)
        participant_data: Dictionary containing all participant stats
    
    Returns:
        InhouseParticipant object
    """
    # Get the match object
    if isinstance(match_id, str):
        match = InhouseMatch.query.filter_by(match_id=match_id).first()
    else:
        match = InhouseMatch.query.get(match_id)
    
    if not match:
        raise ValueError(f"Match not found: {match_id}")
    
    participant = InhouseParticipant(
        match_id=match.id,
        summoner_name=participant_data.get('summoner_name', 'Unknown'),
        tag=participant_data.get('tag', ''),
        puuid=participant_data.get('puuid'),
        team=participant_data.get('team', 'Blue'),
        champion=participant_data.get('champion', 'Unknown'),
        role=participant_data.get('role', 'Unknown'),
        win=participant_data.get('win', False),
        kills=participant_data.get('kills', 0),
        deaths=participant_data.get('deaths', 0),
        assists=participant_data.get('assists', 0),
        kda=participant_data.get('kda', 0.0),
        double_kills=participant_data.get('double_kills', 0),
        triple_kills=participant_data.get('triple_kills', 0),
        quadra_kills=participant_data.get('quadra_kills', 0),
        penta_kills=participant_data.get('penta_kills', 0),
        total_damage_to_champions=participant_data.get('total_damage_to_champions', 0),
        damage_per_min=participant_data.get('damage_per_min', 0.0),
        physical_damage=participant_data.get('physical_damage', 0),
        magic_damage=participant_data.get('magic_damage', 0),
        true_damage=participant_data.get('true_damage', 0),
        damage_taken=participant_data.get('damage_taken', 0),
        damage_mitigated=participant_data.get('damage_mitigated', 0),
        cs=participant_data.get('cs', 0),
        cs_per_min=participant_data.get('cs_per_min', 0.0),
        gold_earned=participant_data.get('gold_earned', 0),
        gold_per_min=participant_data.get('gold_per_min', 0.0),
        vision_score=participant_data.get('vision_score', 0),
        wards_placed=participant_data.get('wards_placed', 0),
        wards_killed=participant_data.get('wards_killed', 0),
        control_wards_bought=participant_data.get('control_wards_bought', 0),
        turret_kills=participant_data.get('turret_kills', 0),
        turret_damage=participant_data.get('turret_damage', 0),
        objective_damage=participant_data.get('objective_damage', 0),
        team_dragons=participant_data.get('team_dragons', 0),
        team_first_dragon=participant_data.get('team_first_dragon', False),
        team_barons=participant_data.get('team_barons', 0),
        team_first_baron=participant_data.get('team_first_baron', False),
        team_heralds=participant_data.get('team_heralds', 0),
        team_first_herald=participant_data.get('team_first_herald', False),
        team_grubs=participant_data.get('team_grubs', 0),
        team_first_grubs=participant_data.get('team_first_grubs', False),
        team_towers=participant_data.get('team_towers', 0),
        team_first_tower=participant_data.get('team_first_tower', False),
        team_first_blood=participant_data.get('team_first_blood', False)
    )
    
    db.session.add(participant)
    db.session.commit()
    
    return participant


def save_inhouse_stats(match_data, participants_data, queue_id=None):
    """
    Save complete inhouse match stats to the database.
    
    This function takes raw match data from the Riot API and saves all
    participant stats to the database.
    
    Args:
        match_data: Dictionary containing match info (match_id, game_date, game_duration_min)
        participants_data: List of dictionaries, each containing participant stats
        queue_id: Optional queue ID for the match
    
    Returns:
        InhouseMatch object with saved participants
    """
    # Extract match info
    match_id = match_data.get('match_id')
    game_date = match_data.get('game_date')
    game_duration_min = match_data.get('game_duration_min', 0)
    
    # Parse date if it's a string
    if isinstance(game_date, str):
        try:
            game_date = datetime.fromisoformat(game_date.replace(' ', 'T'))
        except ValueError:
            # Try parsing common formats
            for fmt in ['%Y-%m-%d %I:%M %p', '%Y-%m-%d', '%m/%d/%Y %I:%M %p']:
                try:
                    game_date = datetime.strptime(game_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                game_date = datetime.utcnow()
    
    # Create or get match
    match = save_inhouse_match(match_id, game_date, game_duration_min, queue_id)
    
    # Save all participants
    for pdata in participants_data:
        save_inhouse_participant(match, pdata)
    
    return match


def convert_row_to_dict(row, team_objectives):
    """
    Convert a spreadsheet row (from inhouse_stats_tracker) to a participant dict.
    
    This is useful when migrating from Google Sheets or when the tracker
    outputs data in the original format.
    
    Args:
        row: List of values from the tracker (in STAT_HEADERS order)
        team_objectives: Dict of team objectives for the player's team
    
    Returns:
        Dictionary suitable for save_inhouse_participant()
    """
    return {
        'summoner_name': row[4],  # Summoner Name
        'tag': row[5],            # Tag
        'team': row[3],           # Team (Blue/Red)
        'champion': row[6],       # Champion
        'role': row[7],           # Role
        'kills': row[8],          # Kills
        'deaths': row[9],         # Deaths
        'assists': row[10],       # Assists
        'kda': row[11],           # KDA
        'double_kills': row[12],   # Double Kills
        'triple_kills': row[13],   # Triple Kills
        'quadra_kills': row[14],   # Quadra Kills
        'penta_kills': row[15],    # Penta Kills
        'total_damage_to_champions': row[16],  # Total Damage to Champions
        'damage_per_min': row[17],              # Damage/min
        'physical_damage': row[18],              # Physical Damage
        'magic_damage': row[19],                 # Magic Damage
        'true_damage': row[20],                  # True Damage
        'damage_taken': row[21],                 # Damage Taken
        'damage_mitigated': row[22],             # Damage Mitigated
        'cs': row[23],                          # CS
        'cs_per_min': row[24],                   # CS/min
        'gold_earned': row[25],                  # Gold Earned
        'gold_per_min': row[26],                 # Gold/min
        'vision_score': row[27],                 # Vision Score
        'wards_placed': row[28],                 # Wards Placed
        'wards_killed': row[29],                 # Wards Killed
        'control_wards_bought': row[30],         # Control Wards Bought
        'turret_kills': row[31],                 # Turret Kills
        'turret_damage': row[32],                # Turret Damage
        'objective_damage': row[33],              # Objective Damage
        'team_dragons': team_objectives.get('dragons', 0),
        'team_first_dragon': team_objectives.get('firstDragon', False),
        'team_barons': team_objectives.get('barons', 0),
        'team_first_baron': team_objectives.get('firstBaron', False),
        'team_heralds': team_objectives.get('heralds', 0),
        'team_first_herald': team_objectives.get('firstHerald', False),
        'team_grubs': team_objectives.get('grubs', 0),
        'team_first_grubs': team_objectives.get('firstGrubs', False),
        'team_towers': team_objectives.get('towers', 0),
        'team_first_tower': team_objectives.get('firstTower', False),
        'team_first_blood': team_objectives.get('firstBlood', False),
        'win': row[37] == 'Win' if isinstance(row[37], str) else row[37],  # Win
    }


def get_inhouse_leaderboard(stat='kda', min_games=3, limit=10):
    """
    Get a leaderboard of inhouse players by a specific stat.
    
    Args:
        stat: Stat to sort by ('kda', 'kills', 'cs', 'gold_earned', 'vision_score', etc.)
        min_games: Minimum number of games played to be included
        limit: Maximum number of players to return
    
    Returns:
        List of dicts with player stats
    """
    from sqlalchemy import func
    
    # Validate stat column exists
    valid_stats = [
        'kda', 'kills', 'deaths', 'assists', 'cs', 'gold_earned', 
        'vision_score', 'wards_placed', 'damage_per_min'
    ]
    if stat not in valid_stats:
        stat = 'kda'
    
    # Build subquery for player stats
    player_stats = db.session.query(
        InhouseParticipant.summoner_name,
        InhouseParticipant.tag,
        func.count(InhouseParticipant.id).label('games'),
        func.avg(getattr(InhouseParticipant, stat)).label('avg_' + stat),
        func.sum(InhouseParticipant.kills).label('total_kills'),
        func.sum(InhouseParticipant.deaths).label('total_deaths'),
        func.sum(InhouseParticipant.assists).label('total_assists'),
        func.sum(db.case((InhouseParticipant.win, 1), else_=0)).label('wins')
    ).group_by(
        InhouseParticipant.summoner_name,
        InhouseParticipant.tag
    ).having(
        func.count(InhouseParticipant.id) >= min_games
    ).order_by(
        getattr(InhouseParticipant, stat).desc()
    ).limit(limit)
    
    results = []
    for row in player_stats:
        results.append({
            'summoner_name': row.summoner_name,
            'tag': row.tag,
            'games': row.games,
            'avg_' + stat: round(row['avg_' + stat], 2) if row['avg_' + stat] else 0,
            'total_kills': row.total_kills,
            'total_deaths': row.total_deaths,
            'total_assists': row.total_assists,
            'wins': row.wins,
            'win_rate': round(row.wins / row.games * 100, 1) if row.games > 0 else 0
        })
    
    return results
