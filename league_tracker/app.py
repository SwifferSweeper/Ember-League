from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import sys
import os
import atexit

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import config using absolute import for gunicorn compatibility
from league_tracker.config import SECRET_KEY, DEBUG, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SQLALCHEMY_ENGINE_OPTIONS, \
                   RIOT_API_KEY, validate_api_key, AUTO_COLLECT_ENABLED, AUTO_COLLECT_INTERVAL
from league_tracker.src.database import db, Team, Player, Match, MatchParticipant, Admin, team_players, TournamentCode, DraftSession, DraftGame, DraftStep, InhouseMatch, InhouseParticipant
from league_tracker.src.api.riot_client import RiotClient, RiotAPIError
from league_tracker.src.api.match_collector import MatchCollector, run_collect
from league_tracker.src.utils.stats_calculator import StatsCalculator
from league_tracker.src.utils.champions import get_all_champions, get_champion_by_id, get_champion_name, CHAMPIONS
from league_tracker.src.utils.draft_logic import DraftSessionManager, DraftModeValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_timestamp(timestamp_ms):
    """Format timestamp from milliseconds to readable date."""
    if not timestamp_ms:
        return "Unknown"
    from datetime import datetime
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%b %d, %Y %H:%M")
    except:
        return "Unknown"


def format_duration(seconds):
    """Format duration in seconds to MM:SS."""
    if not seconds:
        return "0:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


# Global scheduler instance
scheduler = None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def start_scheduler(app):
    """Start APScheduler safely for Railway deployment."""
    global scheduler
    
    # Prevent double-start on reload (Flask debug mode)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or app.debug:
        return None
    
    if scheduler is not None:
        return scheduler
    
    if not AUTO_COLLECT_ENABLED:
        logger.info("Auto-collect disabled")
        return None
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: run_collect(app),
        trigger='interval',
        minutes=AUTO_COLLECT_INTERVAL,
        id='match_collection',
        name='Collect match data for all players'
    )
    scheduler.start()
    logger.info(f"Scheduler started (interval {AUTO_COLLECT_INTERVAL} min)")
    
    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler and scheduler.running else None)
    return scheduler

def create_app():
    """Create Flask app."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(__name__,
                template_folder=os.path.join(app_dir, 'templates'),
                static_folder=os.path.join(app_dir, 'static'))
    
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    
    # Register custom Jinja2 filters and globals
    app.jinja_env.filters['format_timestamp'] = format_timestamp
    app.jinja_env.filters['format_duration'] = format_duration
    app.jinja_env.globals['format_timestamp'] = format_timestamp
    app.jinja_env.globals['format_duration'] = format_duration
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            admin = Admin(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin")
    
    # Riot client lazy init
    app.config['RIOT_CLIENT_FACTORY'] = lambda: RiotClient()
    app.config['RIOT_CLIENT'] = None
    def get_riot_client():
        if app.config.get('RIOT_CLIENT') is None:
            try:
                app.config['RIOT_CLIENT'] = app.config['RIOT_CLIENT_FACTORY']()
            except RiotAPIError:
                logger.warning("Riot API key missing")
                app.config['RIOT_CLIENT'] = False
        return app.config['RIOT_CLIENT'] if app.config['RIOT_CLIENT'] else None
    app.get_riot_client = get_riot_client
    
    # ==================== ROUTES ====================
    
    @app.route('/')
    def index():
        """Home page."""
        total_teams = Team.query.count()
        total_players = Player.query.count()
        total_matches = Match.query.count()
        teams = Team.query.order_by(Team.created_at.desc()).limit(6).all()
        return render_template('index.html', total_teams=total_teams, total_players=total_players, total_matches=total_matches, teams=teams)
    
    @app.route('/teams')
    def teams_list():
        """List all teams."""
        teams = Team.query.all()
        return render_template('teams.html', teams=teams)
    
    @app.route('/leaderboards')
    def leaderboards():
        """Leaderboards page."""
        return render_template('leaderboards.html')
    
    @app.route('/league/matches')
    def league_matches():
        """List all league matches."""
        matches = Match.query.order_by(Match.game_creation.desc()).all()
        return render_template('league_matches.html', matches=matches)
    
    @app.route('/teams/<int:team_id>')
    def team_detail(team_id):
        """Team detail page."""
        team = Team.query.get_or_404(team_id)
        return render_template('team_detail.html', team=team)
    
    @app.route('/matches/<match_id>')
    def match_detail(match_id):
        """Match detail page."""
        match = Match.query.filter_by(match_id=match_id).first_or_404()
        participants = MatchParticipant.query.filter_by(match_id=match.id).all()
        # Create a dictionary mapping puuid to Player for quick lookup
        players = {p.puuid: p for p in Player.query.all() if p.puuid}
        return render_template('match_detail.html', match=match, participants=participants, players=players)
    
    @app.route('/players/<puuid>/history')
    def player_league_history(puuid):
        """Player match history page."""
        player = Player.query.filter_by(puuid=puuid).first_or_404()
        queue_type = request.args.get('type', 'ranked')  # Default to ranked
        
        # Always join with Match to allow ordering by game_creation
        query = MatchParticipant.query.filter_by(puuid=puuid).join(Match)
        
        if queue_type == 'ranked':
            # Filter for ranked games (queue_id 400, 420, 440)
            query = query.filter(Match.queue_id.in_([400, 420, 440]))
        elif queue_type == 'tournament':
            # Filter for tournament games
            query = query.filter(Match.queue_id.in_([0, 3130]))
        # 'all' removed - now only shows ranked or tournament
        
        participants = query.order_by(Match.game_creation.desc()).all()
        # Add match_id to each participant for template access
        for p in participants:
            p._match_id = p.match.match_id if hasattr(p, 'match') and p.match else None
        return render_template('player_history.html', player=player, participants=participants, queue_type=queue_type)
    
    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        """Team signup page."""
        if request.method == 'POST':
            team_name = request.form.get('team_name')
            player_names = request.form.getlist('player_name[]')
            player_tags = request.form.getlist('player_tag[]')
            player_regions = request.form.getlist('player_region[]')
            
            if not team_name:
                flash('Team name is required', 'error')
                return render_template('signup.html', riot_client=get_riot_client())
            
            # Create team
            team = Team(name=team_name)
            db.session.add(team)
            db.session.flush()
            
            # Create players
            for name, tag, region in zip(player_names, player_tags, player_regions):
                if name and tag:
                    # Try to get puuid from Riot API
                    puuid = None
                    riot_client = get_riot_client()
                    if riot_client:
                        try:
                            puuid = riot_client.get_puuid_from_riot_id(name, tag, region)
                            logger.info(f"Looked up puuid for {name}#{tag}: {puuid}")
                        except Exception as e:
                            logger.warning(f"Failed to look up puuid for {name}#{tag}: {e}")
                    
                    player = Player(
                        game_name=name,
                        tag_line=tag,
                        region=region,
                        puuid=puuid
                    )
                    db.session.add(player)
                    db.session.flush()
                    team.players.append(player)
            
            db.session.commit()
            flash('Team registered successfully!', 'success')
            return redirect(url_for('teams_list'))
        
        return render_template('signup.html', riot_client=get_riot_client())
    
    # ==================== ADMIN ROUTES ====================
    
    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        """Admin login page."""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            admin = Admin.query.filter_by(username=username).first()
            if admin and admin.check_password(password):
                session['admin_id'] = admin.id
                flash('Logged in successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('admin_login.html')
    
    @app.route('/admin/logout')
    def admin_logout():
        """Admin logout."""
        session.pop('admin_id', None)
        flash('Logged out successfully', 'success')
        return redirect(url_for('admin_login'))
    
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        """Admin dashboard."""
        return render_template('admin_dashboard.html')
    
    @app.route('/admin/drafts')
    @admin_required
    def admin_drafts():
        """Admin drafts management."""
        drafts = DraftSession.query.order_by(DraftSession.created_at.desc()).all()
        return render_template('admin_drafts.html', drafts=drafts)
    
    @app.route('/admin/drafts/<int:draft_id>')
    @admin_required
    def admin_draft_detail(draft_id):
        """Admin draft detail."""
        draft = DraftSession.query.get_or_404(draft_id)
        return render_template('admin_draft_detail.html', draft=draft)
    
    @app.route('/admin/drafts/create', methods=['GET', 'POST'])
    @admin_required
    def admin_create_draft():
        """Create new draft."""
        if request.method == 'POST':
            # Draft creation logic
            flash('Draft created successfully', 'success')
            return redirect(url_for('admin_drafts'))
        teams = Team.query.all()
        return render_template('admin_edit_draft.html', teams=teams, draft=None)
    
    @app.route('/admin/drafts/<int:draft_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_draft(draft_id):
        """Edit existing draft."""
        draft = DraftSession.query.get_or_404(draft_id)
        if request.method == 'POST':
            # Update draft logic
            flash('Draft updated successfully', 'success')
            return redirect(url_for('admin_draft_detail', draft_id=draft.id))
        teams = Team.query.all()
        return render_template('admin_edit_draft.html', teams=teams, draft=draft)
    
    @app.route('/admin/teams')
    @admin_required
    def admin_teams():
        """Admin teams management."""
        teams = Team.query.all()
        return render_template('admin_teams.html', teams=teams)
    
    @app.route('/admin/teams/<int:team_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_team(team_id):
        """Edit team."""
        team = Team.query.get_or_404(team_id)
        if request.method == 'POST':
            team.name = request.form.get('name')
            db.session.commit()
            flash('Team updated successfully', 'success')
            return redirect(url_for('admin_teams'))
        return render_template('admin_edit_team.html', team=team)
    
    @app.route('/admin/players')
    @admin_required
    def admin_players():
        """Admin players management."""
        players = Player.query.all()
        return render_template('admin_manage_players.html', players=players)
    
    @app.route('/admin/tournament-codes', methods=['GET', 'POST'])
    @admin_required
    def admin_tournament_codes():
        """Admin tournament codes management."""
        if request.method == 'POST':
            # Create tournament code logic
            flash('Tournament code created', 'success')
        codes = TournamentCode.query.order_by(TournamentCode.created_at.desc()).all()
        teams = Team.query.all()
        return render_template('admin_tournament_codes.html', codes=codes, teams=teams)
    
    @app.route('/admin/tournament-codes/add', methods=['POST'])
    @admin_required
    def admin_add_tournament_code():
        """Add a new tournament code."""
        code = request.form.get('code')
        tournament_name = request.form.get('tournament_name')
        team_id = request.form.get('team_id')
        
        if code:
            tc = TournamentCode(
                code=code,
                tournament_name=tournament_name,
                team_id=team_id if team_id else None
            )
            db.session.add(tc)
            db.session.commit()
            flash('Tournament code created', 'success')
        
        return redirect(url_for('admin_tournament_codes'))
    
    @app.route('/admin/tournament-codes/<int:code_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_tournament_code(code_id):
        """Delete a tournament code."""
        tc = TournamentCode.query.get_or_404(code_id)
        db.session.delete(tc)
        db.session.commit()
        flash('Tournament code deleted', 'success')
        return redirect(url_for('admin_tournament_codes'))
    
    @app.route('/admin/teams/<int:team_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_team(team_id):
        """Delete a team."""
        team = Team.query.get_or_404(team_id)
        db.session.delete(team)
        db.session.commit()
        flash('Team deleted', 'success')
        return redirect(url_for('admin_teams'))
    
    @app.route('/admin/drafts/<int:session_id>/toggle', methods=['POST'])
    @admin_required
    def admin_toggle_draft_active(session_id):
        """Toggle draft active status."""
        draft = DraftSession.query.get_or_404(session_id)
        draft.is_active = not draft.is_active
        if not draft.is_active:
            draft.completed_at = db.func.current_timestamp()
        db.session.commit()
        flash(f'Draft marked as {"complete" if not draft.is_active else "active"}', 'success')
        return redirect(url_for('admin_draft_detail', draft_id=session_id))
    
    @app.route('/admin/drafts/<int:session_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_draft(session_id):
        """Delete a draft session."""
        draft = DraftSession.query.get_or_404(session_id)
        db.session.delete(draft)
        db.session.commit()
        flash('Draft deleted', 'success')
        return redirect(url_for('admin_drafts'))
    
    @app.route('/admin/drafts/<int:session_id>/game/<int:game_number>/reset', methods=['POST'])
    @admin_required
    def admin_reset_game(session_id, game_number):
        """Reset a draft game."""
        game = DraftGame.query.filter_by(session_id=session_id, game_number=game_number).first_or_404()
        game.bans_blue = []
        game.bans_red = []
        game.picks_blue = []
        game.picks_red = []
        game.ironman_assignments = {}
        game.unavailable_champions = []
        game.blue_ready = False
        game.red_ready = False
        game.is_completed = False
        db.session.commit()
        flash('Game reset successfully', 'success')
        return redirect(url_for('admin_draft_detail', draft_id=session_id))
    
    # ==================== DRAFT ROUTES ====================
    
    @app.route('/draft')
    def draft_index():
        """Draft index page."""
        drafts = DraftSession.query.filter_by(is_active=True).order_by(DraftSession.created_at.desc()).all()
        return render_template('draft_index.html', drafts=drafts)
    
    @app.route('/draft/create', methods=['GET', 'POST'])
    def draft_create():
        """Create new draft session."""
        if request.method == 'POST':
            name = request.form.get('name')
            draft_mode = request.form.get('draft_mode')
            team_blue_id = request.form.get('team_blue_id')
            team_red_id = request.form.get('team_red_id')
            bans_per_team = request.form.get('bans_per_team', 5)
            
            if not all([name, draft_mode, team_blue_id, team_red_id]):
                flash('All fields are required', 'error')
                return render_template('draft_create.html')
            
            draft = DraftSession(
                name=name,
                draft_mode=draft_mode,
                team_blue_id=team_blue_id,
                team_red_id=team_red_id,
                bans_per_team=int(bans_per_team)
            )
            db.session.add(draft)
            db.session.commit()
            
            flash('Draft session created!', 'success')
            # Show the shareable links page
            return render_template('draft_created.html', draft=draft)
        
        teams = Team.query.all()
        return render_template('draft_create.html', teams=teams)
    
    @app.route('/draft/<int:draft_session_id>')
    @app.route('/draft/<int:draft_session_id>/<side>')
    def draft_view(draft_session_id, side=None):
        """View draft session."""
        draft_session = DraftSession.query.get_or_404(draft_session_id)
        
        # Validate side parameter and check if link is already claimed
        if side and side not in ['blue', 'red', 'spectator']:
            side = None
        
        # Check if blue or red link is already claimed (unless it's the same user returning)
        if side == 'blue' and draft_session.blue_link_claimed:
            # Check if this is the same user returning (stored in localStorage)
            flash('Blue side link has already been used. Please use the original link or refresh.', 'error')
            return render_template('draft_view.html', draft_session=draft_session, champions=get_all_champions(), user_side=None, link_expired=True)
        
        if side == 'red' and draft_session.red_link_claimed:
            flash('Red side link has already been used. Please use the original link or refresh.', 'error')
            return render_template('draft_view.html', draft_session=draft_session, champions=get_all_champions(), user_side=None, link_expired=True)
        
        # If valid side and not claimed, mark it as claimed
        if side in ['blue', 'red']:
            # Mark the side as claimed
            if side == 'blue':
                draft_session.blue_link_claimed = True
            else:
                draft_session.red_link_claimed = True
            db.session.commit()
        
        champions = get_all_champions()
        return render_template('draft_view.html', draft_session=draft_session, champions=champions, user_side=side)
    
    @app.route('/draft/<int:draft_session_id>/leave', methods=['POST'])
    def draft_leave(draft_session_id):
        """Leave a draft session and free up the side link."""
        draft_session = DraftSession.query.get_or_404(draft_session_id)
        side = request.form.get('side')
        
        if side == 'blue':
            draft_session.blue_link_claimed = False
        elif side == 'red':
            draft_session.red_link_claimed = False
        
        db.session.commit()
        flash(f'You have left the {side} side. The link is now available again.', 'success')
        return redirect(url_for('draft_index'))
    
    @app.route('/draft/<int:draft_session_id>/history')
    def draft_history(draft_session_id):
        """View draft history."""
        draft = DraftSession.query.get_or_404(draft_session_id)
        games = DraftGame.query.filter_by(session_id=draft_session_id).order_by(DraftGame.game_number).all()
        return render_template('draft_history.html', draft=draft, games=games)
    
    # ==================== API ROUTES ====================
    
    @app.route('/api/teams')
    def api_teams():
        """Get all teams."""
        teams = Team.query.all()
        return jsonify([team.to_dict() for team in teams])
    
    @app.route('/api/teams/<int:team_id>')
    def api_team_detail(team_id):
        """Get team details."""
        team = Team.query.get_or_404(team_id)
        return jsonify(team.to_dict())
    
    @app.route('/api/teams/register', methods=['POST'])
    def api_register_team():
        """Register a new team via API."""
        data = request.get_json()
        
        if not data or not data.get('team_name'):
            return jsonify({'error': 'team_name is required'}), 400
        
        team = Team(name=data['team_name'])
        db.session.add(team)
        db.session.flush()
        
        if data.get('players'):
            for player_data in data['players']:
                game_name = player_data.get('game_name')
                tag_line = player_data.get('tag_line')
                region = player_data.get('region', 'na1')
                
                # Try to get puuid from Riot API
                puuid = None
                riot_client = get_riot_client()
                if riot_client:
                    try:
                        puuid = riot_client.get_puuid_from_riot_id(game_name, tag_line, region)
                        logger.info(f"Looked up puuid for {game_name}#{tag_line}: {puuid}")
                    except Exception as e:
                        logger.warning(f"Failed to look up puuid for {game_name}#{tag_line}: {e}")
                
                player = Player(
                    game_name=game_name,
                    tag_line=tag_line,
                    region=region,
                    puuid=puuid
                )
                db.session.add(player)
                db.session.flush()
                team.players.append(player)
        
        db.session.commit()
        return jsonify(team.to_dict()), 201
    
    @app.route('/api/draft/sessions')
    def api_draft_sessions():
        """Get all draft sessions."""
        sessions = DraftSession.query.order_by(DraftSession.created_at.desc()).all()
        return jsonify([session.to_dict() for session in sessions])
    
    @app.route('/api/draft/sessions/<int:session_id>')
    def api_draft_session(session_id):
        """Get draft session details."""
        session = DraftSession.query.get_or_404(session_id)
        return jsonify(session.to_dict())
    
    @app.route('/api/champions')
    def api_champions():
        """Get all champions."""
        champions = get_all_champions()
        return jsonify(champions)
    
    @app.route('/api/champions/<int:champion_id>')
    def api_champion(champion_id):
        """Get champion by ID."""
        champion = get_champion_by_id(champion_id)
        if champion:
            return jsonify(champion)
        return jsonify({'error': 'Champion not found'}), 404
    
    @app.route('/api/stats/leaderboards')
    def api_leaderboards():
        """Get leaderboard stats."""
        stats_calculator = StatsCalculator()
        leaderboards = stats_calculator.get_leaderboards()
        return jsonify(leaderboards)
    
    @app.route('/api/matches/recent')
    def api_recent_matches():
        """Get recent matches."""
        matches = Match.query.order_by(Match.game_creation.desc()).limit(20).all()
        return jsonify([match.to_dict() for match in matches])
    
    @app.route('/api/teams/<int:team_id>/collect', methods=['POST'])
    def api_collect_team_matches(team_id):
        """Collect matches for a specific team."""
        team = Team.query.get_or_404(team_id)
        riot_client = get_riot_client()
        
        if not riot_client:
            flash('Riot API key not configured', 'error')
            return redirect(url_for('team_detail', team_id=team_id))
        
        # Collect matches for all players on the team
        for player in team.players:
            try:
                collector = MatchCollector(riot_client)
                collector.collect_player_matches(player, count=20)
            except Exception as e:
                logger.warning(f"Failed to collect matches for {player.display_name}: {e}")
        
        flash(f'Match collection initiated for {team.name}', 'success')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # ==================== INHOUSE STATS ROUTES ====================
    
    @app.route('/inhouse-stats')
    def inhouse_stats():
        """Inhouse stats dashboard page."""
        # Get recent matches for display
        recent_matches = InhouseMatch.query.order_by(InhouseMatch.game_date.desc()).limit(10).all()
        # Get player count
        player_count = db.session.query(InhouseParticipant.summoner_name).distinct().count()
        # Get total matches
        total_matches = InhouseMatch.query.count()
        # Get game nights (unique dates)
        game_nights = db.session.query(db.func.count(db.func.distinct(db.func.date(InhouseMatch.game_date)))).scalar()
        
        return render_template('inhouse_stats.html', 
                             recent_matches=recent_matches,
                             player_count=player_count,
                             total_matches=total_matches,
                             game_nights=game_nights or 0)
    
    @app.route('/api/inhouse/leaderboard')
    def api_inhouse_leaderboard():
        """Get inhouse stats leaderboard."""
        from sqlalchemy import func
        
        # Get query parameters
        stat = request.args.get('stat', 'kda')
        min_games = int(request.args.get('min_games', 3))
        
        # Validate stat
        valid_stats = ['kda', 'kills', 'deaths', 'assists', 'cs', 'gold_earned', 
                      'vision_score', 'wards_placed', 'damage_per_min', 'win_rate']
        if stat not in valid_stats:
            stat = 'kda'
        
        # Build query
        if stat == 'win_rate':
            # Special case for win rate
            player_stats = db.session.query(
                InhouseParticipant.summoner_name,
                InhouseParticipant.tag,
                func.count(InhouseParticipant.id).label('games'),
                func.sum(db.case((InhouseParticipant.win == True, 1), else_=0)).label('wins'),
                func.avg(InhouseParticipant.kda).label('kda'),
                func.avg(InhouseParticipant.cs_per_min).label('cs_per_min'),
                func.avg(InhouseParticipant.gold_per_min).label('gold_per_min'),
                func.avg(InhouseParticipant.vision_score).label('vision_score')
            ).group_by(
                InhouseParticipant.summoner_name,
                InhouseParticipant.tag
            ).having(
                func.count(InhouseParticipant.id) >= min_games
            ).all()
            
            results = []
            for row in player_stats:
                win_rate = (row.wins / row.games * 100) if row.games > 0 else 0
                results.append({
                    'summoner_name': row.summoner_name,
                    'tag': row.tag,
                    'games': row.games,
                    'wins': row.wins,
                    'losses': row.games - row.wins,
                    'win_rate': round(win_rate, 1),
                    'kda': round(row.kda or 0, 2),
                    'cs_per_min': round(row.cs_per_min or 0, 1),
                    'gold_per_min': round(row.gold_per_min or 0, 0),
                    'vision_score': round(row.vision_score or 0, 1)
                })
            
            results.sort(key=lambda x: x['win_rate'], reverse=True)
        else:
            # Regular stats
            stat_col = getattr(InhouseParticipant, stat, InhouseParticipant.kda)
            
            player_stats = db.session.query(
                InhouseParticipant.summoner_name,
                InhouseParticipant.tag,
                func.count(InhouseParticipant.id).label('games'),
                func.avg(stat_col).label('stat_avg'),
                func.avg(InhouseParticipant.kda).label('kda'),
                func.sum(db.case((InhouseParticipant.win == True, 1), else_=0)).label('wins')
            ).group_by(
                InhouseParticipant.summoner_name,
                InhouseParticipant.tag
            ).having(
                func.count(InhouseParticipant.id) >= min_games
            ).all()
            
            results = []
            for row in player_stats:
                results.append({
                    'summoner_name': row.summoner_name,
                    'tag': row.tag,
                    'games': row.games,
                    'wins': row.wins,
                    'losses': row.games - row.wins,
                    'win_rate': round(row.wins / row.games * 100, 1) if row.games > 0 else 0,
                    'kda': round(row.kda or 0, 2),
                    stat: round(row.stat_avg or 0, 2)
                })
            
            results.sort(key=lambda x: x.get(stat, 0), reverse=True)
        
        return jsonify(results)
    
    @app.route('/api/inhouse/matches')
    def api_inhouse_matches():
        """Get all inhouse matches."""
        matches = InhouseMatch.query.order_by(InhouseMatch.game_date.desc()).all()
        return jsonify([{
            'id': m.id,
            'match_id': m.match_id,
            'game_date': m.game_date.isoformat() if m.game_date else None,
            'game_duration_min': m.game_duration_min,
            'queue_id': m.queue_id,
            'participant_count': m.participants.count()
        } for m in matches])
    
    @app.route('/api/inhouse/participants/<match_id>')
    def api_inhouse_participants(match_id):
        """Get participants for a specific match."""
        match = InhouseMatch.query.get_or_404(match_id)
        participants = InhouseParticipant.query.filter_by(match_id=match.id).all()
        return jsonify([p.to_dict() for p in participants])
    
    @app.route('/api/inhouse/champions')
    def api_inhouse_champions():
        """Get champion stats."""
        from sqlalchemy import func
        
        champ_stats = db.session.query(
            InhouseParticipant.champion,
            func.count(InhouseParticipant.id).label('games'),
            func.sum(db.case((InhouseParticipant.win == True, 1), else_=0)).label('wins'),
            func.avg(InhouseParticipant.kda).label('kda')
        ).group_by(
            InhouseParticipant.champion
        ).order_by(
            func.count(InhouseParticipant.id).desc()
        ).limit(20).all()
        
        results = []
        for row in champ_stats:
            wr = (row.wins / row.games * 100) if row.games > 0 else 0
            results.append({
                'champion': row.champion,
                'games': row.games,
                'wins': row.wins,
                'losses': row.games - row.wins,
                'win_rate': round(wr, 1),
                'kda': round(row.kda or 0, 2)
            })
        
        return jsonify(results)
    
    @app.route('/debug/env')
    def debug_env():
        """Debug route to check environment variables."""
        return jsonify({
            "riot_key_set": bool(os.getenv("RIOT_API_KEY")),
            "riot_key_preview": os.getenv("RIOT_API_KEY", "")[:10] + "..." if os.getenv("RIOT_API_KEY") else "NOT SET",
            "database_url_set": bool(os.getenv("DATABASE_URL")),
            "secret_key_set": bool(os.getenv("SECRET_KEY")),
            "all_env_keys": list(os.environ.keys())
        })
    
    @app.route('/debug/db')
    def debug_db():
        """Debug route to check database status."""
        try:
            # Check table counts
            team_count = Team.query.count()
            player_count = Player.query.count()
            match_count = Match.query.count()
            
            # Get recent teams
            recent_teams = Team.query.order_by(Team.created_at.desc()).limit(5).all()
            
            # Get recent players
            recent_players = Player.query.order_by(Player.created_at.desc()).limit(10).all()
            
            return jsonify({
                "status": "connected",
                "database_uri": str(SQLALCHEMY_DATABASE_URI)[:50] + "...",
                "tables": {
                    "teams": team_count,
                    "players": player_count,
                    "matches": match_count
                },
                "recent_teams": [t.to_dict() for t in recent_teams],
                "recent_players": [p.to_dict() for p in recent_players]
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e)
            })
    
    # ==================== ERROR HANDLERS ====================
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return render_template('error.html', error='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal error: {error}")
        return render_template('error.html', error='Internal server error'), 500
    
    return app

# =================== Entry Point for Railway ===================
app = create_app()
start_scheduler(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "False") == "True")
