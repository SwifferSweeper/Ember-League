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

    # ============================
    # === Paste all your routes here exactly as in your original app.py ===
    # For brevity, I'm not repeating every route, just keep your full routes block
    # ============================

    return app

# =================== Entry Point for Railway ===================
app = create_app()
start_scheduler(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "False") == "True")
