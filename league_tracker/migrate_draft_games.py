"""
Migration script to add new columns to draft_games table.
Run this script to update the database schema.
"""
import sqlite3
import os

def migrate_database():
    # Find the database file
    db_path = os.path.join('league_tracker', 'data', 'league.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(draft_games)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add new columns if they don't exist
    new_columns = {
        'blue_side_link': 'VARCHAR(255)',
        'red_side_link': 'VARCHAR(255)',
        'spectator_link': 'VARCHAR(255)',
        'blue_ready': 'BOOLEAN DEFAULT 0',
        'red_ready': 'BOOLEAN DEFAULT 0',
        'match_started': 'BOOLEAN DEFAULT 0',
        'match_started_at': 'DATETIME'
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE draft_games ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"Error adding column {col_name}: {e}")
        else:
            print(f"Column already exists: {col_name}")
    
    conn.commit()
    conn.close()
    print("\nMigration completed!")

if __name__ == '__main__':
    migrate_database()
