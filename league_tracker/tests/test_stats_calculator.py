"""
Unit tests for Stats Calculator.
"""
import pytest

from src.utils.stats_calculator import StatsCalculator


@pytest.mark.unit
class TestStatsCalculator:
    """Tests for StatsCalculator class."""

    def test_get_player_stats_no_participants(self, db_session):
        """Test getting stats for player with no matches."""
        stats = StatsCalculator.get_player_stats('nonexistent-puuid')
        assert stats == {}

    def test_get_player_stats_with_participants(self, db_session, sample_match):
        """Test getting stats for player with matches."""
        # Get a participant from the sample match
        participant = sample_match.participants[0]
        stats = StatsCalculator.get_player_stats(participant.puuid)

        assert stats['total_games'] == 1
        assert stats['wins'] == (1 if participant.win else 0)
        assert stats['losses'] == (0 if participant.win else 1)
        assert stats['total_kills'] == participant.kills
        assert stats['total_deaths'] == participant.deaths
        assert stats['total_assists'] == participant.assists
        assert stats['avg_kills'] == participant.kills
        assert stats['avg_deaths'] == participant.deaths
        assert stats['avg_assists'] == participant.assists

    def test_get_player_stats_win_rate(self, db_session, sample_match):
        """Test win rate calculation."""
        participant = sample_match.participants[0]
        stats = StatsCalculator.get_player_stats(participant.puuid)

        expected_win_rate = 100.0 if participant.win else 0.0
        assert stats['win_rate'] == expected_win_rate

    def test_get_champion_stats_no_participants(self, db_session):
        """Test getting champion stats for player with no matches."""
        stats = StatsCalculator.get_champion_stats('nonexistent-puuid')
        assert stats == []

    def test_get_champion_stats_structure(self, db_session, sample_match):
        """Test structure of champion stats."""
        participant = sample_match.participants[0]
        stats = StatsCalculator.get_champion_stats(participant.puuid)

        if stats:
            champ_stat = stats[0]
            assert 'champion_name' in champ_stat
            assert 'games' in champ_stat
            assert 'wins' in champ_stat
            assert 'kills' in champ_stat
            assert 'deaths' in champ_stat
            assert 'assists' in champ_stat
            assert 'win_rate' in champ_stat
            assert 'avg_kills' in champ_stat
            assert 'avg_deaths' in champ_stat
            assert 'avg_assists' in champ_stat
            assert 'kda' in champ_stat

    def test_get_champion_stats_sorted(self, db_session, sample_match):
        """Test that champion stats are sorted by games played."""
        participant = sample_match.participants[0]
        stats = StatsCalculator.get_champion_stats(participant.puuid)

        # Should be sorted by games in descending order
        for i in range(len(stats) - 1):
            assert stats[i]['games'] >= stats[i + 1]['games']

    def test_get_team_stats_no_team(self, db_session):
        """Test getting stats for nonexistent team."""
        stats = StatsCalculator.get_team_stats(999999)
        assert stats == {}

    def test_get_team_stats_no_matches(self, db_session, sample_team):
        """Test getting stats for team with no matches."""
        stats = StatsCalculator.get_team_stats(sample_team.id)
        assert stats['total_games'] == 0

    def test_get_team_stats_with_matches(self, db_session, sample_match):
        """Test getting stats for team with matches."""
        stats = StatsCalculator.get_team_stats(sample_match.home_team_id)

        assert stats['total_games'] == 1
        assert 'wins' in stats
        assert 'losses' in stats
        assert 'win_rate' in stats
        assert 'total_kills' in stats
        assert 'total_deaths' in stats
        assert 'total_assists' in stats
        assert 'avg_kda' in stats

    def test_get_recent_matches_no_matches(self, db_session, sample_team):
        """Test getting recent matches for team with no matches."""
        matches = StatsCalculator.get_recent_matches(sample_team.id, limit=10)
        assert matches == []

    def test_get_recent_matches_structure(self, db_session, sample_match):
        """Test structure of recent matches."""
        matches = StatsCalculator.get_recent_matches(sample_match.home_team_id, limit=10)

        if matches:
            match = matches[0]
            assert 'match_id' in match
            assert 'game_creation' in match
            assert 'game_duration' in match
            assert 'win' in match
            assert 'team_players' in match
            assert 'opponent_players' in match

    def test_get_recent_matches_limit(self, db_session, sample_match):
        """Test that recent matches respects limit parameter."""
        matches = StatsCalculator.get_recent_matches(sample_match.home_team_id, limit=5)
        assert len(matches) <= 5

    def test_format_duration(self):
        """Test formatting game duration."""
        assert StatsCalculator.format_duration(0) == '0:00'
        assert StatsCalculator.format_duration(60) == '1:00'
        assert StatsCalculator.format_duration(90) == '1:30'
        assert StatsCalculator.format_duration(3665) == '61:05'
        assert StatsCalculator.format_duration(1800) == '30:00'

    def test_format_timestamp(self):
        """Test formatting timestamp."""
        # Test with known timestamp (2024-01-01 00:00:00 UTC = 1704067200000 ms)
        # Note: This will be displayed in local timezone
        timestamp_ms = 1704067200000
        formatted = StatsCalculator.format_timestamp(timestamp_ms)
        # Just verify the format is correct, not the exact date
        assert len(formatted) > 0
        assert ':' in formatted  # Should have time separator
        assert '-' in formatted  # Should have date separator

    def test_get_league_matches_all(self, db_session, sample_match):
        """Test getting all league matches."""
        matches = StatsCalculator.get_league_matches(limit=50)
        assert isinstance(matches, list)

    def test_get_league_matches_structure(self, db_session, sample_match):
        """Test structure of league matches."""
        matches = StatsCalculator.get_league_matches(limit=50)

        if matches:
            match = matches[0]
            assert 'match_id' in match
            assert 'game_creation' in match
            assert 'game_duration' in match
            assert 'queue_id' in match
            assert 'participants' in match

    def test_get_league_matches_limit(self, db_session, sample_match):
        """Test that league matches respects limit parameter."""
        matches = StatsCalculator.get_league_matches(limit=5)
        assert len(matches) <= 5

    def test_get_league_matches_ranked_filter(self, db_session, sample_match):
        """Test filtering league matches by ranked queue."""
        matches = StatsCalculator.get_league_matches(limit=50, queue_type='ranked')
        assert isinstance(matches, list)

    def test_get_league_matches_normal_filter(self, db_session, sample_match):
        """Test filtering league matches by normal queue."""
        matches = StatsCalculator.get_league_matches(limit=50, queue_type='normal')
        assert isinstance(matches, list)

    def test_get_league_matches_tournament_filter(self, db_session, sample_match):
        """Test filtering league matches by tournament queue."""
        matches = StatsCalculator.get_league_matches(limit=50, queue_type='tournament')
        assert isinstance(matches, list)

    def test_get_player_league_history_no_participants(self, db_session):
        """Test getting league history for player with no matches."""
        history = StatsCalculator.get_player_league_history('nonexistent-puuid', limit=20)
        assert history == []

    def test_get_player_league_history_structure(self, db_session, sample_match):
        """Test structure of player league history."""
        participant = sample_match.participants[0]
        history = StatsCalculator.get_player_league_history(participant.puuid, limit=20)

        if history:
            entry = history[0]
            assert 'match_id' in entry
            assert 'game_creation' in entry
            assert 'game_duration' in entry
            assert 'win' in entry
            assert 'champion_name' in entry
            assert 'kills' in entry
            assert 'deaths' in entry
            assert 'assists' in entry
            assert 'kda' in entry
            assert 'queue_id' in entry

    def test_get_player_league_history_limit(self, db_session, sample_match):
        """Test that player league history respects limit parameter."""
        participant = sample_match.participants[0]
        history = StatsCalculator.get_player_league_history(participant.puuid, limit=5)
        assert len(history) <= 5

    def test_get_player_league_history_queue_filter(self, db_session, sample_match):
        """Test filtering player league history by queue type."""
        participant = sample_match.participants[0]
        history = StatsCalculator.get_player_league_history(
            participant.puuid, limit=20, queue_type='tournament'
        )
        assert isinstance(history, list)
