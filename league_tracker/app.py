"""
League of Legends League Tracker - Flask Application
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import sys
import os
import atexit

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import SECRET_KEY, DEBUG, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, \
                   RIOT_API_KEY, validate_api_key, AUTO_COLLECT_ENABLED, AUTO_COLLECT_INTERVAL
from src.database import db, Team, Player, Match, MatchParticipant, Admin, team_players, TournamentCode, DraftSession, DraftGame, DraftStep
from src.api.riot_client import RiotClient, RiotAPIError
from src.api.match_collector import MatchCollector, run_collect
from src.utils.stats_calculator import StatsCalculator
from src.utils.champions import get_all_champions, get_champion_by_id, get_champion_name, CHAMPIONS
from src.utils.draft_logic import DraftSessionManager, DraftModeValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Global scheduler instance
scheduler = None


def admin_required(f):
    """Decorator to require admin login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def start_scheduler(app):
    """Start the background scheduler for match collection."""
    global scheduler
    
    # Check if we're in debug mode with reloader (avoids double-start)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # This is the child process after reload, scheduler was already started
        return None
    
    if scheduler is not None:
        return scheduler
    
    # Check if auto-collect is enabled
    if not AUTO_COLLECT_ENABLED:
        logger.info("Auto-collect is disabled (AUTO_COLLECT_ENABLED=False)")
        return None
    
    scheduler = BackgroundScheduler()
    
    # Schedule match collection based on config interval
    scheduler.add_job(
        func=lambda: run_collect(app),
        trigger='interval',
        minutes=AUTO_COLLECT_INTERVAL,
        id='match_collection',
        name='Collect match data for all players'
    )
    
    scheduler.start()
    logger.info(f"Background scheduler started (interval: {AUTO_COLLECT_INTERVAL} minutes)")
    
    # Register shutdown only if we're the main process
    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler and scheduler.running else None)
    
    return scheduler


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    
    # Initialize database
    db.init_app(app)
    
    # Create tables and default admin
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        if not Admin.query.first():
            admin = Admin(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin user (username: admin, password: admin123)")
    
    # Store riot_client factory in app config for lazy initialization
    app.config['RIOT_CLIENT_FACTORY'] = lambda: RiotClient()
    app.config['RIOT_CLIENT'] = None  # Will be created on first use
    
    def get_riot_client():
        """Get or create the Riot API client."""
        if app.config.get('RIOT_CLIENT') is None:
            try:
                app.config['RIOT_CLIENT'] = app.config['RIOT_CLIENT_FACTORY']()
            except RiotAPIError:
                logger.warning("Riot API key not configured. Some features will be limited.")
                app.config['RIOT_CLIENT'] = False  # Mark as unavailable
        return app.config['RIOT_CLIENT'] if app.config['RIOT_CLIENT'] else None
    
    app.get_riot_client = get_riot_client
    
    # === Routes ===
    
    @app.route('/')
    def index():
        """Home page."""
        teams = Team.query.order_by(Team.created_at.desc()).limit(5).all()
        total_teams = Team.query.count()
        # Count only players that are on at least one team
        total_players = db.session.query(db.func.count(db.distinct(team_players.c.player_id))).scalar() or 0
        total_matches = Match.query.count()
        
        return render_template('index.html',
                             teams=teams,
                             total_teams=total_teams,
                             total_players=total_players,
                             total_matches=total_matches)
    
    @app.route('/teams')
    def teams_list():
        """List all teams."""
        teams = Team.query.order_by(Team.name).all()
        return render_template('teams.html', teams=teams)
    
    @app.route('/teams/<int:team_id>')
    def team_detail(team_id):
        """Show team details."""
        team = Team.query.get_or_404(team_id)
        
        # Get team stats
        stats = StatsCalculator.get_team_stats(team_id)
        
        # Get recent matches
        recent_matches = StatsCalculator.get_recent_matches(team_id, limit=10)
        
        return render_template('team_detail.html', 
                             team=team, 
                             stats=stats,
                             recent_matches=recent_matches,
                             format_duration=StatsCalculator.format_duration,
                             format_timestamp=StatsCalculator.format_timestamp)
    
    @app.route('/matches/<match_id>')
    def match_detail(match_id):
        """Show match details."""
        match = Match.query.filter_by(match_id=match_id).first_or_404()
        participants = MatchParticipant.query.filter_by(match_id=match.id).all()
        
        # Get player names for participants
        players = {}
        for p in participants:
            player = Player.query.filter_by(puuid=p.puuid).first()
            if player:
                players[p.puuid] = player
        
        return render_template('match_detail.html',
                             match=match,
                             participants=participants,
                             players=players,
                             format_duration=StatsCalculator.format_duration,
                             format_timestamp=StatsCalculator.format_timestamp)
    
    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        """Team registration page."""
        if request.method == 'POST':
            team_name = request.form.get('team_name')
            
            # Get player data from form
            player_names = request.form.getlist('player_name[]')
            player_tags = request.form.getlist('player_tag[]')
            player_regions = request.form.getlist('player_region[]')
            
            if not team_name or not player_names:
                flash('Team name and at least one player are required.', 'error')
                return render_template('signup.html', riot_client=app.get_riot_client())
            
            # Check if team name exists
            if Team.query.filter_by(name=team_name).first():
                flash('A team with this name already exists.', 'error')
                return render_template('signup.html', riot_client=app.get_riot_client())
            
            # Create team
            team = Team(name=team_name)
            db.session.add(team)
            db.session.flush()  # Get team ID
            
            # Create players and add to team
            for name, tag, region in zip(player_names, player_tags, player_regions):
                if not name or not tag:
                    continue
                
                # Get PUUID from Riot API
                puuid = None
                riot_client = app.get_riot_client()
                if riot_client:
                    try:
                        puuid = riot_client.get_puuid_from_riot_id(name, tag, region)
                    except Exception as e:
                        logger.error(f"Error getting PUUID for {name}#{tag}: {e}")
                
                # Check if player already exists
                player = Player.query.filter_by(
                    game_name=name, tag_line=tag
                ).first()
                
                if not player:
                    player = Player(
                        puuid=puuid,  # Will be NULL if Riot API fails
                        game_name=name,
                        tag_line=tag,
                        region=region or 'na1'
                    )
                    db.session.add(player)
                else:
                    # Update PUUID if we got one
                    if puuid and not player.puuid:
                        player.puuid = puuid
                
                # Add player to team
                team.players.append(player)
            
            db.session.commit()
            flash(f'Team "{team_name}" has been registered successfully!', 'success')
            return redirect(url_for('team_detail', team_id=team.id))
        
        return render_template('signup.html', riot_client=app.get_riot_client())
    
    @app.route('/leaderboards')
    def leaderboards():
        """Show team and player leaderboards."""
        # Team rankings by wins
        teams = Team.query.all()
        team_rankings = []
        
        for team in teams:
            stats = StatsCalculator.get_team_stats(team.id)
            team_rankings.append({
                'team': team,
                'wins': stats.get('wins', 0),
                'losses': stats.get('losses', 0),
                'games_played': stats.get('total_games', 0),
                'win_rate': stats.get('win_rate', 0),
                'avg_kda': stats.get('avg_kda', 0),
            })
        
        team_rankings.sort(key=lambda x: x['wins'], reverse=True)
        
        return render_template('leaderboards.html', team_rankings=team_rankings)
    
    @app.route('/league/matches')
    def league_matches():
        """Show all league tournament match history."""
        limit = request.args.get('limit', 50, type=int)
        queue_type = request.args.get('type', None)
        league_matches = StatsCalculator.get_league_matches(limit=limit, queue_type=queue_type)
        
        return render_template('league_matches.html',
                             matches=league_matches,
                             queue_type=queue_type,
                             format_duration=StatsCalculator.format_duration,
                             format_timestamp=StatsCalculator.format_timestamp)
    
    @app.route('/league/players/<puuid>/history')
    def player_league_history(puuid):
        """Show league tournament match history for a specific player."""
        player = Player.query.filter_by(puuid=puuid).first()
        if not player:
            return render_template('error.html', error={'message': 'Player not found'}), 404
        
        limit = request.args.get('limit', 20, type=int)
        queue_type = request.args.get('type', None)
        history = StatsCalculator.get_player_league_history(puuid, limit=limit, queue_type=queue_type)
        
        return render_template('player_history.html',
                             player=player,
                             history=history,
                             queue_type=queue_type,
                             format_duration=StatsCalculator.format_duration,
                             format_timestamp=StatsCalculator.format_timestamp)
    
    # === Admin Routes ===
    
    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        """Admin login page."""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            admin = Admin.query.filter_by(username=username).first()
            
            if admin and admin.check_password(password):
                session['admin_id'] = admin.id
                flash('Successfully logged in as admin!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        
        return render_template('admin_login.html')
    
    @app.route('/admin/logout')
    def admin_logout():
        """Logout admin user."""
        session.pop('admin_id', None)
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))
    
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        """Admin dashboard with all teams."""
        teams = Team.query.order_by(Team.name).all()
        return render_template('admin_dashboard.html', teams=teams)
    
    @app.route('/admin/team/<int:team_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_team(team_id):
        """Edit team name."""
        team = Team.query.get_or_404(team_id)
        
        if request.method == 'POST':
            new_name = request.form.get('team_name')
            
            if not new_name:
                flash('Team name is required.', 'error')
            elif Team.query.filter_by(name=new_name).first() and new_name != team.name:
                flash('A team with this name already exists.', 'error')
            else:
                team.name = new_name
                db.session.commit()
                flash(f'Team "{team.name}" has been updated.', 'success')
                return redirect(url_for('admin_dashboard'))
        
        return render_template('admin_edit_team.html', team=team)
    
    @app.route('/admin/team/<int:team_id>/players', methods=['GET', 'POST'])
    @admin_required
    def admin_manage_players(team_id):
        """Add or remove players from a team."""
        team = Team.query.get_or_404(team_id)
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add':
                # Add existing player to team
                player_id = request.form.get('player_id')
                if player_id:
                    player = Player.query.get(player_id)
                    if player and player not in team.players:
                        team.players.append(player)
                        db.session.commit()
                        flash(f'Player {player.game_name}#{player.tag_line} added to team.', 'success')
            
            elif action == 'remove':
                # Remove player from team
                player_id = request.form.get('player_id')
                if player_id:
                    player = Player.query.get(player_id)
                    if player and player in team.players:
                        team.players.remove(player)
                        db.session.commit()
                        flash(f'Player {player.game_name}#{player.tag_line} removed from team.', 'success')
            
            elif action == 'create':
                # Create new player and add to team
                game_name = request.form.get('game_name')
                tag_line = request.form.get('tag_line')
                region = request.form.get('region', 'na1')
                
                if game_name and tag_line:
                    # Check if player exists
                    existing = Player.query.filter_by(game_name=game_name, tag_line=tag_line).first()
                    if existing:
                        if existing not in team.players:
                            team.players.append(existing)
                            db.session.commit()
                            flash(f'Player {existing.game_name}#{existing.tag_line} added to team.', 'success')
                        else:
                            flash('Player is already on this team.', 'error')
                    else:
                        # Get PUUID if API is available
                        puuid = None
                        riot_client = app.get_riot_client()
                        if riot_client:
                            try:
                                puuid = riot_client.get_puuid_from_riot_id(game_name, tag_line, region)
                            except:
                                pass
                        
                        player = Player(
                            puuid=puuid,
                            game_name=game_name,
                            tag_line=tag_line,
                            region=region
                        )
                        db.session.add(player)
                        team.players.append(player)
                        db.session.commit()
                        flash(f'Player {game_name}#{tag_line} created and added to team.', 'success')
                else:
                    flash('Game name and tag line are required.', 'error')
        
        # Get all players not on this team for the add dropdown
        all_players = Player.query.all()
        team_player_ids = [p.id for p in team.players]
        available_players = [p for p in all_players if p.id not in team_player_ids]
        
        return render_template('admin_manage_players.html', 
                             team=team, 
                             available_players=available_players)
    
    @app.route('/admin/team/<int:team_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_team(team_id):
        """Delete a team and its associated players (if no longer on any team)."""
        team = Team.query.get_or_404(team_id)
        team_name = team.name
        
        # Get player IDs that are only on this team (not on any other team)
        players_to_delete = []
        for player in team.players:
            if player.teams.count() == 1:  # Only on this team
                players_to_delete.append(player)
        
        # Delete the team first (this removes associations)
        db.session.delete(team)
        
        # Delete players that are no longer on any team
        for player in players_to_delete:
            db.session.delete(player)
        
        db.session.commit()
        
        flash(f'Team "{team_name}" has been deleted.', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # === Tournament Code Routes ===
    
    @app.route('/admin/tournament-codes', methods=['GET'])
    @admin_required
    def admin_tournament_codes():
        """List all tournament codes."""
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
        
        if not code:
            flash('Tournament code is required.', 'error')
            return redirect(url_for('admin_tournament_codes'))
        
        # Check if code already exists
        existing = TournamentCode.query.filter_by(code=code).first()
        if existing:
            flash('This tournament code already exists.', 'error')
            return redirect(url_for('admin_tournament_codes'))
        
        tournament_code = TournamentCode(
            code=code,
            tournament_name=tournament_name,
            team_id=int(team_id) if team_id else None
        )
        db.session.add(tournament_code)
        db.session.commit()
        
        flash(f'Tournament code added successfully.', 'success')
        return redirect(url_for('admin_tournament_codes'))
    
    @app.route('/admin/tournament-codes/<int:code_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_tournament_code(code_id):
        """Delete a tournament code."""
        code = TournamentCode.query.get_or_404(code_id)
        db.session.delete(code)
        db.session.commit()
        
        flash('Tournament code deleted.', 'success')
        return redirect(url_for('admin_tournament_codes'))
    
    # === Admin Draft Management Routes ===
    
    @app.route('/admin/drafts')
    @admin_required
    def admin_drafts():
        """List all draft sessions for admin management."""
        sessions = DraftSession.query.order_by(DraftSession.created_at.desc()).all()
        return render_template('admin_drafts.html', sessions=sessions)
    
    @app.route('/admin/drafts/<int:session_id>')
    @admin_required
    def admin_draft_detail(session_id):
        """View draft session details for admin."""
        session = DraftSession.query.get_or_404(session_id)
        history = DraftSessionManager.get_series_history(session_id)
        teams = Team.query.all()
        # Convert CHAMPIONS dict for template lookup
        champion_names = {k: v for k, v in CHAMPIONS.items()}
        return render_template('admin_draft_detail.html', draft_session=session, history=history, teams=teams, champion_names=champion_names)
    
    @app.route('/admin/drafts/<int:session_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_draft(session_id):
        """Edit draft session settings."""
        session = DraftSession.query.get_or_404(session_id)
        teams = Team.query.all()
        
        if request.method == 'POST':
            name = request.form.get('name')
            draft_mode = request.form.get('draft_mode')
            team_blue_id = request.form.get('team_blue_id')
            team_red_id = request.form.get('team_red_id')
            bans_per_team = request.form.get('bans_per_team', 5, type=int)
            picks_per_team = request.form.get('picks_per_team', 5, type=int)
            
            if not name or not team_blue_id or not team_red_id:
                flash('Name and teams are required.', 'error')
            elif team_blue_id == team_red_id:
                flash('Teams must be different.', 'error')
            else:
                session.name = name
                session.draft_mode = draft_mode
                session.team_blue_id = int(team_blue_id)
                session.team_red_id = int(team_red_id)
                session.bans_per_team = bans_per_team
                session.picks_per_team = picks_per_team
                db.session.commit()
                flash(f'Draft session "{name}" updated successfully!', 'success')
                return redirect(url_for('admin_drafts'))
        
        return render_template('admin_edit_draft.html', draft_session=session, teams=teams)
    
    @app.route('/admin/drafts/<int:session_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_draft(session_id):
        """Delete a draft session and all associated games/steps."""
        session = DraftSession.query.get_or_404(session_id)
        session_name = session.name
        
        # Delete all draft steps, games, and the session
        DraftStep.query.filter_by(session_id=session_id).delete()
        DraftGame.query.filter_by(session_id=session_id).delete()
        db.session.delete(session)
        db.session.commit()
        
        flash(f'Draft session "{session_name}" has been deleted.', 'success')
        return redirect(url_for('admin_drafts'))
    
    @app.route('/admin/drafts/<int:session_id>/reset/<int:game_number>', methods=['POST'])
    @admin_required
    def admin_reset_game(session_id, game_number):
        """Reset a specific game in a draft session."""
        try:
            game = DraftSessionManager.reset_game(session_id, game_number)
            flash(f'Game {game_number} has been reset.', 'success')
        except Exception as e:
            flash(f'Error resetting game: {str(e)}', 'error')
        
        return redirect(url_for('admin_draft_detail', session_id=session_id))
    
    @app.route('/admin/drafts/<int:session_id>/toggle-active', methods=['POST'])
    @admin_required
    def admin_toggle_draft_active(session_id):
        """Toggle the active state of a draft session."""
        session = DraftSession.query.get_or_404(session_id)
        
        session.is_active = not session.is_active
        if not session.is_active:
            from datetime import datetime
            session.completed_at = datetime.utcnow()
        else:
            session.completed_at = None
        
        db.session.commit()
        
        status = 'activated' if session.is_active else 'completed'
        flash(f'Draft session has been {status}.', 'success')
        
        return redirect(url_for('admin_draft_detail', session_id=session_id))
    
    # === API Routes ====
    
    @app.route('/api/teams', methods=['GET'])
    def api_teams():
        """Get all teams as JSON."""
        teams = Team.query.all()
        return jsonify([t.to_dict() for t in teams])
    
    @app.route('/api/teams/<int:team_id>', methods=['GET'])
    def api_team_detail(team_id):
        """Get team details as JSON."""
        team = Team.query.get_or_404(team_id)
        stats = StatsCalculator.get_team_stats(team_id)
        return jsonify({
            'team': team.to_dict(),
            'players': [p.to_dict() for p in team.players],
            'stats': stats
        })
    
    @app.route('/api/teams/register', methods=['POST'])
    def api_register_team():
        """Register a team via API."""
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        team_name = data.get('team_name')
        players = data.get('players', [])
        
        if not team_name or not players:
            return jsonify({'error': 'Team name and players are required'}), 400
        
        if Team.query.filter_by(name=team_name).first():
            return jsonify({'error': 'Team name already exists'}), 400
        
        team = Team(name=team_name)
        db.session.add(team)
        db.session.flush()
        
        for player_data in players:
            game_name = player_data.get('game_name')
            tag_line = player_data.get('tag_line')
            region = player_data.get('region', 'na1')
            
            if not game_name or not tag_line:
                continue
            
            # Get PUUID
            puuid = None
            riot_client = app.get_riot_client()
            if riot_client:
                try:
                    puuid = riot_client.get_puuid_from_riot_id(game_name, tag_line, region)
                except:
                    pass
            
            player = Player.query.filter_by(
                game_name=game_name, tag_line=tag_line
            ).first()
            
            if not player:
                player = Player(
                    puuid=puuid,  # Will be NULL if Riot API fails
                    game_name=game_name,
                    tag_line=tag_line,
                    region=region
                )
                db.session.add(player)
            
            team.players.append(player)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Team registered successfully',
            'team': team.to_dict()
        }), 201
    
    @app.route('/api/players/<puuid>/matches', methods=['GET'])
    def api_player_matches(puuid):
        """Get match history for a player."""
        participants = MatchParticipant.query.filter_by(puuid=puuid).all()
        return jsonify([p.to_dict() for p in participants])
    
    @app.route('/api/players/<puuid>/stats', methods=['GET'])
    def api_player_stats(puuid):
        """Get aggregated stats for a player."""
        stats = StatsCalculator.get_player_stats(puuid)
        return jsonify(stats)
    
    @app.route('/api/collect', methods=['POST'])
    def api_collect_matches():
        """Trigger match collection for all players."""
        if not app.get_riot_client():
            return jsonify({'error': 'Riot API not configured'}), 400
        
        try:
            stats = run_collect(app)
            return jsonify({
                'message': 'Collection complete',
                'stats': stats
            })
        except Exception as e:
            logger.error(f"Collection error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/collect/team/<int:team_id>', methods=['POST'])
    def api_collect_team_matches(team_id):
        """Trigger match collection for a specific team."""
        if not app.get_riot_client():
            return jsonify({'error': 'Riot API not configured'}), 400
        
        team = Team.query.get_or_404(team_id)
        
        try:
            collector = MatchCollector(app)
            new_matches = 0
            for player in team.players:
                matches = collector.collect_player_matches(player, count=10)
                new_matches += len(matches)
            
            return jsonify({
                'message': f'Collected {new_matches} new matches',
                'team': team.name,
                'new_matches': new_matches
            })
        except Exception as e:
            logger.error(f"Collection error: {e}")
            return jsonify({'error': str(e)}), 500
    
    # ==================== DRAFT API ROUTES ====================
    
    @app.route('/draft')
    def draft_index():
        """Draft tool landing page."""
        teams = Team.query.all()
        active_sessions = DraftSession.query.filter_by(is_active=True).order_by(DraftSession.created_at.desc()).all()
        closed_sessions = DraftSession.query.filter_by(is_active=False).order_by(DraftSession.completed_at.desc()).limit(10).all()
        
        # Get game links for active sessions
        session_games = {}
        for session in active_sessions:
            game = DraftGame.query.filter_by(
                session_id=session.id,
                game_number=session.current_game_number
            ).first()
            if game:
                session_games[session.id] = game
        
        return render_template('draft_index.html', teams=teams, active_sessions=active_sessions, 
                               closed_sessions=closed_sessions, session_games=session_games)
    
    @app.route('/draft/create', methods=['GET', 'POST'])
    def draft_create():
        """Create a new draft session."""
        teams = Team.query.all()
        
        if request.method == 'POST':
            name = request.form.get('name')
            draft_mode = request.form.get('draft_mode')
            team_blue_id = request.form.get('team_blue_id')
            team_red_id = request.form.get('team_red_id')
            bans_per_team = request.form.get('bans_per_team', 5, type=int)
            
            if not name or not draft_mode or not team_blue_id or not team_red_id:
                flash('All fields are required.', 'error')
                return render_template('draft_create.html', teams=teams)
            
            if team_blue_id == team_red_id:
                flash('Teams must be different.', 'error')
                return render_template('draft_create.html', teams=teams)
            
            try:
                session = DraftSessionManager.create_session(
                    name=name,
                    draft_mode=draft_mode,
                    team_blue_id=int(team_blue_id),
                    team_red_id=int(team_red_id),
                    bans_per_team=bans_per_team
                )
                flash(f'Draft session "{name}" created successfully!', 'success')
                return redirect(url_for('draft_view', session_id=session.id))
            except Exception as e:
                flash(f'Error creating draft session: {str(e)}', 'error')
        
        return render_template('draft_create.html', teams=teams)
    
    @app.route('/draft/<int:session_id>')
    def draft_view(session_id):
        """View and interact with a draft session."""
        draft_session = DraftSession.query.get_or_404(session_id)
        teams = Team.query.all()
        
        state = DraftSessionManager.get_session_state(session_id)
        champions = get_all_champions()
        
        return render_template('draft_view.html', 
                             draft_session=draft_session, 
                             state=state,
                             champions=champions,
                             teams=teams)
    
    @app.route('/draft/<int:session_id>/history')
    def draft_history(session_id):
        """View the complete history of a draft series."""
        session = DraftSession.query.get_or_404(session_id)
        history = DraftSessionManager.get_series_history(session_id)
        
        # Convert CHAMPIONS dict to use integer keys for proper lookup
        champion_names = {k: v for k, v in CHAMPIONS.items()}
        
        return render_template('draft_history.html', session=session, history=history, champion_names=champion_names)
    
    # Draft API endpoints
    
    @app.route('/api/draft/sessions', methods=['GET'])
    def api_draft_sessions():
        """Get all draft sessions."""
        sessions = DraftSession.query.order_by(DraftSession.created_at.desc()).all()
        return jsonify([s.to_dict() for s in sessions])
    
    @app.route('/api/draft/sessions/<int:session_id>', methods=['GET'])
    def api_draft_session(session_id):
        """Get a specific draft session state."""
        state = DraftSessionManager.get_session_state(session_id)
        if not state:
            return jsonify({'error': 'Session not found'}), 404
        return jsonify(state)
    
    @app.route('/api/draft/sessions', methods=['POST'])
    def api_create_draft_session():
        """Create a new draft session via API."""
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name')
        draft_mode = data.get('draft_mode')
        team_blue_id = data.get('team_blue_id')
        team_red_id = data.get('team_red_id')
        bans_per_team = data.get('bans_per_team', 5)
        
        if not name or not draft_mode or not team_blue_id or not team_red_id:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if team_blue_id == team_red_id:
            return jsonify({'error': 'Teams must be different'}), 400
        
        try:
            session = DraftSessionManager.create_session(
                name=name,
                draft_mode=draft_mode,
                team_blue_id=team_blue_id,
                team_red_id=team_red_id,
                bans_per_team=bans_per_team
            )
            return jsonify({
                'message': 'Draft session created',
                'session': session.to_dict()
            }), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/draft/sessions/<int:session_id>/action', methods=['POST'])
    def api_draft_action(session_id):
        """Execute a ban or pick action."""
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        action_type = data.get('action_type')  # 'ban' or 'pick'
        champion_id = data.get('champion_id')
        team_color = data.get('team')  # 'blue' or 'red'
        player_id = data.get('player_id')
        position = data.get('position')
        
        if not action_type or not champion_id or not team_color:
            return jsonify({'error': 'Missing required fields'}), 400
        
        try:
            result = DraftSessionManager.execute_action(
                session_id=session_id,
                action_type=action_type,
                champion_id=champion_id,
                team_color=team_color,
                player_id=player_id,
                position=position
            )
            return jsonify(result)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Draft action error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/draft/sessions/<int:session_id>/reset/<int:game_number>', methods=['POST'])
    def api_reset_game(session_id, game_number):
        """Reset a game to start fresh."""
        try:
            game = DraftSessionManager.reset_game(session_id, game_number)
            return jsonify({
                'message': f'Game {game_number} reset',
                'game': game.to_dict()
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/draft/sessions/<int:session_id>/history', methods=['GET'])
    def api_draft_history(session_id):
        """Get the complete series history."""
        history = DraftSessionManager.get_series_history(session_id)
        return jsonify(history)
    
    @app.route('/api/draft/sessions/<int:session_id>/game/<int:game_number>/ready', methods=['POST'])
    def api_set_team_ready(session_id, game_number):
        """Set a team as ready for the match to begin."""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        team_color = data.get('team')
        if not team_color or team_color not in ['blue', 'red']:
            return jsonify({'error': 'Valid team color (blue or red) is required'}), 400
        
        try:
            game = DraftSessionManager.set_team_ready(session_id, game_number, team_color)
            return jsonify({
                'message': f'{team_color.capitalize()} team is ready',
                'game': game.to_dict()
            })
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error setting team ready: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/draft/sessions/<int:session_id>/game/<int:game_number>/links', methods=['GET'])
    def api_get_game_links(session_id, game_number):
        """Get the game links for blue side, red side, and spectator."""
        game = DraftGame.query.filter_by(
            session_id=session_id,
            game_number=game_number
        ).first()
        
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        return jsonify({
            'game_number': game.game_number,
            'blue_side_link': game.blue_side_link,
            'red_side_link': game.red_side_link,
            'spectator_link': game.spectator_link,
            'blue_ready': game.blue_ready,
            'red_ready': game.red_ready,
            'match_started': game.match_started
        })
    
    @app.route('/api/draft/available/<int:session_id>', methods=['GET'])
    def api_available_champions(session_id):
        """Get available champions for current draft state."""
        session = DraftSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        game = DraftGame.query.filter_by(
            session_id=session_id,
            game_number=session.current_game_number
        ).first()
        
        player_id = request.args.get('player_id', type=int)
        position = request.args.get('position')
        
        validator = DraftModeValidator(session, game, session.current_team_turn)
        champions = validator.get_available_champions(player_id, position)
        
        return jsonify(champions)
    
    @app.route('/api/champions', methods=['GET'])
    def api_champions():
        """Get all champions."""
        champions = get_all_champions()
        return jsonify(champions)
    
    @app.route('/api/champions/<int:champion_id>', methods=['GET'])
    def api_champion(champion_id):
        """Get a specific champion."""
        champion = get_champion_by_id(champion_id)
        if not champion['name'].startswith('Unknown'):
            return jsonify(champion)
        return jsonify({'error': 'Champion not found'}), 404
    
    # === Draft Game Link Routes ===
    
    @app.route('/game/<int:session_id>/<int:game_number>/<team_color>/<token>')
    def draft_game_link(session_id, game_number, team_color, token):
        """Handle draft game links for blue side, red side, and spectator."""
        # Validate team color
        if team_color not in ['blue', 'red', 'spectator']:
            return render_template('error.html', error={'message': 'Invalid team color'}), 404
        
        # Get the draft session
        session = DraftSession.query.get_or_404(session_id)
        
        # Get the game
        game = DraftGame.query.filter_by(
            session_id=session_id,
            game_number=game_number
        ).first_or_404()
        
        # Validate the token
        valid_link = None
        if team_color == 'blue' and game.blue_side_link and token in game.blue_side_link:
            valid_link = game.blue_side_link
        elif team_color == 'red' and game.red_side_link and token in game.red_side_link:
            valid_link = game.red_side_link
        elif team_color == 'spectator' and game.spectator_link and token in game.spectator_link:
            valid_link = game.spectator_link
        
        if not valid_link:
            return render_template('error.html', error={'message': 'Invalid or expired game link'}), 404
        
        # Redirect to the draft view page
        # Store the team/side selection in session or localStorage would be handled by the frontend
        return redirect(url_for('draft_view', session_id=session_id))
    
    # === Error Handlers ===
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', error=error), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', error=error), 500
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    if not validate_api_key():
        print("WARNING: No RIOT_API_KEY configured. Set it in config.py or as environment variable.")
    
    # Start background scheduler (enabled by default via AUTO_COLLECT_ENABLED config)
    start_scheduler(app)
    
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)
