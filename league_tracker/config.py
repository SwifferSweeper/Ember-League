"""
Configuration for League Tracker Flask application.
"""

import os
from pathlib import Path

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
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Riot API Configuration
# RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")

RIOT_API_KEY = "RGAPI-a08bfde6-b475-4982-a777-3f09c8c23251"

# Tournament queue ID (0 = custom games/tournament mode)
# You can change this to filter specific queue types
TOURNAMENT_QUEUE_ID = 0

# Auto-collect matches in production (set to False to disable)
AUTO_COLLECT_ENABLED = os.getenv("AUTO_COLLECT_ENABLED", "True").lower() == "true"
AUTO_COLLECT_INTERVAL = int(os.getenv("AUTO_COLLECT_INTERVAL", "5"))  # minutes

# Regional routing
REGIONAL_ROUTING = {
    "americas": "americas",
    "europe": "europe",
    "asia": "asia",
    "sea": "sea",
}

# Supported regions
SUPPORTED_REGIONS = ["na1", "euw1", "eun1", "kr", "jp1", "br1", "la1", "la2", "oc1", "tr1", "ru"]


def validate_api_key() -> bool:
    """Check if API key is configured."""
    return bool(RIOT_API_KEY and RIOT_API_KEY != "")


# Database URI
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
