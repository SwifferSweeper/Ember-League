import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Project paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Configuration
class Config:
    """Cloudflare Workers configuration."""
    
    # Flask configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Riot API Configuration
    RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
    
    # Tournament queue ID
    TOURNAMENT_QUEUE_ID = 0
    
    # Auto-collect matches
    AUTO_COLLECT_ENABLED = os.getenv("AUTO_COLLECT_ENABLED", "True").lower() == "true"
    AUTO_COLLECT_INTERVAL = int(os.getenv("AUTO_COLLECT_INTERVAL", "5"))  # minutes
    
    # Database
    D1_DATABASE_NAME = "league-tracker-db"
    
    # KV namespace for sessions
    SESSIONS_NAMESPACE = "SESSIONS"
    
    @staticmethod
    def validate_api_key() -> bool:
        """Check if API key is configured."""
        return bool(Config.RIOT_API_KEY and Config.RIOT_API_KEY != "")

# Global config instance
config = Config()

# Helper functions

def get_env_var(name: str, default: Optional[str] = None) -> str:
    """Get environment variable with fallback."""
    return os.getenv(name, default)

def get_db_binding() -> str:
    """Get D1 database binding name."""
    return "DB"

def get_sessions_binding() -> str:
    """Get KV sessions binding name."""
    return "SESSIONS"

def get_static_assets_binding() -> str:
    """Get R2 static assets binding name."""
    return "STATIC_ASSETS"

def get_cron_triggers() -> list:
    """Get cron triggers configuration."""
    return ["*/5 * * * *"]  # Every 5 minutes