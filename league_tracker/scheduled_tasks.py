from league_tracker.src.api.match_collector import run_collect
from league_tracker.app import create_app

app = create_app()
with app.app_context():
    stats = run_collect(app)
    print(f'Scheduled collection complete. Stats: {stats}')