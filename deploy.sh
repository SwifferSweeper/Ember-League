#!/bin/bash

# Deployment script for League Tracker to Cloudflare Pages + Workers

set -e

echo "🚀 Deploying League Tracker to Cloudflare..."

# Check if wrangler is installed
if ! command -v wrangler &&; then
    echo "❌ wrangler CLI not found. Please install it first:"
    echo "npm install -g wrangler"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "wrangler.toml" ]; then
    echo "❌ wrangler.toml not found. Make sure you're in the project root."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Cloudflare configuration
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFARE_API_TOKEN=your_api_token_here

# Riot API configuration
RIOT_API_KEY=your_riot_api_key_here

# Application configuration
SECRET_KEY=your_secret_key_here
DEBUG=false
AUTO_COLLECT_ENABLED=true
AUTO_COLLECT_INTERVAL=5
EOF
    echo "✅ .env file created. Please edit it with your actual values."
fi

# Create data directory
mkdir -p data

# Create Cloudflare resources
echo "🔧 Creating Cloudflare resources..."

# Create D1 database
echo "🔧 Creating D1 database..."
wrangler d1 create league-tracker-db

# Create KV namespace for sessions
echo "🔧 Creating KV namespace for sessions..."
wrangler kv:namespace create SESSIONS

# Create R2 bucket for static assets (optional)
echo "🔧 Creating R2 bucket for static assets..."
wrangler r2 bucket create league-tracker-assets

# Update wrangler.toml with actual IDs
echo "🔧 Updating wrangler.toml with actual resource IDs..."

# Get the actual IDs from wrangler
d1_id=$(wrangler d1 list | grep league-tracker-db | awk '{print $1}')
kv_id=$(wrangler kv:namespace list | grep SESSIONS | awk '{print $1}')
r2_id=$(wrangler r2 bucket list | grep league-tracker-assets | awk '{print $1}')

# Update wrangler.toml with actual IDs
sed -i "s/your-database-id-here/$d1_id/g" wrangler.toml
sed -i "s/your-kv-namespace-id-here/$kv_id/g" wrangler.toml
sed -i "s/your-r2-bucket-id-here/$r2_id/g" wrangler.toml

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the project
echo "🔨 Building the project..."
npm run build

# Deploy to Cloudflare
echo "✨ Deploying to Cloudflare..."
wrangler deploy

# Initialize database schema
echo "🔧 Initializing database schema..."
wrangler d1 eval --binding DB "
    -- Create tables for League Tracker
    
    -- Admins table
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime(''now''))
    );
    
    -- Teams table
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime(''now'')),
        players TEXT  -- Store player IDs as comma-separated string
    );
    
    -- Players table
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        puuid TEXT,
        game_name TEXT NOT NULL,
        tag_line TEXT NOT NULL,
        region TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime(''now''))
    );
    
    -- Team players junction table
    CREATE TABLE IF NOT EXISTS team_players (
        team_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
        FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE,
        PRIMARY KEY (team_id, player_id)
    );
    
    -- Matches table
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT UNIQUE NOT NULL,
        game_mode TEXT NOT NULL,
        queue_id INTEGER NOT NULL,
        duration INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        game_version TEXT NOT NULL,
        platform_id TEXT NOT NULL
    );
    
    -- Match participants table
    CREATE TABLE IF NOT EXISTS match_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        puuid TEXT NOT NULL,
        champion_id INTEGER NOT NULL,
        kills INTEGER NOT NULL,
        deaths INTEGER NOT NULL,
        assists INTEGER NOT NULL,
        win BOOLEAN NOT NULL,
        team_id INTEGER NOT NULL,
        individual_position TEXT NOT NULL,
        champion_name TEXT NOT NULL,
        FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE
    );
    
    -- Draft sessions table
    CREATE TABLE IF NOT EXISTS draft_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        draft_mode TEXT NOT NULL,
        team_blue_id INTEGER NOT NULL,
        team_red_id INTEGER NOT NULL,
        bans_per_team INTEGER NOT NULL DEFAULT 5,
        picks_per_team INTEGER NOT NULL DEFAULT 5,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        current_game_number INTEGER NOT NULL DEFAULT 1,
        current_team_turn TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime(''now'')),
        completed_at TEXT
    );
    
    -- Draft games table
    CREATE TABLE IF NOT EXISTS draft_games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        game_number INTEGER NOT NULL,
        blue_side_link TEXT,
        red_side_link TEXT,
        spectator_link TEXT,
        blue_ready BOOLEAN NOT NULL DEFAULT 0,
        red_ready BOOLEAN NOT NULL DEFAULT 0,
        match_started BOOLEAN NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime(''now'')),
        FOREIGN KEY (session_id) REFERENCES draft_sessions (id) ON DELETE CASCADE
    );
    
    -- Draft steps table
    CREATE TABLE IF NOT EXISTS draft_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        game_number INTEGER NOT NULL,
        step_number INTEGER NOT NULL,
        action_type TEXT NOT NULL,  -- ''ban' or ''pick'
        champion_id INTEGER NOT NULL,
        team_color TEXT NOT NULL,  -- ''blue' or ''red'
        player_id INTEGER,
        position TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime(''now'')),
        FOREIGN KEY (session_id) REFERENCES draft_sessions (id) ON DELETE CASCADE
    );
    
    -- Tournament codes table
    CREATE TABLE IF NOT EXISTS tournament_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        tournament_name TEXT,
        team_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime(''now'')),
        FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE SET NULL
    );
    
    -- Insert default admin if not exists
    INSERT OR IGNORE INTO admins (username, password) VALUES 
    ('admin', '$2b$12$9zZj9zZj9zZj9zZj9zZj9u7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7');
"

# Set secrets
echo "🔑 Setting secrets..."
wrangler secret put RIOT_API_KEY --from-literal "$RIOT_API_KEY"
wrangler secret put SECRET_KEY --from-literal "$SECRET_KEY"

# Test the deployment
echo "🧪 Testing the deployment..."
curl -f "https://your-workers-url.com/api/teams" && echo "✅ API is responding!"

# Create GitHub Actions workflow for CI/CD
echo "📝 Creating GitHub Actions workflow..."
cat > .github/workflows/deploy.yml << EOF
name: Deploy to Cloudflare

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    
    - name: Install wrangler
      run: npm install -g wrangler
    
    - name: Deploy to Cloudflare
      run: |
        wrangler deploy
      env:
        CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
        CLOUDFARE_API_TOKEN: ${{ secrets.CLOUDFARE_API_TOKEN }}
EOF

echo "🎉 Deployment complete!"
echo "📋 Next steps:"
echo "1. Update wrangler.toml with your actual resource IDs"
echo "2. Set up your Cloudflare account and API token"
echo "3. Configure your domain if needed"
echo "4. Set up the database schema"
echo "5. Test your application at: https://your-workers-url.com"
echo ""
echo "🚀 Your League Tracker is now running on Cloudflare Pages + Workers!"