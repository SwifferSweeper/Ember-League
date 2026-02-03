"""Script to clear players and teams data from league.db"""
import sqlite3
import os
import time

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                       'league_tracker', 'data', 'league.db')

def clear_data():
    """Clear all data from players and teams tables."""
    # Try multiple times with delay to handle locking
    for attempt in range(5):
        try:
            # Use a longer timeout and check_same_thread=False for better locking handling
            conn = sqlite3.connect(DB_PATH, timeout=30)
            cursor = conn.cursor()
            
            # Disable foreign key constraints temporarily
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Clear in correct order due to foreign key constraints
            # First delete match participants (references matches)
            cursor.execute("DELETE FROM match_participant")
            print(f"Deleted {cursor.rowcount} match participants")
            
            # Delete matches (may reference teams)
            cursor.execute("DELETE FROM match")
            print(f"Deleted {cursor.rowcount} matches")
            
            # Clear team_players associations
            cursor.execute("DELETE FROM team_players")
            print("Cleared team_players associations")
            
            # Delete players
            cursor.execute("DELETE FROM players")
            print(f"Deleted {cursor.rowcount} players")
            
            # Delete teams
            cursor.execute("DELETE FROM teams")
            print(f"Deleted {cursor.rowcount} teams")
            
            # Commit changes
            conn.commit()
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.close()
            print("\nAll data cleared successfully!")
            return True
            
        except sqlite3.OperationalError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 4:
                print("Waiting 2 seconds before retry...")
                time.sleep(2)
            else:
                print("\nCould not clear database. Make sure the Flask app is not running.")
                return False
    
    return False

if __name__ == "__main__":
    clear_data()
