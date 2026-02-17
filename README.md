# League Tracker

A League of Legends league tracking application for managing teams, tracking matches, and running tournament drafts.

## Features

- **Team Management**: Create and manage teams with players
- **Match Tracking**: Automatic match collection and statistics via Riot API
- **Admin Dashboard**: Secure admin interface for managing the league
- **Draft Tool**: Tournament draft management with live updates
- **Leaderboards**: Player and team statistics
- **Player History**: Individual player match history and performance

## Tech Stack

- **Backend**: Flask (Python 3.11)
- **Database**: PostgreSQL (Railway)
- **Frontend**: Jinja2 templates with HTML/CSS/JavaScript
- **API Integration**: Riot Games API via riotwatcher
- **Task Scheduling**: APScheduler for automatic match collection

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database (or use Railway)
- Riot API key from [Riot Developer Portal](https://developer.riotgames.com/)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/riot_api_project_ember.git
   cd riot_api_project_ember
   ```

2. **Create virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```
   RIOT_API_KEY=your_riot_api_key
   SECRET_KEY=your_secret_key
   DEBUG=True
   ```

4. **Run the application**
   ```bash
   flask --app league_tracker.app run
   ```

## Deployment (Railway)

See [DEPLOYMENT_RAILWAY.md](./DEPLOYMENT_RAILWAY.md) for detailed instructions.

### Quick Deploy

1. Create a Railway account at https://railway.app
2. Connect your GitHub repository
3. Add a PostgreSQL database
4. Set environment variables:
   - `RIOT_API_KEY` - Your Riot Games API key
   - `SECRET_KEY` - Generate with `openssl rand -base64 32`
5. Deploy!

## Project Structure

```
riot_api_project_ember/
├── Procfile                  # Railway start command
├── requirements.txt          # Python dependencies
├── runtime.txt               # Python version
├── pytest.ini               # Test configuration
├── ruff.toml                # Linting configuration
├── league_tracker/
│   ├── app.py               # Main Flask application
│   ├── config.py            # Configuration settings
│   ├── scheduled_tasks.py   # Background task runner
│   ├── static/              # Static files (CSS, JS)
│   ├── templates/           # HTML templates
│   ├── tests/               # Test files
│   └── src/
│       ├── api/             # Riot API client & match collector
│       ├── database/        # Database models & operations
│       └── utils/           # Utility functions
```

## API Endpoints

### Public Routes
- `GET /` - Home page
- `GET /teams` - Team listing
- `GET /teams/<id>` - Team details
- `GET /matches` - Match history
- `GET /players/<puuid>` - Player details
- `GET /leaderboards` - Statistics leaderboards

### Draft System
- `GET /draft` - Draft lobby
- `GET /draft/<id>` - Draft session
- `POST /draft/create` - Create new draft

### Admin Routes
- `GET /admin` - Admin dashboard
- `GET /admin/teams` - Manage teams
- `GET /admin/players` - Manage players
- `GET /admin/drafts` - Manage drafts

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Auto | PostgreSQL connection string (auto-set on Railway) |
| `RIOT_API_KEY` | Yes | Riot Games API key |
| `SECRET_KEY` | Yes | Secret key for sessions |
| `DEBUG` | No | Enable debug mode (default: False) |
| `AUTO_COLLECT_ENABLED` | No | Enable automatic match collection |
| `AUTO_COLLECT_INTERVAL` | No | Collection interval in minutes (default: 5) |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=league_tracker

# Run specific test file
pytest league_tracker/tests/test_app_routes.py
```

## Development

### Code Style

This project uses Ruff for linting and formatting:

```bash
# Check for issues
ruff check .

# Format code
ruff format .
```

### Database Migrations

The application automatically creates tables on startup. For schema changes, update the models in `league_tracker/src/database/__init__.py`.

## Cost Estimation (Railway)

| Service | Free Tier | Notes |
|---------|-----------|-------|
| Railway | $5 credit/month | ~$0.10/service/hour |
| PostgreSQL | Included | Storage: ~$0.01/GB/month |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the [Riot API documentation](https://developer.riotgames.com/docs/lol)
