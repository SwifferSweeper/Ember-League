"""
Statistics Calculator
Calculates various statistics for teams and players.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database import db, Team, Player, Match, MatchParticipant

logger = logging.getLogger(__name__)


class StatsCalculator:
    """Calculate statistics for teams and players."""
    
    @staticmethod
    def get_player_stats(puuid: str) -> Dict[str, Any]:
        """Get aggregated stats for a player."""
        participants = MatchParticipant.query.filter_by(puuid=puuid).all()
        
        if not participants:
            return {}
        
        total_kills = sum(p.kills for p in participants)
        total_deaths = sum(p.deaths for p in participants)
        total_assists = sum(p.assists for p in participants)
        total_games = len(participants)
        wins = sum(1 for p in participants if p.win)
        
        return {
            'total_games': total_games,
            'wins': wins,
            'losses': total_games - wins,
            'win_rate': round(100 * wins / total_games, 2) if total_games > 0 else 0,
            'total_kills': total_kills,
            'total_deaths': total_deaths,
            'total_assists': total_assists,
            'avg_kills': round(total_kills / total_games, 2) if total_games > 0 else 0,
            'avg_deaths': round(total_deaths / total_games, 2) if total_games > 0 else 0,
            'avg_assists': round(total_assists / total_games, 2) if total_games > 0 else 0,
            'avg_kda': round((total_kills + total_assists) / total_deaths, 2) if total_deaths > 0 else float(total_kills + total_assists),
            'total_gold': sum(p.gold_earned for p in participants),
            'avg_cs': round(sum(p.cs for p in participants) / total_games, 1) if total_games > 0 else 0,
            'total_vision': sum(p.vision_score for p in participants),
        }
    
    @staticmethod
    def get_champion_stats(puuid: str) -> List[Dict[str, Any]]:
        """Get stats grouped by champion for a player."""
        participants = MatchParticipant.query.filter_by(puuid=puuid).all()
        
        champion_stats = {}
        for p in participants:
            champ_name = p.champion_name or 'Unknown'
            if champ_name not in champion_stats:
                champion_stats[champ_name] = {
                    'champion_name': champ_name,
                    'games': 0,
                    'wins': 0,
                    'kills': 0,
                    'deaths': 0,
                    'assists': 0,
                }
            
            stats = champion_stats[champ_name]
            stats['games'] += 1
            stats['wins'] += 1 if p.win else 0
            stats['kills'] += p.kills
            stats['deaths'] += p.deaths
            stats['assists'] += p.assists
        
        # Calculate averages
        for champ_name in champion_stats:
            stats = champion_stats[champ_name]
            stats['win_rate'] = round(100 * stats['wins'] / stats['games'], 2)
            stats['avg_kills'] = round(stats['kills'] / stats['games'], 2)
            stats['avg_deaths'] = round(stats['deaths'] / stats['games'], 2)
            stats['avg_assists'] = round(stats['assists'] / stats['games'], 2)
            stats['kda'] = round((stats['kills'] + stats['assists']) / stats['deaths'], 2) if stats['deaths'] > 0 else float(stats['kills'] + stats['assists'])
        
        return sorted(champion_stats.values(), key=lambda x: x['games'], reverse=True)
    
    @staticmethod
    def get_team_stats(team_id: int) -> Dict[str, Any]:
        """Get aggregated stats for a team."""
        team = Team.query.get(team_id)
        if not team:
            return {}
        
        # Get all matches for the team
        matches = Match.query.filter(
            (Match.home_team_id == team_id) | (Match.away_team_id == team_id)
        ).all()
        
        total_games = len(matches)
        if total_games == 0:
            return {'total_games': 0}
        
        # Get all participants from team matches
        match_ids = [m.id for m in matches]
        participants = MatchParticipant.query.filter(
            MatchParticipant.match_id.in_(match_ids)
        ).all()
        
        # Separate by team (100 = blue, 200 = red)
        # Note: This is a simplified calculation
        team_wins = 0
        opponent_wins = 0
        
        for match in matches:
            match_participants = [p for p in participants if p.match_id == match.id]
            blue_win = any(p.win for p in match_participants if p.team_id == 100)
            
            if match.home_team_id == team_id:
                if blue_win:
                    team_wins += 1
                else:
                    opponent_wins += 1
            else:
                if blue_win:
                    opponent_wins += 1
                else:
                    team_wins += 1
        
        # Get all team players
        player_puuids = [p.puuid for p in team.players if p.puuid]
        player_participants = [p for p in participants if p.puuid in player_puuids]
        
        total_kills = sum(p.kills for p in player_participants)
        total_deaths = sum(p.deaths for p in player_participants)
        total_assists = sum(p.assists for p in player_participants)
        
        return {
            'total_games': total_games,
            'wins': team_wins,
            'losses': opponent_wins,
            'win_rate': round(100 * team_wins / total_games, 2),
            'total_kills': total_kills,
            'total_deaths': total_deaths,
            'total_assists': total_assists,
            'avg_kda': round((total_kills + total_assists) / total_deaths, 2) if total_deaths > 0 else 0,
        }
    
    @staticmethod
    def get_recent_matches(team_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent matches for a team."""
        matches = Match.query.filter(
            (Match.home_team_id == team_id) | (Match.away_team_id == team_id)
        ).order_by(Match.game_creation.desc()).limit(limit).all()
        
        result = []
        for match in matches:
            participants = MatchParticipant.query.filter_by(match_id=match.id).all()
            
            # Determine result
            if match.home_team_id == team_id:
                team_won = any(p.win for p in participants if p.team_id == 100)
                opponent_participants = [p for p in participants if p.team_id == 200]
            else:
                team_won = any(p.win for p in participants if p.team_id == 200)
                opponent_participants = [p for p in participants if p.team_id == 100]
            
            # Get team players in this match
            team = Team.query.get(team_id)
            team_puuids = [p.puuid for p in team.players if p.puuid]
            team_participants = [p for p in participants if p.puuid in team_puuids]
            
            result.append({
                'match_id': match.match_id,
                'game_creation': match.game_creation,
                'game_duration': match.game_duration,
                'win': team_won,
                'team_players': [p.to_dict() for p in team_participants],
                'opponent_players': [p.to_dict() for p in opponent_participants],
            })
        
        return result
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format game duration as MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    @staticmethod
    def format_timestamp(timestamp_ms: int) -> str:
        """Format timestamp to readable date."""
        timestamp_s = timestamp_ms // 1000
        return datetime.fromtimestamp(timestamp_s).strftime('%Y-%m-%d %H:%M')
    
    @staticmethod
    def get_league_matches(limit: int = 50, queue_type: str = None) -> List[Dict[str, Any]]:
        """Get all league tournament matches (from the database)."""
        query = Match.query
        
        if queue_type == 'ranked':
            query = query.filter(Match.queue_id.in_([420, 440]))
        elif queue_type == 'normal':
            query = query.filter(Match.queue_id.in_([400, 430, 450]))
        elif queue_type == 'tournament':
            query = query.filter_by(queue_id=0)
        
        matches = query.order_by(Match.game_creation.desc()).limit(limit).all()
        
        result = []
        for match in matches:
            participants = MatchParticipant.query.filter_by(match_id=match.id).all()
            
            result.append({
                'match_id': match.match_id,
                'game_creation': match.game_creation,
                'game_duration': match.game_duration,
                'queue_id': match.queue_id,
                'home_team': match.home_team.name if match.home_team else None,
                'away_team': match.away_team.name if match.away_team else None,
                'participants': [p.to_dict() for p in participants],
            })
        
        return result
    
    @staticmethod
    def get_player_league_history(puuid: str, limit: int = 20, queue_type: str = None) -> List[Dict[str, Any]]:
        """Get tournament match history for a specific player."""
        # First get participant IDs
        participant_query = MatchParticipant.query.filter_by(puuid=puuid)
        
        if queue_type == 'ranked':
            participant_query = participant_query.join(Match).filter(Match.queue_id.in_([420, 440]))
        elif queue_type == 'normal':
            participant_query = participant_query.join(Match).filter(Match.queue_id.in_([400, 430, 450]))
        elif queue_type == 'tournament':
            participant_query = participant_query.join(Match).filter_by(queue_id=0)
        
        participants = participant_query.order_by(MatchParticipant.id.desc()).limit(limit).all()
        
        result = []
        for p in participants:
            match = Match.query.get(p.match_id)
            if match:
                result.append({
                    'match_id': match.match_id,
                    'game_creation': match.game_creation,
                    'game_duration': match.game_duration,
                    'win': p.win,
                    'champion_name': p.champion_name,
                    'kills': p.kills,
                    'deaths': p.deaths,
                    'assists': p.assists,
                    'kda': p.kda,
                    'queue_id': match.queue_id,
                })
        
        return result
