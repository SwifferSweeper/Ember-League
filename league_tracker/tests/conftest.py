"""
Pytest configuration and fixtures for league_tracker tests.
"""
import pytest
import os
import tempfile
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from src.database import db, Team, Player, Match, MatchParticipant, Admin, DraftSession, DraftGame


@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test session."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    # Clean up the temporary database file
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for a test."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        session = db.session
        session.begin_nested()
        
        yield session
        
        session.rollback()
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def authenticated_client(app, sample_admin):
    """Create an authenticated test client."""
    client = app.test_client()
    
    # Login as admin
    with client.session_transaction() as sess:
        sess['admin_id'] = sample_admin.id
    
    return client


@pytest.fixture(scope='function')
def sample_admin(db_session):
    """Create a sample admin user."""
    admin = Admin(username='testadmin')
    admin.set_password('test_password')
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture(scope='function')
def sample_team(db_session):
    """Create a sample team."""
    team = Team(name='Test Team')
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture(scope='function')
def sample_player(db_session):
    """Create a sample player."""
    player = Player(
        puuid='test-puuid-12345',
        game_name='TestPlayer',
        tag_line='NA1',
        region='na1'
    )
    db_session.add(player)
    db_session.commit()
    return player


@pytest.fixture(scope='function')
def sample_team_with_players(db_session):
    """Create a sample team with players."""
    team = Team(name='Team With Players')
    db_session.add(team)
    db_session.flush()
    
    players = []
    for i in range(5):
        player = Player(
            puuid=f'test-puuid-{i}',
            game_name=f'Player{i}',
            tag_line='NA1',
            region='na1'
        )
        db_session.add(player)
        players.append(player)
    
    db_session.flush()
    
    for player in players:
        team.players.append(player)
    
    db_session.commit()
    return team


@pytest.fixture(scope='function')
def sample_match(db_session, sample_team):
    """Create a sample match."""
    match = Match(
        match_id='NA1_1234567890',
        game_duration=1800,
        game_version='14.1.1',
        game_creation=1704067200000,
        queue_id=0,
        home_team_id=sample_team.id
    )
    db_session.add(match)
    db_session.flush()
    
    # Add a participant
    participant = MatchParticipant(
        match_id=match.id,
        puuid='test-puuid-12345',
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
    
    # Refresh to load relationships
    db_session.refresh(match)
    return match


@pytest.fixture(scope='function')
def sample_draft_session(db_session, sample_team):
    """Create a sample draft session."""
    team2 = Team(name='Opponent Team')
    db_session.add(team2)
    db_session.flush()
    
    session = DraftSession(
        name='Test Draft',
        draft_mode='normal',
        team_blue_id=sample_team.id,
        team_red_id=team2.id,
        bans_per_team=5,
        picks_per_team=5
    )
    db_session.add(session)
    db_session.flush()
    
    # Create a game for the session
    game = DraftGame(
        session_id=session.id,
        game_number=1,
        bans_blue=[],
        bans_red=[],
        picks_blue=[],
        picks_red=[]
    )
    db_session.add(game)
    db_session.commit()
    
    # Refresh to load relationships
    db_session.refresh(session)
    return session


@pytest.fixture(scope='function', autouse=False)
def mock_riot_api_key(monkeypatch):
    """Mock the Riot API key for testing."""
    monkeypatch.setenv('RIOT_API_KEY', 'test-api-key')
    return 'test-api-key'
