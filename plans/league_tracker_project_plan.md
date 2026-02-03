# League of Legends League Tracker System

## Overview
A web-based system where teams can register with their Riot IDs, and the system automatically collects match data filtered by tournament queue, displaying team leaderboards and player statistics.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Web Application                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Team     │  │ Player   │  │ Match    │  │ Leaderboard      │ │
│  │ Signup   │  │ Profile  │  │ History  │  │ Display          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Background Scheduler                          │
│           (Checks for new matches every 5 minutes)              │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │ Riot API    │    │ SQLite      │    │ Statistics  │
   │ (RiotWatcher)│   │ Database    │    │ Calculator  │
   └─────────────┘    └─────────────┘    └─────────────┘
```

## Database Schema

### Teams Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Team name |
| created_at | TIMESTAMP | Registration date |
| queue_id | INTEGER | Tournament queue filter |

### Players Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| team_id | INTEGER | Foreign key to teams |
| puuid | TEXT | Riot PUUID |
| game_name | TEXT | Player name |
| tag_line | TEXT | Player tag (NA1) |
| region | TEXT | Server region |
| created_at | TIMESTAMP | Registration date |

### Team Membership Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| team_id | INTEGER | Foreign key to teams |
| player_id | INTEGER | Foreign key to players |
| is_captain | BOOLEAN | Team captain flag |

### Match Queue Config Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| queue_id | INTEGER | Riot queue ID (e.g., 0 for custom) |
| description | TEXT | Queue description |

## File Structure

```
riot_league_tracker/
├── app.py                    # Flask application entry point
├── config.py                 # Configuration
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (gitignored)
│
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── riot_client.py    # RiotWatcher wrapper
│   │   └── match_collector.py # Match fetching logic
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── models.py         # Database models
│   │
│   └── utils/
│       ├── __init__.py
│       └── stats_calculator.py # KDA, win rate calculations
│
├── templates/
│   ├── base.html             # Base template
│   ├── index.html            # Home page
│   ├── teams.html            # Team listing
│   ├── team_detail.html      # Team profile
│   ├── signup.html           # Team registration
│   └── leaderboards.html     # Rankings
│
├── static/
│   ├── style.css             # CSS styling
│   └── script.js             # JavaScript
│
├── data/
│   └── league.db             # SQLite database
│
└── .github/
    └── workflows/
        └── daily_check.yml   # GitHub Actions for backup
```

## Python Dependencies (requirements.txt)

```
flask>=2.3.0
flask-sqlalchemy>=3.0.0
riotwatcher>=3.2.5
apscheduler>=3.10.0
python-dotenv>=1.0.0
gunicorn>=21.0.0  # For production deployment
```

## Key Features

### 1. Team Registration
```python
# API endpoint example
@app.route('/api/teams/register', methods=['POST'])
def register_team():
    data = request.json
    team = Team(name=data['team_name'])
    for player in data['players']:
        player = Player(
            game_name=player['game_name'],
            tag_line=player['tag_line'],
            region=player['region']
        )
        team.players.append(player)
    db.session.add(team)
    db.session.commit()
```

### 2. Background Match Collection
```python
from apscheduler.schedulers.background import BackgroundScheduler

def collect_matches():
    """Run every 5 minutes to check for new matches."""
    for player in Player.query.all():
        match_ids = riot_client.get_match_ids(player.puuid)
        for match_id in match_ids:
            if not Match.query.filter_by(match_id=match_id).first():
                match_data = riot_client.get_match(match_id)
                # Process and store match...
```

### 3. Leaderboard Calculation
```python
def calculate_team_rankings():
    teams = Team.query.all()
    rankings = []
    for team in teams:
        stats = calculate_team_stats(team.id)
        rankings.append({
            'team': team,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_rate': stats['win_rate'],
            'avg_kda': stats['avg_kda']
        })
    return sorted(rankings, key=lambda x: x['win_rate'], reverse=True)
```

### 4. Tournament Queue Filtering
```python
# Only collect matches from specific queue
MATCH_QUEUE_ID = 0  # Custom games (tournament mode)

def collect_matches(self, player, queue_id=MATCH_QUEUE_ID):
    return self.watcher.match.matchlist_by_puuid(
        regional_route, player.puuid,
        queue=queue_id,  # Filter by tournament queue
        count=20
    )
```

## Web Pages

### 1. Home Page (`/`)
- League announcements
- Featured matches
- Top teams preview

### 2. Team Signup (`/signup`)
- Team name input
- Player list (add/remove players)
- Riot ID validation

### 3. Teams List (`/teams`)
- All registered teams
- Filter by division
- Search functionality

### 4. Team Detail (`/teams/<id>`)
- Team info
- Player roster
- Recent matches
- Team statistics

### 5. Leaderboards (`/leaderboards`)
- Team rankings (wins, win rate)
- Top players (KDA, CS, damage)
- Weekly MVPs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/teams` | GET | List all teams |
| `/api/teams/<id>` | GET | Team details |
| `/api/teams/register` | POST | Register new team |
| `/api/players/<puuid>/matches` | GET | Player match history |
| `/api/leaderboards/teams` | GET | Team rankings |
| `/api/leaderboards/players` | GET | Player rankings |
| `/api/matches/<id>` | GET | Match details |

## GitHub Actions Workflow

```yaml
# .github/workflows/daily_check.yml
name: Daily League Data Check

on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes
  workflow_dispatch:

jobs:
  collect-matches:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: python -c "from app import app, db; from src.api.match_collector import MatchCollector; mc = MatchCollector(app, db); mc.run()"
```

## Deployment Options

### Option 1: Render.com (Free Tier)
- Web service with Flask
- Scheduled tasks via Render cron
- SQLite database

### Option 2: Railway
- Full deployment
- Managed PostgreSQL
- Background workers

### Option 3: Fly.io
- Docker-based deployment
- Persistent volumes for database

## Implementation Priority

### Phase 1: Core (Week 1)
1. Set up Flask project structure
2. Create database models
3. Implement Riot API integration
4. Team registration form

### Phase 2: Data Collection (Week 2)
1. Background scheduler setup
2. Match collection logic
3. Player statistics calculation
4. Match history display

### Phase 3: UI/UX (Week 3)
1. Leaderboard pages
2. Team profile pages
3. Search and filtering
4. Mobile responsiveness

### Phase 4: Polish (Week 4)
1. Match replay links
2. Tournament bracket integration
3. Email notifications
4. Admin dashboard

## Next Steps

Would you like me to proceed with implementing this system? I can start with:

1. **Phase 1 Core Setup**: Flask app, database models, team registration
2. **Phase 2 Data Collection**: Background scheduler, match fetching, stats

Let me know which part you'd like to start with, or if you'd like any changes to this plan!
