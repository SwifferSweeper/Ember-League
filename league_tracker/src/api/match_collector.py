"""
Match Collection Service
Automatically fetches and stores match data for all registered players.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import TOURNAMENT_QUEUE_ID
from src.database import db, Team, Player, Match, MatchParticipant
from src.api.riot_client import RiotClient, RiotAPIError

logger = logging.getLogger(__name__)


class MatchCollector:
    """Service for collecting and processing match data."""
    
    def __init__(self, app=None):
        self.client = None
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app context."""
        self.app = app
        try:
            self.client = RiotClient()
        except RiotAPIError:
            logger.warning("Riot API client could not be initialized")
    
    def calculate_kda(self, kills: int, deaths: int, assists: int) -> float:
        """Calculate KDA ratio."""
        if deaths == 0:
            return float(kills + assists)
        return round((kills + assists) / deaths, 2)
    
    def process_match_participant(self, participant: Dict, match_id: str) -> Dict:
        """Process a single participant from match data."""
        kills = participant.get('kills', 0)
        deaths = participant.get('deaths', 0)
        assists = participant.get('assists', 0)
        
        return {
            'puuid': participant.get('puuid'),
            'champion_id': participant.get('championId'),
            'champion_name': participant.get('championName'),
            'team_id': participant.get('teamId'),
            'win': participant.get('win', False),
            'kills': kills,
            'deaths': deaths,
            'assists': assists,
            'kda': self.calculate_kda(kills, deaths, assists),
            'total_damage_dealt': participant.get('totalDamageDealtToChampions', 0),
            'gold_earned': participant.get('goldEarned', 0),
            'cs': participant.get('totalMinionsKilled', 0) + participant.get('neutralMinionsKilled', 0),
            'vision_score': participant.get('visionScore', 0),
            'item_0': participant.get('item0'),
            'item_1': participant.get('item1'),
            'item_2': participant.get('item2'),
            'item_3': participant.get('item3'),
            'item_4': participant.get('item4'),
            'item_5': participant.get('item5'),
            'item_6': participant.get('item6'),
        }
    
    def process_match(self, match_data: Dict[str, Any]) -> Dict:
        """Process full match data into database format."""
        metadata = match_data.get('metadata', {})
        info = match_data.get('info', {})
        match_id = metadata.get('matchId')
        
        return {
            'match_id': match_id,
            'game_duration': info.get('gameDuration', 0),
            'game_version': info.get('gameVersion'),
            'game_creation': info.get('gameCreation', 0),
            'queue_id': info.get('queueId'),
            'participants': [
                self.process_match_participant(p, match_id)
                for p in info.get('participants', [])
            ]
        }
    
    def match_exists(self, match_id: str) -> bool:
        """Check if a match is already in the database."""
        return Match.query.filter_by(match_id=match_id).first() is not None
    
    def add_match(self, match_data: Dict) -> bool:
        """Add a match and its participants to the database."""
        try:
            match = Match(
                match_id=match_data['match_id'],
                game_duration=match_data['game_duration'],
                game_version=match_data.get('game_version'),
                game_creation=match_data.get('game_creation', 0),
                queue_id=match_data.get('queue_id')
            )
            db.session.add(match)
            db.session.flush()
            
            for participant_data in match_data['participants']:
                participant = MatchParticipant(
                    match_id=match.id,
                    **{k: v for k, v in participant_data.items() if k != 'match_id'}
                )
                db.session.add(participant)
            
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding match {match_data.get('match_id')}: {e}")
            db.session.rollback()
            return False
    
    def collect_player_matches(self, player: Player, count: int = 20) -> List[str]:
        """Collect matches for a single player."""
        if not self.client:
            logger.warning("No Riot API client available")
            return []
        
        puuid = player.puuid
        if not puuid:
            logger.warning(f"Player {player.display_name} has no PUUID")
            return []
        
        try:
            region = player.region
            match_ids = self.client.get_match_ids_by_puuid(
                puuid, region, count=count, queue=TOURNAMENT_QUEUE_ID
            )
            
            new_matches = []
            for match_id in match_ids:
                if not self.match_exists(match_id):
                    try:
                        match_data = self.client.get_match_details(match_id, region)
                        processed = self.process_match(match_data)
                        
                        if self.add_match(processed):
                            new_matches.append(match_id)
                            logger.info(f"Added match: {match_id}")
                    except RiotAPIError as e:
                        logger.error(f"Error fetching match {match_id}: {e}")
                        continue
            
            return new_matches
        
        except RiotAPIError as e:
            logger.error(f"Error getting match IDs for {player.display_name}: {e}")
            return []
    
    def collect_all_matches(self, count_per_player: int = 10) -> Dict[str, int]:
        """Collect matches for all registered players."""
        stats = {
            'players_processed': 0,
            'new_matches': 0,
            'errors': 0
        }
        
        players = Player.query.all()
        logger.info(f"Processing {len(players)} players...")
        
        for player in players:
            try:
                new_matches = self.collect_player_matches(player, count_per_player)
                stats['new_matches'] += len(new_matches)
                stats['players_processed'] += 1
            except Exception as e:
                logger.error(f"Error processing player {player.display_name}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Collection complete: {stats}")
        return stats


def run_collect(app) -> Dict[str, int]:
    """Run the match collector with app context."""
    with app.app_context():
        collector = MatchCollector(app)
        return collector.collect_all_matches()
