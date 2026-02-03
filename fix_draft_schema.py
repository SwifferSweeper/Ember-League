#!/usr/bin/env python
"""
Script to fix the database schema by adding missing columns.
Run this to update an existing database to match the current model definitions.
"""
import sqlite3
import os

# Get the database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'league_tracker', 'data', 'league.db')

def fix_draft_sessions_schema():
    """Add missing columns to draft_sessions table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(draft_sessions)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    print(f"Existing columns in draft_sessions: {existing_columns}")
    
    # Define columns that should exist based on the model
    # timer_started_at was added after initial schema
    columns_to_add = [
        ("timer_started_at", "DATETIME"),
        ("timer_duration", "INTEGER DEFAULT 30"),
        ("blue_captain_id", "INTEGER"),
        ("red_captain_id", "INTEGER"),
    ]
    
    for col_name, col_def in columns_to_add:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE draft_sessions ADD COLUMN {col_name} {col_def}")
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"✗ Failed to add {col_name}: {e}")
        else:
            print(f"Column already exists: {col_name}")
    
    conn.commit()
    conn.close()
    print("\nSchema update complete!")

if __name__ == "__main__":
    fix_draft_sessions_schema()
