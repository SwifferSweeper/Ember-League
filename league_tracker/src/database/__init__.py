from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()

# Enable foreign key support for SQLite only
# (PostgreSQL supports FKs natively)
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    # Only run PRAGMA for SQLite (connection string contains 'sqlite')
    dialect = dbapi_conn.__class__.__module__
    if 'sqlite' in dialect.lower():
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Admin(db.Model):
    """Admin user for managing the application."""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def set_password(self, password):
        """Set password hash from plain text password."""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash."""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'


class Team(db.Model):
    """Team model representing a registered league team."""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Team {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'player_count': len(self.players) if hasattr(self, 'players') else 0
        }


class Player(db.Model):
    """Player model representing a registered player."""
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    puuid = db.Column(db.String(100), nullable=True)  # No UNIQUE constraint - may be NULL for players without Riot ID
    game_name = db.Column(db.String(50), nullable=False)
    tag_line = db.Column(db.String(10), nullable=False)
    region = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    @property
    def display_name(self):
        """Return the player's display name (game_name#tag_line)."""
        return f"{self.game_name}#{self.tag_line}"
    
    def __repr__(self):
        return f'<Player {self.game_name}#{self.tag_line}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'puuid': self.puuid,
            'game_name': self.game_name,
            'tag_line': self.tag_line,
            'region': self.region,
            'display_name': f"{self.game_name}#{self.tag_line}"
        }


# Association table for team-player relationships
team_players = db.Table('team_players',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('players.id'), primary_key=True),
    db.Column('is_captain', db.Boolean, default=False)
)


# Add relationship after both models are defined
Team.players = db.relationship('Player', secondary=team_players, 
                               backref=db.backref('teams', lazy='dynamic'))


class Match(db.Model):
    """Match model representing a league match."""
    __tablename__ = 'match_table'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.String(50), unique=True, nullable=False)
    game_duration = db.Column(db.Integer)  # in seconds
    game_version = db.Column(db.String(20))
    game_creation = db.Column(db.BigInteger)  # timestamp in ms
    queue_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Team references (nullable for solo queue matches)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    
    def __repr__(self):
        return f'<Match {self.match_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'match_id': self.match_id,
            'game_duration': self.game_duration,
            'game_version': self.game_version,
            'game_creation': self.game_creation,
            'queue_id': self.queue_id,
            'home_team': self.home_team.name if self.home_team else None,
            'away_team': self.away_team.name if self.away_team else None
        }


class MatchParticipant(db.Model):
    """Individual player stats in a match."""
    __tablename__ = 'match_participant'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match_table.id'), nullable=False)
    puuid = db.Column(db.String(100), nullable=False)
    
    # Player info
    champion_id = db.Column(db.Integer)
    champion_name = db.Column(db.String(50))
    team_id = db.Column(db.Integer)  # 100 = blue, 200 = red
    
    # Match stats
    win = db.Column(db.Boolean)
    kills = db.Column(db.Integer)
    deaths = db.Column(db.Integer)
    assists = db.Column(db.Integer)
    kda = db.Column(db.Float)
    
    # Additional stats
    total_damage_dealt = db.Column(db.Integer)
    gold_earned = db.Column(db.Integer)
    cs = db.Column(db.Integer)  # creep score
    vision_score = db.Column(db.Integer)
    
    # Items
    item_0 = db.Column(db.Integer)
    item_1 = db.Column(db.Integer)
    item_2 = db.Column(db.Integer)
    item_3 = db.Column(db.Integer)
    item_4 = db.Column(db.Integer)
    item_5 = db.Column(db.Integer)
    item_6 = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Participant {self.champion_name} KDA:{self.kda}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'puuid': self.puuid,
            'champion_id': self.champion_id,
            'champion_name': self.champion_name,
            'team_id': self.team_id,
            'win': self.win,
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'kda': self.kda,
            'gold_earned': self.gold_earned,
            'cs': self.cs,
            'vision_score': self.vision_score
        }


# Add match relationships after all models are defined
Match.home_team = db.relationship('Team', foreign_keys=[Match.home_team_id], 
                                   backref='home_matches')
Match.away_team = db.relationship('Team', foreign_keys=[Match.away_team_id], 
                                   backref='away_matches')
Match.participants = db.relationship('MatchParticipant', backref='match', lazy='dynamic')


class TournamentCode(db.Model):
    """Tournament code tracking for automatic match detection."""
    __tablename__ = 'tournament_codes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    tournament_name = db.Column(db.String(100))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    match_id = db.Column(db.String(50), nullable=True)  # Associated match when used
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    used_at = db.Column(db.DateTime, nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<TournamentCode {self.code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'tournament_name': self.tournament_name,
            'team_id': self.team_id,
            'match_id': self.match_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'is_used': self.is_used
        }


# Add relationship after model definition
TournamentCode.team = db.relationship('Team', backref='tournament_codes')


# ==================== DRAFT MODELS ====================

class DraftSession(db.Model):
    """Session for tracking a draft (e.g., a series of games)."""
    __tablename__ = 'draft_sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    draft_mode = db.Column(db.String(20), nullable=False)  # 'normal', 'fearless', 'ironman'
    team_blue_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team_red_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    
    # Draft settings
    bans_per_team = db.Column(db.Integer, default=5)
    picks_per_team = db.Column(db.Integer, default=5)
    
    # State
    is_active = db.Column(db.Boolean, default=True)
    current_game_number = db.Column(db.Integer, default=1)
    current_phase = db.Column(db.String(20), default='bans')  # 'bans', 'picks'
    current_team_turn = db.Column(db.String(20), default='blue')  # 'blue', 'red'
    step_number = db.Column(db.Integer, default=1)  # Current step in draft
    
    # Timer state
    timer_started_at = db.Column(db.DateTime, nullable=True)  # When current timer started
    timer_duration = db.Column(db.Integer, default=30)  # Timer duration in seconds
    
    # Captain tracking
    blue_captain_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    red_captain_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    team_blue = db.relationship('Team', foreign_keys=[team_blue_id])
    team_red = db.relationship('Team', foreign_keys=[team_red_id])
    blue_captain = db.relationship('Player', foreign_keys=[blue_captain_id])
    red_captain = db.relationship('Player', foreign_keys=[red_captain_id])
    games = db.relationship('DraftGame', backref='session', lazy='dynamic', order_by='DraftGame.game_number')
    
    def __repr__(self):
        return f'<DraftSession {self.name} ({self.draft_mode})>'
    
    def get_current_timer_remaining(self):
        """Get remaining seconds on current timer."""
        if not self.timer_started_at:
            return self.timer_duration
        from datetime import datetime
        elapsed = (datetime.utcnow() - self.timer_started_at).total_seconds()
        remaining = self.timer_duration - int(elapsed)
        return max(0, remaining)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'draft_mode': self.draft_mode,
            'team_blue': self.team_blue.to_dict() if self.team_blue else None,
            'team_red': self.team_red.to_dict() if self.team_red else None,
            'bans_per_team': self.bans_per_team,
            'picks_per_team': self.picks_per_team,
            'current_game_number': self.current_game_number,
            'current_phase': self.current_phase,
            'current_team_turn': self.current_team_turn,
            'step_number': self.step_number,
            'is_active': self.is_active,
            'timer_remaining': self.get_current_timer_remaining(),
            'timer_duration': self.timer_duration,
            'blue_captain_id': self.blue_captain_id,
            'red_captain_id': self.red_captain_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DraftGame(db.Model):
    """Individual game within a draft session."""
    __tablename__ = 'draft_games'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('draft_sessions.id'), nullable=False)
    game_number = db.Column(db.Integer, nullable=False)
    
    # Bans and picks stored as JSON
    bans_blue = db.Column(db.JSON, default=[])  # List of champion IDs
    bans_red = db.Column(db.JSON, default=[])
    
    picks_blue = db.Column(db.JSON, default=[])  # List of champion IDs per position
    picks_red = db.Column(db.JSON, default=[])
    
    # Ironman mode: champion assignments per player
    ironman_assignments = db.Column(db.JSON, default={})  # {player_id: champion_id}
    
    # Fearless mode: previously banned/picked champions
    unavailable_champions = db.Column(db.JSON, default=[])
    
    # Game links for each team and spectators
    blue_side_link = db.Column(db.String(255), nullable=True)
    red_side_link = db.Column(db.String(255), nullable=True)
    spectator_link = db.Column(db.String(255), nullable=True)
    
    # Ready status for each team
    blue_ready = db.Column(db.Boolean, default=False)
    red_ready = db.Column(db.Boolean, default=False)
    
    # Match started flag (timer starts when both teams are ready)
    match_started = db.Column(db.Boolean, default=False)
    match_started_at = db.Column(db.DateTime, nullable=True)
    
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<DraftGame session={self.session_id} game={self.game_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'game_number': self.game_number,
            'bans_blue': self.bans_blue or [],
            'bans_red': self.bans_red or [],
            'picks_blue': self.picks_blue or [],
            'picks_red': self.picks_red or [],
            'ironman_assignments': self.ironman_assignments or {},
            'unavailable_champions': self.unavailable_champions or [],
            'blue_side_link': self.blue_side_link,
            'red_side_link': self.red_side_link,
            'spectator_link': self.spectator_link,
            'blue_ready': self.blue_ready,
            'red_ready': self.red_ready,
            'match_started': self.match_started,
            'match_started_at': self.match_started_at.isoformat() if self.match_started_at else None,
            'is_completed': self.is_completed
        }


class DraftStep(db.Model):
    """Individual ban/pick action in a draft."""
    __tablename__ = 'draft_steps'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('draft_sessions.id'), nullable=False)
    game_number = db.Column(db.Integer, nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    
    step_type = db.Column(db.String(20), nullable=False)  # 'ban', 'pick'
    team = db.Column(db.String(20), nullable=False)  # 'blue', 'red'
    champion_id = db.Column(db.Integer, nullable=True)
    position = db.Column(db.String(20), nullable=True)  # For picks: 'top', 'jungle', 'mid', 'adc', 'support'
    
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)  # For ironman mode
    
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationships
    player = db.relationship('Player')
    
    def __repr__(self):
        return f'<DraftStep {self.step_type} {self.team} champion={self.champion_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'game_number': self.game_number,
            'step_number': self.step_number,
            'step_type': self.step_type,
            'team': self.team,
            'champion_id': self.champion_id,
            'position': self.position,
            'player_id': self.player_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Add relationship after model definition
DraftSession.team_blue = db.relationship('Team', foreign_keys=[DraftSession.team_blue_id])
DraftSession.team_red = db.relationship('Team', foreign_keys=[DraftSession.team_red_id])
DraftSession.steps = db.relationship('DraftStep', backref='session', 
                                      order_by='DraftStep.step_number', lazy='dynamic')


# ==================== INHOUSE STATS MODELS ====================


class InhouseMatch(db.Model):
    """Match record for inhouse games."""
    __tablename__ = 'inhouse_matches'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    game_date = db.Column(db.DateTime, nullable=False)
    game_duration_min = db.Column(db.Float, nullable=False)
    queue_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationships
    participants = db.relationship('InhouseParticipant', backref='match', lazy='dynamic', 
                                   cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<InhouseMatch {self.match_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'match_id': self.match_id,
            'game_date': self.game_date.isoformat() if self.game_date else None,
            'game_duration_min': self.game_duration_min,
            'queue_id': self.queue_id,
            'participant_count': self.participants.count()
        }


class InhouseParticipant(db.Model):
    """Individual player stats in an inhouse match."""
    __tablename__ = 'inhouse_participants'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey('inhouse_matches.id'), nullable=False)
    
    # Player identification
    summoner_name = db.Column(db.String(50), nullable=False)
    tag = db.Column(db.String(10))
    puuid = db.Column(db.String(100))
    
    # Team and champion
    team = db.Column(db.String(10), nullable=False)  # 'Blue' or 'Red'
    champion = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20))
    
    # Game result
    win = db.Column(db.Boolean, nullable=False)
    
    # KDA stats
    kills = db.Column(db.Integer, default=0)
    deaths = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    kda = db.Column(db.Float, default=0.0)
    
    # Multi-kills
    double_kills = db.Column(db.Integer, default=0)
    triple_kills = db.Column(db.Integer, default=0)
    quadra_kills = db.Column(db.Integer, default=0)
    penta_kills = db.Column(db.Integer, default=0)
    
    # Damage stats
    total_damage_to_champions = db.Column(db.Integer, default=0)
    damage_per_min = db.Column(db.Float, default=0.0)
    physical_damage = db.Column(db.Integer, default=0)
    magic_damage = db.Column(db.Integer, default=0)
    true_damage = db.Column(db.Integer, default=0)
    damage_taken = db.Column(db.Integer, default=0)
    damage_mitigated = db.Column(db.Integer, default=0)
    
    # CS and Gold
    cs = db.Column(db.Integer, default=0)
    cs_per_min = db.Column(db.Float, default=0.0)
    gold_earned = db.Column(db.Integer, default=0)
    gold_per_min = db.Column(db.Float, default=0.0)
    
    # Vision
    vision_score = db.Column(db.Integer, default=0)
    wards_placed = db.Column(db.Integer, default=0)
    wards_killed = db.Column(db.Integer, default=0)
    control_wards_bought = db.Column(db.Integer, default=0)
    
    # Objectives
    turret_kills = db.Column(db.Integer, default=0)
    turret_damage = db.Column(db.Integer, default=0)
    objective_damage = db.Column(db.Integer, default=0)
    
    # Team objectives
    team_dragons = db.Column(db.Integer, default=0)
    team_first_dragon = db.Column(db.Boolean, default=False)
    team_barons = db.Column(db.Integer, default=0)
    team_first_baron = db.Column(db.Boolean, default=False)
    team_heralds = db.Column(db.Integer, default=0)
    team_first_herald = db.Column(db.Boolean, default=False)
    team_grubs = db.Column(db.Integer, default=0)
    team_first_grubs = db.Column(db.Boolean, default=False)
    team_towers = db.Column(db.Integer, default=0)
    team_first_tower = db.Column(db.Boolean, default=False)
    team_first_blood = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<InhouseParticipant {self.summoner_name} {self.champion}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'match_id': self.match_id,
            'summoner_name': self.summoner_name,
            'tag': self.tag,
            'team': self.team,
            'champion': self.champion,
            'role': self.role,
            'win': self.win,
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'kda': self.kda,
            'cs': self.cs,
            'gold_earned': self.gold_earned,
            'vision_score': self.vision_score
        }
