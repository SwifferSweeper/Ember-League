# League of Legends League Tracker

A comprehensive web-based system for tracking League of Legends team matches, statistics, and managing tournament drafts.

## Features

### Core Features
- **Team Registration**: Teams can register with their Riot IDs and player information
- **Automatic Match Collection**: Background scheduler fetches match data at configurable intervals
- **Player Tracking**: Automatically fetches player PUUIDs from Riot API
- **Match Statistics**: Team and player stats (wins, losses, KDA, win rate)
- **Leaderboards**: Team rankings by wins and win rate
- **Responsive Web Interface**: Clean, modern UI for all features

### Draft System
- **Multiple Draft Modes**:
  - **Normal**: Standard draft with bans and picks
  - **Fearless**: Champions used in previous games become unavailable
  - **Ironman**: Each player must pick a champion they can play (position-based)
- **Best of 3 Series**: Automatic game progression through a series
- **Unique Game Links**: Separate links for blue side, red side, and spectators
- **Team Ready System**: Both teams must mark ready before draft begins
- **Draft Timer**: Configurable timer for each draft step
- **Draft History**: Complete history of all games in a series

### Admin Features
- **Admin Dashboard**: Central hub for managing all teams and drafts
- **Team Management**: Edit team names, add/remove players, delete teams
- **Tournament Codes**: Manage tournament codes for custom games
- **Draft Management**: View, edit, reset, and delete draft sessions
- **Player Management**: Create new players and assign to teams

## Installation

### Prerequisites
- Python 3.8 or higher
- Riot API key (get one from [developer.riotgames.com](https://developer.riotgames.com/))

### Setup

1. **Clone or navigate to the project directory**:
```bash
cd league_tracker
```

2. **Create a virtual environment** (recommended):
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure your Riot API key**:
   - Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   - Edit `.env` and set your API key:
   ```
   RIOT_API_KEY=RGAPI-your-key-here
   ```
   - Or edit [`config.py`](config.py:27) directly:
   ```python
   RIOT_API_KEY = "RGAPI-your-key-here"
   ```

5. **Initialize the database**:
```bash
python -c "from app import app, db; with app.app_context(): db.create_all()"
```

## Running the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

### Default Admin Credentials
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Important**: Change the default admin password in production!

## Usage

### Team Registration

1. Visit `/signup` to register a new team
2. Enter team name and player information (Riot ID, tag line, region)
3. The system will automatically fetch PUUIDs from Riot API

### Viewing Teams and Matches

1. **Teams List**: Visit `/teams` to see all registered teams
2. **Team Details**: Click on a team to view statistics and match history
3. **Match Details**: Click on a match to see detailed participant information
4. **Leaderboards**: Visit `/leaderboards` to see team rankings

### Match Collection

Matches can be collected in two ways:

1. **Automatic**: Background scheduler collects matches at configured intervals
2. **Manual**: Use API endpoints to trigger collection:
   - `/api/collect` - Collect for all players
   - `/api/collect/team/<id>` - Collect for a specific team

### Draft System

1. **Create Draft**: Visit `/draft/create` to create a new draft session
   - Select teams (blue and red)
   - Choose draft mode (normal, fearless, ironman)
   - Configure bans per team (default: 5)

2. **View Draft**: Visit `/draft/<session_id>` to participate in the draft
   - Both teams must click "Ready" to start the draft
   - Follow the ban/pick order displayed
   - Champions are automatically validated based on draft mode

3. **Game Links**: Each game generates unique links:
   - Blue side link: `/game/<session_id>/<game_number>/blue/<token>`
   - Red side link: `/game/<session_id>/<game_number>/red/<token>`
   - Spectator link: `/game/<session_id>/<game_number>/spectator/<token>`

4. **Draft History**: Visit `/draft/<session_id>/history` to view the complete series history

### Admin Dashboard

1. **Login**: Visit `/admin/login` with admin credentials
2. **Manage Teams**: Edit team names, add/remove players, delete teams
3. **Manage Drafts**: View all drafts, edit settings, reset games, delete sessions
4. **Tournament Codes**: Add and manage tournament codes for custom games

## API Endpoints

### Team Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/teams` | GET | List all teams |
| `/api/teams/<id>` | GET | Get team details with stats |
| `/api/teams/register` | POST | Register a team |

### Player Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/players/<puuid>/matches` | GET | Player match history |
| `/api/players/<puuid>/stats` | GET | Player aggregated stats |

### Match Collection Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/collect` | POST | Trigger collection for all players |
| `/api/collect/team/<id>` | POST | Trigger collection for specific team |

### Draft Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/draft/sessions` | GET | List all draft sessions |
| `/api/draft/sessions` | POST | Create a new draft session |
| `/api/draft/sessions/<id>` | GET | Get draft session state |
| `/api/draft/sessions/<id>/action` | POST | Execute ban or pick action |
| `/api/draft/sessions/<id>/reset/<game_number>` | POST | Reset a game |
| `/api/draft/sessions/<id>/history` | GET | Get series history |
| `/api/draft/sessions/<id>/game/<game_number>/ready` | POST | Set team ready status |
| `/api/draft/sessions/<id>/game/<game_number>/links` | GET | Get game links |
| `/api/draft/available/<id>` | GET | Get available champions |

### Champion Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/champions` | GET | Get all champions |
| `/api/champions/<id>` | GET | Get a specific champion |

## Project Structure

```
league_tracker/
├── app.py                      # Flask application with all routes
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── .env.example               # Environment variables template
├── data/
│   └── league.db              # SQLite database
├── src/
│   ├── api/
│   │   ├── riot_client.py     # Riot API wrapper
│   │   └── match_collector.py # Match fetching service
│   ├── database/
│   │   └── __init__.py        # SQLAlchemy models
│   └── utils/
│       ├── champions.py       # Champion data and utilities
│       ├── draft_logic.py     # Draft mode logic
│       └── stats_calculator.py # Statistics calculations
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Home page
│   ├── teams.html             # Teams list
│   ├── team_detail.html       # Team profile with stats
│   ├── match_detail.html      # Match details
│   ├── signup.html            # Registration form
│   ├── leaderboards.html      # Rankings
│   ├── error.html             # Error page
│   ├── admin_*.html           # Admin templates
│   └── draft_*.html           # Draft templates
└── static/
    ├── style.css              # CSS styles
    └── script.js              # JavaScript
```

## Configuration

### Environment Variables

Create a `.env` file in the `league_tracker` directory:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True

# Riot API Configuration
RIOT_API_KEY=RGAPI-your-key-here

# Auto-collect Configuration
AUTO_COLLECT_ENABLED=True
AUTO_COLLECT_INTERVAL=5
```

### Tournament Queue

To filter matches by a specific queue, edit [`config.py`](config.py:31):

```python
TOURNAMENT_QUEUE_ID = 0  # Custom/tournament games
# Or use ranked queues:
# TOURNAMENT_QUEUE_ID = 420  # Ranked Solo/Duo
# TOURNAMENT_QUEUE_ID = 440  # Ranked Flex
```

### Scheduler Interval

To change how often matches are collected, edit [`config.py`](config.py:35):

```python
AUTO_COLLECT_INTERVAL = 5  # minutes
```

### Draft Timer

To change the draft timer duration, edit [`draft_logic.py`](src/utils/draft_logic.py:254):

```python
timer_duration=30  # seconds per step
```

## Draft Modes Explained

### Normal Mode
- Standard competitive draft
- Champions can be picked in any game
- Only bans and current picks restrict availability

### Fearless Mode
- Champions used in previous games become unavailable
- Encourages champion diversity across the series
- Each game has a smaller champion pool

### Ironman Mode
- Combines Fearless mode with position restrictions
- Each player must pick a champion they can play
- Position-based champion filtering

## Supported Regions

The following Riot regions are supported:

| Region | Code |
|--------|------|
| North America | `na1` |
| Europe West | `euw1` |
| Europe Nordic & East | `eun1` |
| Korea | `kr` |
| Japan | `jp1` |
| Brazil | `br1` |
| Latin America North | `la1` |
| Latin America South | `la2` |
| Oceania | `oc1` |
| Turkey | `tr1` |
| Russia | `ru` |

## Database Schema

### Core Tables
- **Team**: Team information
- **Player**: Player information with Riot IDs
- **Match**: Match data from Riot API
- **MatchParticipant**: Individual player performance in matches
- **Admin**: Admin user accounts

### Draft Tables
- **DraftSession**: Draft session configuration
- **DraftGame**: Individual game in a series
- **DraftStep**: Each ban/pick action
- **TournamentCode**: Tournament codes for custom games

## Troubleshooting

### Riot API Key Issues
- Ensure your API key is valid and not expired
- API keys expire after 24 hours - get a new one from developer.riotgames.com
- Check that the key is set correctly in `.env` or `config.py`

### Database Issues
- If you encounter database errors, delete `data/league.db` and reinitialize
- Ensure the `data/` directory exists and is writable

### Match Collection Not Working
- Check that `AUTO_COLLECT_ENABLED` is `True` in config
- Verify the Riot API key is valid
- Check the application logs for error messages

### Draft Issues
- Ensure both teams have clicked "Ready" before starting the draft
- Check that the draft mode is correctly configured
- Verify that champions are being validated correctly

## Development

### Running in Debug Mode
Set `DEBUG=True` in `.env` or `config.py` to enable debug mode with auto-reload.

### Adding New Features
1. Add routes in [`app.py`](app.py)
2. Create templates in `templates/`
3. Add static assets in `static/`
4. Update database models in `src/database/__init__.py`

### Testing
```bash
# Run the application
python app.py

# Access the web interface
http://localhost:5000
```

## Production Deployment

For production deployment, consider:

1. **Use a production WSGI server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Use a production database**:
   - PostgreSQL or MySQL instead of SQLite
   - Update `SQLALCHEMY_DATABASE_URI` in config

3. **Set secure environment variables**:
   - Change `SECRET_KEY` to a strong random value
   - Change default admin password
   - Set `DEBUG=False`

4. **Use a hosting platform**:
   - Render, Railway, Fly.io, Heroku, or similar

5. **Set up HTTPS**:
   - Use a reverse proxy like nginx
   - Configure SSL certificates

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the application logs
3. Ensure all dependencies are correctly installed
4. Verify your Riot API key is valid
