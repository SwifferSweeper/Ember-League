"""
Unit tests for Match Collector.
"""
import pytest
from unittest.mock import Mock, patch

from src.api.match_collector import MatchCollector
from src.api.riot_client import RiotAPIError


@pytest.mark.unit
class TestMatchCollector:
    """Tests for MatchCollector class."""

    @pytest.fixture
    def collector(self, app):
        """Create a MatchCollector instance for testing."""
        return MatchCollector(app)

    def test_init_app(self, app):
        """Test MatchCollector initialization with app."""
        collector = MatchCollector(app)
        assert collector.app == app

    def test_init_without_app(self):
        """Test MatchCollector initialization without app."""
        collector = MatchCollector()
        assert collector.app is None

    def test_calculate_kda_with_deaths(self):
        """Test KDA calculation with deaths."""
        kda = MatchCollector.calculate_kda(5, 2, 8)
        assert kda == 6.5

    def test_calculate_kda_no_deaths(self):
        """Test KDA calculation with zero deaths."""
        kda = MatchCollector.calculate_kda(5, 0, 8)
        assert kda == 13.0

    def test_calculate_kda_all_zeros(self):
        """Test KDA calculation with all zeros."""
        kda = MatchCollector.calculate_kda(0, 0, 0)
        assert kda == 0.0

    def test_process_match_participant(self, collector):
        """Test processing a match participant."""
        participant_data = {
            'puuid': 'test-puuid',
            'championId': 1,
            'championName': 'Annie',
            'teamId': 100,
            'win': True,
            'kills': 5,
            'deaths': 2,
            'assists': 8,
            'totalDamageDealtToChampions': 20000,
            'goldEarned': 10000,
            'totalMinionsKilled': 150,
            'neutralMinionsKilled': 0,
            'visionScore': 20,
            'item0': 0,
            'item1': 0,
            'item2': 0,
            'item3': 0,
            'item4': 0,
            'item5': 0,
            'item6': 0
        }

        result = collector.process_match_participant(participant_data, 'match-id')

        assert result['puuid'] == 'test-puuid'
        assert result['champion_name'] == 'Annie'
        assert result['team_id'] == 100
        assert result['win'] is True
        assert result['kills'] == 5
        assert result['deaths'] == 2
        assert result['assists'] == 8
        assert result['kda'] == 6.5
        assert result['cs'] == 150

    def test_process_match(self, collector):
        """Test processing full match data."""
        match_data = {
            'metadata': {'matchId': 'NA1_1234567890'},
            'info': {
                'gameDuration': 1800,
                'gameVersion': '14.1.1',
                'gameCreation': 1704067200000,
                'queueId': 0,
                'participants': [
                    {
                        'puuid': 'test-puuid',
                        'championId': 1,
                        'championName': 'Annie',
                        'teamId': 100,
                        'win': True,
                        'kills': 5,
                        'deaths': 2,
                        'assists': 8,
                        'totalDamageDealtToChampions': 20000,
                        'goldEarned': 10000,
                        'totalMinionsKilled': 150,
                        'neutralMinionsKilled': 0,
                        'visionScore': 20,
                        'item0': 0,
                        'item1': 0,
                        'item2': 0,
                        'item3': 0,
                        'item4': 0,
                        'item5': 0,
                        'item6': 0
                    }
                ]
            }
        }

        result = collector.process_match(match_data)

        assert result['match_id'] == 'NA1_1234567890'
        assert result['game_duration'] == 1800
        assert result['game_version'] == '14.1.1'
        assert result['queue_id'] == 0
        assert len(result['participants']) == 1
        assert result['participants'][0]['champion_name'] == 'Annie'

    def test_match_exists_true(self, db_session, sample_match):
        """Test checking if match exists (true case)."""
        collector = MatchCollector()
        assert collector.match_exists('NA1_1234567890') is True

    def test_match_exists_false(self, db_session):
        """Test checking if match exists (false case)."""
        collector = MatchCollector()
        assert collector.match_exists('NA1_9999999999') is False

    def test_add_match_success(self, db_session, sample_team_with_players):
        """Test adding a match to database successfully."""
        collector = MatchCollector()

        match_data = {
            'match_id': 'NA1_9999999999',
            'game_duration': 1800,
            'game_version': '14.1.1',
            'game_creation': 1704067200000,
            'queue_id': 0,
            'participants': [
                {
                    'puuid': sample_team_with_players.players[0].puuid,
                    'champion_id': 1,
                    'champion_name': 'Annie',
                    'team_id': 100,
                    'win': True,
                    'kills': 5,
                    'deaths': 2,
                    'assists': 8,
                    'kda': 6.5,
                    'total_damage_dealt': 20000,
                    'gold_earned': 10000,
                    'cs': 150,
                    'vision_score': 20,
                    'item_0': 0,
                    'item_1': 0,
                    'item_2': 0,
                    'item_3': 0,
                    'item_4': 0,
                    'item_5': 0,
                    'item_6': 0
                }
            ]
        }

        result = collector.add_match(match_data)
        assert result is True

    def test_add_match_duplicate(self, db_session, sample_match):
        """Test adding duplicate match fails."""
        collector = MatchCollector()

        match_data = {
            'match_id': 'NA1_1234567890',
            'game_duration': 1800,
            'participants': []
        }

        result = collector.add_match(match_data)
        assert result is False

    @patch('src.api.match_collector.RiotClient')
    def test_collect_player_matches_no_puuid(self, mock_riot_client_class, app):
        """Test collecting matches for player without PUUID."""
        from src.database import Player

        mock_client = Mock()
        mock_riot_client_class.return_value = mock_client

        player = Player(game_name='TestPlayer', tag_line='NA1', region='na1')
        player.puuid = None

        collector = MatchCollector(app)
        result = collector.collect_player_matches(player, count=10)

        assert result == []
        mock_client.get_match_ids_by_puuid.assert_not_called()

    @patch('src.api.match_collector.RiotClient')
    def test_collect_player_matches_success(self, mock_riot_client_class, app, sample_player):
        """Test collecting matches for player successfully."""
        mock_client = Mock()
        mock_riot_client_class.return_value = mock_client

        mock_client.get_match_ids_by_puuid.return_value = ['match1', 'match2']
        
        # Return different match data for each match ID
        def get_match_details_side_effect(match_id, region):
            if match_id == 'match1':
                return {
                    'metadata': {'matchId': 'match1'},
                    'info': {
                        'gameDuration': 1800,
                        'gameVersion': '14.1.1',
                        'gameCreation': 1704067200000,
                        'queueId': 0,
                        'participants': []
                    }
                }
            elif match_id == 'match2':
                return {
                    'metadata': {'matchId': 'match2'},
                    'info': {
                        'gameDuration': 2100,
                        'gameVersion': '14.1.1',
                        'gameCreation': 1704067300000,
                        'queueId': 0,
                        'participants': []
                    }
                }
            return None
        
        mock_client.get_match_details.side_effect = get_match_details_side_effect

        collector = MatchCollector(app)
        result = collector.collect_player_matches(sample_player, count=10)

        assert len(result) == 2
        assert mock_client.get_match_ids_by_puuid.call_count == 1
        assert mock_client.get_match_details.call_count == 2

    @patch('src.api.match_collector.RiotClient')
    def test_collect_player_matches_api_error(self, mock_riot_client_class, app, sample_player):
        """Test collecting matches with API error."""
        mock_client = Mock()
        mock_riot_client_class.return_value = mock_client

        mock_client.get_match_ids_by_puuid.side_effect = RiotAPIError('API Error')

        collector = MatchCollector(app)
        result = collector.collect_player_matches(sample_player, count=10)

        assert result == []

    @patch('src.api.match_collector.RiotClient')
    def test_collect_all_matches(self, mock_riot_client_class, app, sample_team_with_players):
        """Test collecting matches for all players."""
        mock_client = Mock()
        mock_riot_client_class.return_value = mock_client

        mock_client.get_match_ids_by_puuid.return_value = ['match1']
        mock_client.get_match_details.return_value = {
            'metadata': {'matchId': 'match1'},
            'info': {
                'gameDuration': 1800,
                'gameVersion': '14.1.1',
                'gameCreation': 1704067200000,
                'queueId': 0,
                'participants': []
            }
        }

        collector = MatchCollector(app)
        result = collector.collect_all_matches(count_per_player=5)

        assert result['players_processed'] == len(sample_team_with_players.players)
        assert 'new_matches' in result
        assert 'errors' in result
