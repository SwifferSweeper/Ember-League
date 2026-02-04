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
from league_tracker.config import SECRET_KEY, DEBUG, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, \
                   RIOT_API_KEY, validate_api_key, AUTO_COLLECT_ENABLED, AUTO_COLLECT_INTERVAL
from league_tracker.src.database import db, Team, Player, Match, MatchParticipant, Admin, team_players, TournamentCode, DraftSession, DraftGame, DraftStep
from league_tracker.src.api.riot_client import RiotClient, RiotAPIError
from league_tracker.src.api.match_collector import MatchCollector, run_collect
from league_tracker.src.utils.stats_calculator import StatsCalculator
from league_tracker.src.utils.champions import get_all_champions, get_champion_by_id, get_champion_name, CHAMPIONS
from league_tracker.src.utils.draft_logic import DraftSessionManager, DraftModeValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        return render_template('index.html')
    
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
        return render_template('match_detail.html', match=match)
    
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
                return render_template('signup.html')
            
            # Create team
            team = Team(name=team_name)
            db.session.add(team)
            db.session.flush()
            
            # Create players
            for name, tag, region in zip(player_names, player_tags, player_regions):
                if name and tag:
                    player = Player(
                        game_name=name,
                        tag_line=tag,
                        region=region
                    )
                    db.session.add(player)
                    db.session.flush()
                    team.players.append(player)
            
            db.session.commit()
            flash('Team registered successfully!', 'success')
            return redirect(url_for('teams_list'))
        
        return render_template('signup.html')
    
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
            
            if not all([name, draft_mode, team_blue_id, team_red_id]):
                flash('All fields are required', 'error')
                return render_template('draft_create.html')
            
            draft = DraftSession(
                name=name,
                draft_mode=draft_mode,
                team_blue_id=team_blue_id,
                team_red_id=team_red_id
            )
            db.session.add(draft)
            db.session.commit()
            
            flash('Draft session created!', 'success')
            return redirect(url_for('draft_view', draft_session_id=draft.id))
        
        teams = Team.query.all()
        return render_template('draft_create.html', teams=teams)
    
    @app.route('/draft/<int:draft_session_id>')
    def draft_view(draft_session_id):
        """View draft session."""
        draft = DraftSession.query.get_or_404(draft_session_id)
        return render_template('draft_view.html', draft=draft)
    
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
                player = Player(
                    game_name=player_data.get('game_name'),
                    tag_line=player_data.get('tag_line'),
                    region=player_data.get('region', 'na1')
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
