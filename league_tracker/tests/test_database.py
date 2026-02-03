"""
Unit tests for database models.
"""
import pytest
from datetime import datetime

from src.database import (
    db, Team, Player, Match, MatchParticipant, Admin,
    TournamentCode, DraftSession, DraftGame, DraftStep, team_players
)


@pytest.mark.unit
class TestAdmin:
    """Tests for Admin model."""

    def test_create_admin(self, db_session):
        """Test creating an admin user."""
        admin = Admin(username='testadmin')
        admin.set_password('password123')
        db_session.add(admin)
        db_session.commit()

        assert admin.id is not None
        assert admin.username == 'testadmin'
        assert admin.password_hash is not None
        assert admin.check_password('password123') is True
        assert admin.check_password('wrongpassword') is False

    def test_admin_repr(self, db_session):
        """Test Admin __repr__ method."""
        admin = Admin(username='testadmin')
        assert repr(admin) == '<Admin testadmin>'


@pytest.mark.unit
class TestTeam:
    """Tests for Team model."""

    def test_create_team(self, db_session):
        """Test creating a team."""
        team = Team(name='Test Team')
        db_session.add(team)
        db_session.commit()

        assert team.id is not None
        assert team.name == 'Test Team'
        assert team.created_at is not None

    def test_team_unique_name(self, db_session):
        """Test that team names must be unique."""
        team1 = Team(name='Same Name')
        db_session.add(team1)
        db_session.commit()

        team2 = Team(name='Same Name')
        db_session.add(team2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_team_repr(self, db_session):
        """Test Team __repr__ method."""
        team = Team(name='Test Team')
        assert repr(team) == '<Team Test Team>'

    def test_team_to_dict(self, db_session):
        """Test Team to_dict method."""
        team = Team(name='Test Team')
        db_session.add(team)
        db_session.commit()

        team_dict = team.to_dict()
        assert team_dict['name'] == 'Test Team'
        assert 'id' in team_dict
        assert 'created_at' in team_dict

    def test_team_player_relationship(self, db_session, sample_team, sample_player):
        """Test team-player relationship."""
        sample_team.players.append(sample_player)
        db_session.commit()

        assert sample_player in sample_team.players
        assert sample_team in sample_player.teams.all()


@pytest.mark.unit
class TestPlayer:
    """Tests for Player model."""

    def test_create_player(self, db_session):
        """Test creating a player."""
        player = Player(
            puuid='test-puuid',
            game_name='TestPlayer',
            tag_line='NA1',
            region='na1'
        )
        db_session.add(player)
        db_session.commit()

        assert player.id is not None
        assert player.puuid == 'test-puuid'
        assert player.game_name == 'TestPlayer'
        assert player.tag_line == 'NA1'
        assert player.region == 'na1'

    def test_player_display_name(self, db_session):
        """Test Player display_name property."""
        player = Player(
            game_name='TestPlayer',
            tag_line='NA1',
            region='na1'
        )
        assert player.display_name == 'TestPlayer#NA1'

    def test_player_repr(self, db_session):
        """Test Player __repr__ method."""
        player = Player(game_name='TestPlayer', tag_line='NA1', region='na1')
        assert repr(player) == '<Player TestPlayer#NA1>'

    def test_player_to_dict(self, db_session):
        """Test Player to_dict method."""
        player = Player(
            puuid='test-puuid',
            game_name='TestPlayer',
            tag_line='NA1',
            region='na1'
        )
        db_session.add(player)
        db_session.commit()

        player_dict = player.to_dict()
        assert player_dict['game_name'] == 'TestPlayer'
        assert player_dict['tag_line'] == 'NA1'
        assert player_dict['display_name'] == 'TestPlayer#NA1'


@pytest.mark.unit
class TestMatch:
    """Tests for Match model."""

    def test_create_match(self, db_session, sample_team):
        """Test creating a match."""
        match = Match(
            match_id='NA1_1234567890',
            game_duration=1800,
            game_version='14.1.1',
            game_creation=1704067200000,
            queue_id=0,
            home_team_id=sample_team.id
        )
        db_session.add(match)
        db_session.commit()

        assert match.id is not None
        assert match.match_id == 'NA1_1234567890'
        assert match.game_duration == 1800

    def test_match_unique_match_id(self, db_session):
        """Test that match IDs must be unique."""
        match1 = Match(match_id='NA1_1234567890', game_duration=1800)
        db_session.add(match1)
        db_session.commit()

        match2 = Match(match_id='NA1_1234567890', game_duration=1800)
        db_session.add(match2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_match_repr(self, db_session):
        """Test Match __repr__ method."""
        match = Match(match_id='NA1_1234567890', game_duration=1800)
        assert repr(match) == '<Match NA1_1234567890>'

    def test_match_to_dict(self, db_session, sample_team):
        """Test Match to_dict method."""
        match = Match(
            match_id='NA1_1234567890',
            game_duration=1800,
            home_team_id=sample_team.id
        )
        db_session.add(match)
        db_session.commit()

        match_dict = match.to_dict()
        assert match_dict['match_id'] == 'NA1_1234567890'
        assert 'home_team' in match_dict


@pytest.mark.unit
class TestMatchParticipant:
    """Tests for MatchParticipant model."""

    def test_create_participant(self, db_session, sample_match):
        """Test creating a match participant."""
        participant = MatchParticipant(
            match_id=sample_match.id,
            puuid='test-puuid',
            champion_id=1,
            champion_name='Annie',
            team_id=100,
            win=True,
            kills=5,
            deaths=2,
            assists=8,
            kda=6.5
        )
        db_session.add(participant)
        db_session.commit()

        assert participant.id is not None
        assert participant.champion_name == 'Annie'
        assert participant.win is True

    def test_participant_repr(self, db_session):
        """Test MatchParticipant __repr__ method."""
        participant = MatchParticipant(
            champion_name='Annie',
            kda=6.5
        )
        assert 'Annie' in repr(participant)
        assert '6.5' in repr(participant)

    def test_participant_to_dict(self, db_session, sample_match):
        """Test MatchParticipant to_dict method."""
        participant = MatchParticipant(
            match_id=sample_match.id,
            puuid='test-puuid',
            champion_name='Annie',
            team_id=100,
            win=True,
            kills=5,
            deaths=2,
            assists=8,
            kda=6.5
        )
        db_session.add(participant)
        db_session.commit()

        participant_dict = participant.to_dict()
        assert participant_dict['champion_name'] == 'Annie'
        assert participant_dict['win'] is True
        assert participant_dict['kda'] == 6.5


@pytest.mark.unit
class TestTournamentCode:
    """Tests for TournamentCode model."""

    def test_create_tournament_code(self, db_session, sample_team):
        """Test creating a tournament code."""
        code = TournamentCode(
            code='TOURNAMENT123',
            tournament_name='Test Tournament',
            team_id=sample_team.id
        )
        db_session.add(code)
        db_session.commit()

        assert code.id is not None
        assert code.code == 'TOURNAMENT123'
        assert code.is_used is False

    def test_tournament_code_unique_code(self, db_session):
        """Test that tournament codes must be unique."""
        code1 = TournamentCode(code='SAME123')
        db_session.add(code1)
        db_session.commit()

        code2 = TournamentCode(code='SAME123')
        db_session.add(code2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_tournament_code_repr(self, db_session):
        """Test TournamentCode __repr__ method."""
        code = TournamentCode(code='TOURNAMENT123')
        assert repr(code) == '<TournamentCode TOURNAMENT123>'

    def test_tournament_code_to_dict(self, db_session, sample_team):
        """Test TournamentCode to_dict method."""
        code = TournamentCode(
            code='TOURNAMENT123',
            tournament_name='Test Tournament',
            team_id=sample_team.id
        )
        db_session.add(code)
        db_session.commit()

        code_dict = code.to_dict()
        assert code_dict['code'] == 'TOURNAMENT123'
        assert code_dict['tournament_name'] == 'Test Tournament'


@pytest.mark.unit
class TestDraftSession:
    """Tests for DraftSession model."""

    def test_create_draft_session(self, db_session, sample_team):
        """Test creating a draft session."""
        team2 = Team(name='Opponent Team')
        db_session.add(team2)
        db_session.commit()

        session = DraftSession(
            name='Test Draft',
            draft_mode='normal',
            team_blue_id=sample_team.id,
            team_red_id=team2.id,
            bans_per_team=5,
            picks_per_team=5
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.name == 'Test Draft'
        assert session.draft_mode == 'normal'
        assert session.is_active is True

    def test_draft_session_repr(self, db_session, sample_team):
        """Test DraftSession __repr__ method."""
        team2 = Team(name='Opponent Team')
        db_session.add(team2)
        db_session.commit()

        session = DraftSession(
            name='Test Draft',
            draft_mode='normal',
            team_blue_id=sample_team.id,
            team_red_id=team2.id
        )
        assert 'Test Draft' in repr(session)
        assert 'normal' in repr(session)

    def test_draft_session_to_dict(self, db_session, sample_team):
        """Test DraftSession to_dict method."""
        team2 = Team(name='Opponent Team')
        db_session.add(team2)
        db_session.commit()

        session = DraftSession(
            name='Test Draft',
            draft_mode='normal',
            team_blue_id=sample_team.id,
            team_red_id=team2.id
        )
        db_session.add(session)
        db_session.commit()

        session_dict = session.to_dict()
        assert session_dict['name'] == 'Test Draft'
        assert session_dict['draft_mode'] == 'normal'
        assert 'timer_remaining' in session_dict


@pytest.mark.unit
class TestDraftGame:
    """Tests for DraftGame model."""

    def test_create_draft_game(self, db_session, sample_draft_session):
        """Test creating a draft game."""
        game = DraftGame(
            session_id=sample_draft_session.id,
            game_number=1,
            bans_blue=[1, 2, 3],
            bans_red=[4, 5, 6],
            picks_blue=[{'champion_id': 7}],
            picks_red=[{'champion_id': 8}]
        )
        db_session.add(game)
        db_session.commit()

        assert game.id is not None
        assert game.game_number == 1
        assert len(game.bans_blue) == 3

    def test_draft_game_repr(self, db_session, sample_draft_session):
        """Test DraftGame __repr__ method."""
        game = DraftGame(
            session_id=sample_draft_session.id,
            game_number=1
        )
        assert 'session=' in repr(game)
        assert 'game=1' in repr(game)

    def test_draft_game_to_dict(self, db_session, sample_draft_session):
        """Test DraftGame to_dict method."""
        game = DraftGame(
            session_id=sample_draft_session.id,
            game_number=1,
            bans_blue=[1, 2, 3],
            picks_blue=[{'champion_id': 7}]
        )
        db_session.add(game)
        db_session.commit()

        game_dict = game.to_dict()
        assert game_dict['game_number'] == 1
        assert game_dict['bans_blue'] == [1, 2, 3]


@pytest.mark.unit
class TestDraftStep:
    """Tests for DraftStep model."""

    def test_create_draft_step(self, db_session, sample_draft_session):
        """Test creating a draft step."""
        step = DraftStep(
            session_id=sample_draft_session.id,
            game_number=1,
            step_number=1,
            step_type='ban',
            team='blue',
            champion_id=1
        )
        db_session.add(step)
        db_session.commit()

        assert step.id is not None
        assert step.step_type == 'ban'
        assert step.team == 'blue'

    def test_draft_step_repr(self, db_session, sample_draft_session):
        """Test DraftStep __repr__ method."""
        step = DraftStep(
            session_id=sample_draft_session.id,
            game_number=1,
            step_number=1,
            step_type='ban',
            team='blue',
            champion_id=1
        )
        assert 'ban' in repr(step)
        assert 'blue' in repr(step)

    def test_draft_step_to_dict(self, db_session, sample_draft_session):
        """Test DraftStep to_dict method."""
        step = DraftStep(
            session_id=sample_draft_session.id,
            game_number=1,
            step_number=1,
            step_type='ban',
            team='blue',
            champion_id=1
        )
        db_session.add(step)
        db_session.commit()

        step_dict = step.to_dict()
        assert step_dict['step_type'] == 'ban'
        assert step_dict['team'] == 'blue'
        assert step_dict['champion_id'] == 1
