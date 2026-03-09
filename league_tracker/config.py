"""
Configuration for League Tracker Flask application.
Supports both local development and Railway deployment.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

# Project paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "league.db"

# Flask configuration
# Note: Environment variables take precedence over .env file
# Railway dashboard variables are set as environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Riot API Configuration
RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")

# Database configuration
# Railway provides DATABASE_URL for PostgreSQL as environment variable
# For local development, use SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    # Use PostgreSQL on Railway
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_ENGINE_OPTIONS = {}
else:
    # Use SQLite for local development
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_ENGINE_OPTIONS = {}

SQLALCHEMY_TRACK_MODIFICATIONS = False

# Auto-collect configuration
AUTO_COLLECT_ENABLED = os.getenv("AUTO_COLLECT_ENABLED", "True").lower() == "true"
AUTO_COLLECT_INTERVAL = int(os.getenv("AUTO_COLLECT_INTERVAL", "5"))

def validate_api_key():
    """Validate the Riot API key."""
    return bool(RIOT_API_KEY and RIOT_API_KEY != "")

# Tournament queue ID for match collection (None = all queues, or set to specific queue ID)
TOURNAMENT_QUEUE_ID = None  # Set to int queue ID like 0 for custom games, or None for all
