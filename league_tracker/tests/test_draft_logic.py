"""
Unit tests for Draft Logic module.
"""
import pytest

from src.database import Team
from src.utils.draft_logic import (
    DraftOrderGenerator, DraftModeValidator, DraftSessionManager
)


@pytest.mark.unit
class TestDraftOrderGenerator:
    """Tests for DraftOrderGenerator class."""

    def test_generate_ban_order(self):
        """Test generating ban order."""
        order = DraftOrderGenerator.generate_ban_order(5, 1)
        assert len(order) == 10  # 5 bans per team

        # Check first phase (3 bans each, blue starts)
        assert order[0] == ('blue', 'ban', 1)
        assert order[1] == ('red', 'ban', 1)
        assert order[2] == ('blue', 'ban', 2)
        assert order[3] == ('red', 'ban', 2)
        assert order[4] == ('blue', 'ban', 3)
        assert order[5] == ('red', 'ban', 3)

        # Check second phase (2 bans each, red starts)
        assert order[6] == ('red', 'ban', 4)
        assert order[7] == ('blue', 'ban', 4)
        assert order[8] == ('red', 'ban', 5)
        assert order[9] == ('blue', 'ban', 5)

    def test_generate_pick_order(self):
        """Test generating pick order."""
        order = DraftOrderGenerator.generate_pick_order(5, 1, 'normal')
        assert len(order) == 10  # 5 picks per team

        # Check phase 1 (3 picks each, blue starts)
        assert order[0] == ('blue', 'pick', 1)
        assert order[1] == ('red', 'pick', 1)
        assert order[2] == ('red', 'pick', 2)
        assert order[3] == ('blue', 'pick', 2)
        assert order[4] == ('blue', 'pick', 3)
        assert order[5] == ('red', 'pick', 3)

        # Check phase 2 (2 picks each, red starts)
        assert order[6] == ('red', 'pick', 4)
        assert order[7] == ('blue', 'pick', 4)
        assert order[8] == ('blue', 'pick', 5)
        assert order[9] == ('red', 'pick', 5)

    def test_get_full_draft_order(self):
        """Test getting full draft order."""
        order = DraftOrderGenerator.get_full_draft_order(5, 5, 1, 'normal')
        assert len(order) == 20  # 10 bans + 10 picks

        # First 10 should be bans
        for i in range(10):
            assert order[i][1] == 'ban'

        # Last 10 should be picks
        for i in range(10, 20):
            assert order[i][1] == 'pick'


@pytest.mark.unit
class TestDraftModeValidator:
    """Tests for DraftModeValidator class."""

    @pytest.fixture
    def validator(self, sample_draft_session):
        """Create a DraftModeValidator instance."""
        game = sample_draft_session.games[0]
        return DraftModeValidator(sample_draft_session, game, 'blue')

    def test_can_pick_normal_available(self, validator):
        """Test picking available champion in normal mode."""
        validator.session.draft_mode = 'normal'
        assert validator.can_pick_champion(1) is True

    def test_can_pick_normal_picked(self, validator):
        """Test picking already picked champion in normal mode."""
        validator.session.draft_mode = 'normal'
        validator.game.picks_blue = [{'champion_id': 1}]
        assert validator.can_pick_champion(1) is False

    def test_can_pick_normal_banned(self, validator):
        """Test picking banned champion in normal mode."""
        validator.session.draft_mode = 'normal'
        validator.game.bans_blue = [1]
        assert validator.can_pick_champion(1) is False

    def test_can_pick_fearless_unavailable(self, validator):
        """Test picking unavailable champion in fearless mode."""
        validator.session.draft_mode = 'fearless'
        validator.game.unavailable_champions = [1]
        assert validator.can_pick_champion(1) is False

    def test_can_pick_ironman(self, validator):
        """Test picking in ironman mode."""
        validator.session.draft_mode = 'ironman'
        # Ironman should work like fearless for now
        assert validator.can_pick_champion(1) is True

    def test_can_ban_normal(self, validator):
        """Test banning in normal mode."""
        validator.session.draft_mode = 'normal'
        assert validator.can_ban_champion(1) is True

    def test_can_ban_fearless_unavailable(self, validator):
        """Test banning unavailable champion in fearless mode."""
        validator.session.draft_mode = 'fearless'
        validator.game.unavailable_champions = [1]
        assert validator.can_ban_champion(1) is False

    def test_get_available_champions_normal(self, validator):
        """Test getting available champions in normal mode."""
        validator.session.draft_mode = 'normal'
        validator.game.picks_blue = [{'champion_id': 1}]
        validator.game.bans_blue = [2]

        available = validator.get_available_champions()
        assert isinstance(available, list)
        # Champion 1 and 2 should not be available
        champ_ids = [c['id'] for c in available]
        assert 1 not in champ_ids
        assert 2 not in champ_ids

    def test_get_available_champions_fearless(self, validator):
        """Test getting available champions in fearless mode."""
        validator.session.draft_mode = 'fearless'
        validator.game.unavailable_champions = [1, 2, 3]

        available = validator.get_available_champions()
        champ_ids = [c['id'] for c in available]
        assert 1 not in champ_ids
        assert 2 not in champ_ids
        assert 3 not in champ_ids

    def test_get_available_champions_ironman_with_position(self, validator):
        """Test getting available champions in ironman mode with position."""
        validator.session.draft_mode = 'ironman'
        validator.game.unavailable_champions = []

        available = validator.get_available_champions(player_id=1, position='top')
        assert isinstance(available, list)


@pytest.mark.unit
class TestDraftSessionManager:
    """Tests for DraftSessionManager class."""

    def test_generate_game_links(self):
        """Test generating game links."""
        links = DraftSessionManager.generate_game_links(1, 1)

        assert 'blue_side_link' in links
        assert 'red_side_link' in links
        assert 'spectator_link' in links

        assert '/game/1/1/blue/' in links['blue_side_link']
        assert '/game/1/1/red/' in links['red_side_link']
        assert '/game/1/1/spectator/' in links['spectator_link']

    def test_generate_game_links_unique(self):
        """Test that game links are unique."""
        links1 = DraftSessionManager.generate_game_links(1, 1)
        links2 = DraftSessionManager.generate_game_links(1, 1)

        assert links1['blue_side_link'] != links2['blue_side_link']
        assert links1['red_side_link'] != links2['red_side_link']
        assert links1['spectator_link'] != links2['spectator_link']

    def test_create_session(self, db_session, sample_team):
        """Test creating a draft session."""
        team2 = Team(name='Opponent Team')
        db_session.add(team2)
        db_session.commit()

        session = DraftSessionManager.create_session(
            name='Test Draft',
            draft_mode='normal',
            team_blue_id=sample_team.id,
            team_red_id=team2.id,
            bans_per_team=5,
            picks_per_team=5
        )

        assert session.id is not None
        assert session.name == 'Test Draft'
        assert session.draft_mode == 'normal'
        assert session.is_active is True
        assert session.current_game_number == 1
        assert session.current_phase == 'bans'
        assert session.current_team_turn == 'blue'

    def test_create_session_creates_game(self, db_session, sample_team):
        """Test that creating a session creates the first game."""
        team2 = Team(name='Opponent Team')
        db_session.add(team2)
        db_session.commit()

        session = DraftSessionManager.create_session(
            name='Test Draft',
            draft_mode='normal',
            team_blue_id=sample_team.id,
            team_red_id=team2.id
        )

        games = session.games.all()
        assert len(games) == 1
        assert games[0].game_number == 1

    def test_is_team_captain_blue(self, db_session, sample_draft_session):
        """Test checking if player is blue team captain."""
        from src.database import Player
        player = Player(game_name='Captain', tag_line='NA1', region='na1')
        db_session.add(player)
        db_session.commit()

        sample_draft_session.blue_captain_id = player.id
        db_session.commit()

        is_captain = DraftSessionManager.is_team_captain(
            sample_draft_session.id, 'blue', player.id
        )
        assert is_captain is True

    def test_is_team_captain_red(self, db_session, sample_draft_session):
        """Test checking if player is red team captain."""
        from src.database import Player
        player = Player(game_name='Captain', tag_line='NA1', region='na1')
        db_session.add(player)
        db_session.commit()

        sample_draft_session.red_captain_id = player.id
        db_session.commit()

        is_captain = DraftSessionManager.is_team_captain(
            sample_draft_session.id, 'red', player.id
        )
        assert is_captain is True

    def test_is_team_captain_false(self, db_session, sample_draft_session):
        """Test checking if non-captain is captain."""
        from src.database import Player
        player = Player(game_name='Player', tag_line='NA1', region='na1')
        db_session.add(player)
        db_session.commit()

        is_captain = DraftSessionManager.is_team_captain(
            sample_draft_session.id, 'blue', player.id
        )
        assert is_captain is False

    def test_can_player_act(self, db_session, sample_draft_session):
        """Test checking if player can act."""
        can_act = DraftSessionManager.can_player_act(
            sample_draft_session.id, 'blue'
        )
        assert can_act is True

    def test_get_session_state(self, db_session, sample_draft_session):
        """Test getting session state."""
        state = DraftSessionManager.get_session_state(sample_draft_session.id)

        assert state is not None
        assert 'session' in state
        assert 'game' in state
        assert 'steps' in state
        assert 'ban_order' in state
        assert 'pick_order' in state

    def test_get_session_state_nonexistent(self, db_session):
        """Test getting state for nonexistent session."""
        state = DraftSessionManager.get_session_state(999999)
        assert state is None

    def test_set_team_ready_blue(self, db_session, sample_draft_session):
        """Test setting blue team as ready."""
        game = sample_draft_session.games[0]
        result = DraftSessionManager.set_team_ready(
            sample_draft_session.id, 1, 'blue'
        )

        assert result.blue_ready is True
        assert result.red_ready is False

    def test_set_team_ready_both(self, db_session, sample_draft_session):
        """Test setting both teams as ready."""
        game = sample_draft_session.games[0]
        DraftSessionManager.set_team_ready(sample_draft_session.id, 1, 'blue')
        result = DraftSessionManager.set_team_ready(sample_draft_session.id, 1, 'red')

        assert result.blue_ready is True
        assert result.red_ready is True
        assert result.match_started is True

    def test_set_team_ready_invalid_team(self, db_session, sample_draft_session):
        """Test setting invalid team as ready."""
        with pytest.raises(ValueError, match='Invalid team color'):
            DraftSessionManager.set_team_ready(
                sample_draft_session.id, 1, 'invalid'
            )

    def test_reset_game(self, db_session, sample_draft_session):
        """Test resetting a game."""
        game = sample_draft_session.games[0]
        game.bans_blue = [1, 2, 3]
        game.picks_blue = [{'champion_id': 4}]
        db_session.commit()

        result = DraftSessionManager.reset_game(sample_draft_session.id, 1)

        assert result.bans_blue == []
        assert result.picks_blue == []
        assert result.is_completed is False

    def test_get_series_history(self, db_session, sample_draft_session):
        """Test getting series history."""
        history = DraftSessionManager.get_series_history(sample_draft_session.id)

        assert isinstance(history, list)
        if history:
            game_history = history[0]
            assert 'game_number' in game_history
            assert 'is_completed' in game_history
            assert 'bans_blue' in game_history
            assert 'bans_red' in game_history
            assert 'picks_blue' in game_history
            assert 'picks_red' in game_history
            assert 'steps' in game_history
