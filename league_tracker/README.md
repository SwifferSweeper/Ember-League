# League of Legends League Tracker

A web-based system for tracking League of Legends team matches and statistics.

## Features

- **Team Registration**: Teams can register with their Riot IDs
- **Automatic Match Collection**: Background scheduler fetches match data every 5 minutes
- **Player Tracking**: Automatically fetches player PUUIDs from Riot API
- **Match Collection**: Collects match data for registered players
- **Statistics**: Team and player stats (wins, losses, KDA, win rate)
- **Leaderboards**: Team rankings by wins and win rate
- **Web Interface**: Clean, responsive UI

## Installation

1. Install dependencies:
```bash
cd league_tracker
pip install -r requirements.txt
```

2. Configure your Riot API key:
   - Open `config.py`
   - Uncomment and set your API key:
   ```python
   RIOT_API_KEY = "RGAPI-your-key-here"
   ```

3. Initialize the database:
```bash
python -c "from app import app, db; db.create_all()"
```

## Running the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## Usage

1. **Register a Team**: Visit `/signup` and enter your team name and player Riot IDs
2. **View Teams**: Visit `/teams` to see all registered teams
3. **Collect Matches**: Visit a team's page and click "Collect Matches" or let the background scheduler do it
4. **Leaderboards**: Visit `/leaderboards` to see team rankings

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/teams` | GET | List all teams |
| `/api/teams/<id>` | GET | Get team details with stats |
| `/api/teams/register` | POST | Register a team |
| `/api/players/<puuid>/matches` | GET | Player match history |
| `/api/players/<puuid>/stats` | GET | Player aggregated stats |
| `/api/collect` | POST | Trigger collection for all players |
| `/api/collect/team/<id>` | POST | Trigger collection for specific team |

## Project Structure

```
league_tracker/
├── app.py                  # Flask application with scheduler
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── README.md              # This file
├── src/
│   ├── api/
│   │   ├── riot_client.py      # Riot API wrapper
│   │   └── match_collector.py  # Match fetching service
│   └── database/
│       └── models.py           # SQLAlchemy models
├── templates/
│   ├── base.html           # Base template
│   ├── index.html          # Home page
│   ├── teams.html          # Teams list
│   ├── team_detail.html    # Team profile with stats
│   ├── match_detail.html   # Match details
│   ├── signup.html         # Registration form
│   ├── leaderboards.html   # Rankings
│   └── error.html          # Error page
└── static/
    ├── style.css           # CSS styles
    └── script.js           # JavaScript
```

## Phase 2 Features Implemented

- ✅ Background scheduler (runs every 5 minutes)
- ✅ Match collection service
- ✅ Statistics calculator
- ✅ Team match history display
- ✅ Match detail page
- ✅ API endpoints for triggering collection

## Configuration

### Tournament Queue
To filter matches by a specific queue, edit `config.py`:
```python
TOURNAMENT_QUEUE_ID = 0  # Custom/tournament games
# Or use ranked queues:
# TOURNAMENT_QUEUE_ID = 420  # Ranked Solo/Duo
# TOURNAMENT_QUEUE_ID = 440  # Ranked Flex
```

### Scheduler Interval
To change how often matches are collected, edit `app.py`:
```python
scheduler.add_job(..., trigger='interval', minutes=5)  # Change 5 to your preferred minutes
```

## Next Steps

Phase 2 is complete! The system can:
- Automatically collect matches for all registered players
- Display team statistics and match history
- Trigger manual collection via API or web interface

For production deployment, consider:
- Using a production WSGI server (gunicorn)
- Using a production database (PostgreSQL)
- Deploying to a hosting platform (Render, Railway, Fly.io)
