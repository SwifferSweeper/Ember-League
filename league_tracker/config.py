"""
Configuration for League Tracker Flask application.
Supports both local development and Railway deployment.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Project paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "league.db"

# Flask configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Riot API Configuration
RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")

# Database configuration
# Railway provides DATABASE_URL for PostgreSQL
# For local development, use SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    # Use PostgreSQL on Railway
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    # Disable foreign key constraints for SQLite compatibility
    SQLALCHEMY_ENGINE_OPTIONS = {"isolation_level": "autocommit"}
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
