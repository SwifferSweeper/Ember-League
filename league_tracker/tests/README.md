# League Tracker Tests

This directory contains the unit tests for the League Tracker application.

## Test Structure

```
tests/
├── __init__.py           # Tests package initialization
├── conftest.py           # Pytest fixtures and configuration
├── test_database.py       # Database model tests
├── test_riot_client.py   # Riot API client tests
├── test_match_collector.py # Match collector tests
├── test_champions.py      # Champions utility tests
├── test_stats_calculator.py # Stats calculator tests
├── test_draft_logic.py    # Draft logic tests
└── test_app_routes.py     # Flask app route tests
```

## Running Tests

### Run all tests:
```bash
cd league_tracker
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_database.py -v
```

### Run tests with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run tests by marker:
```bash
# Run only unit tests
pytest tests/ -m unit

# Run only API tests
pytest tests/ -m api

# Run only database tests
pytest tests/ -m database
```

## Test Fixtures

The `conftest.py` file provides the following fixtures:

- `app`: Flask application instance with test database
- `client`: Flask test client
- `runner`: Flask CLI test runner
- `db_session`: Database session for testing
- `sample_admin`: Sample admin user
- `sample_team`: Sample team
- `sample_player`: Sample player
- `sample_team_with_players`: Sample team with 5 players
- `sample_match`: Sample match with participants
- `sample_tournament_code`: Sample tournament code
- `sample_draft_session`: Sample draft session
- `authenticated_client`: Test client with admin session
- `mock_riot_api_key`: Mocked Riot API key
- `mock_riot_client_responses`: Mocked Riot API responses

## Test Coverage

The test suite covers:

- **Database Models**: All SQLAlchemy models (Admin, Team, Player, Match, MatchParticipant, TournamentCode, DraftSession, DraftGame, DraftStep)
- **API Modules**: RiotClient and MatchCollector
- **Utilities**: Champions data, StatsCalculator, DraftLogic
- **Flask Routes**: All public and admin routes

## CI/CD

Tests are automatically run on GitHub Actions for:
- Python 3.10, 3.11, 3.12
- Linting with Ruff
- Code formatting with Ruff
- Test coverage reporting

## Adding New Tests

1. Create a new test file in the `tests/` directory
2. Import necessary fixtures from `conftest.py`
3. Use appropriate test markers (`@pytest.mark.unit`, `@pytest.mark.api`, etc.)
4. Follow the naming convention: `test_<module>.py`
5. Write descriptive test names that explain what is being tested

## Best Practices

- Keep tests isolated and independent
- Use fixtures for common setup
- Mock external dependencies (Riot API, etc.)
- Test both success and failure cases
- Use descriptive test names
- Keep tests fast (unit tests should run in seconds)
