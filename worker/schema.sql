-- Create tables for League Tracker

-- Admins table
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    players TEXT  -- Store player IDs as comma-separated string
);

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    puuid TEXT,
    game_name TEXT NOT NULL,
    tag_line TEXT NOT NULL,
    region TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
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
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
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
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES draft_sessions (id) ON DELETE CASCADE
);

-- Draft steps table
CREATE TABLE IF NOT EXISTS draft_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    game_number INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- 'ban' or 'pick'
    champion_id INTEGER NOT NULL,
    team_color TEXT NOT NULL,  -- 'blue' or 'red'
    player_id INTEGER,
    position TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES draft_sessions (id) ON DELETE CASCADE
);

-- Tournament codes table
CREATE TABLE IF NOT EXISTS tournament_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    tournament_name TEXT,
    team_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE SET NULL
);

-- Insert default admin if not exists
INSERT OR IGNORE INTO admins (username, password) VALUES 
('admin', '$2b$12$9zZj9zZj9zZj9zZj9zZj9u7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7v7');