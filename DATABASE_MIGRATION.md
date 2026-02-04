# Database Migration Guide: SQLite to PostgreSQL on Railway

This guide explains how to migrate your existing SQLite database to PostgreSQL on Railway.

## Where is Your Current Data?

### Database File Location

Your SQLite database file is located at:
- **`league_tracker/data/league.db`** - Your local SQLite database file

### Database Tables Definition

The table schemas are defined in [`league_tracker/src/database/__init__.py`](league_tracker/src/database/__init__.py:1-410):

| Table | Description | File Location |
|-------|-------------|---------------|
| `admins` | Admin users | [`league_tracker/src/database/__init__.py:15-35`](league_tracker/src/database/__init__.py:15) |
| `teams` | Registered teams | [`league_tracker/src/database/__init__.py:38-55`](league_tracker/src/database/__init__.py:38) |
| `players` | Players with Riot IDs | [`league_tracker/src/database/__init__.py:58-85`](league_tracker/src/database/__init__.py:58) |
| `team_players` | Team-player associations | [`league_tracker/src/database/__init__.py:88-98`](league_tracker/src/database/__init__.py:88) |
| `match` | Match records | [`league_tracker/src/database/__init__.py:101-130`](league_tracker/src/database/__init__.py:101) |
| `match_participant` | Individual player stats | [`league_tracker/src/database/__init__.py:133-186`](league_tracker/src/database/__init__.py:133) |
| `tournament_codes` | Tournament codes | [`league_tracker/src/database/__init__.py:197-223`](league_tracker/src/database/__init__.py:197) |
| `draft_sessions` | Draft sessions | [`league_tracker/src/database/__init__.py:232-302`](league_tracker/src/database/__init__.py:232) |
| `draft_games` | Draft games within sessions | [`league_tracker/src/database/__init__.py:305-364`](league_tracker/src/database/__init__.py:305) |
| `draft_steps` | Individual ban/pick actions | [`league_tracker/src/database/__init__.py:367-403`](league_tracker/src/database/__init__.py:367) |

## Viewing Your Current Data

### Using SQLite3 Command Line

```bash
# View all tables
sqlite3 league_tracker/data/league.db ".tables"

# View table schema
sqlite3 league_tracker/data/league.db ".schema teams"

# View all teams
sqlite3 league_tracker/data/league.db "SELECT * FROM teams;"

# View all players
sqlite3 league_tracker/data/league.db "SELECT * FROM players;"

# View match count
sqlite3 league_tracker/data/league.db "SELECT COUNT(*) FROM match;"

# View draft sessions
sqlite3 league_tracker/data/league.db "SELECT * FROM draft_sessions;"

# Export entire database to SQL
sqlite3 league_tracker/data/league.db ".dump" > league_data_backup.sql
```

### Using Python

```python
import sqlite3

conn = sqlite3.connect('league_tracker/data/league.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

# Get row counts for each table
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"{table_name}: {count} rows")

conn.close()
```

## Option 1: Fresh Start (Recommended for new deployments)

If you don't have critical data, simply:
1. Deploy to Railway (PostgreSQL will be empty)
2. Railway will auto-create tables on first run
3. Start fresh with new data

## Option 2: Migrate Existing Data

### Step 1: Export SQLite Data

Run this script to export your SQLite data to SQL statements:

```python
# export_sqlite.py
import sqlite3

# Connect to your SQLite database
conn = sqlite3.connect('league_tracker/data/league.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

output = []

for table in tables:
    table_name = table[0]
    print(f"Exporting {table_name}...")
    
    # Get table data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]
    
    for row in rows:
        values = []
        for val in row:
            if val is None:
                values.append('NULL')
            elif isinstance(val, bool):
                values.append('TRUE' if val else 'FALSE')
            elif isinstance(val, str):
                # Escape single quotes
                escaped = val.replace("'", "''")
                values.append(f"'{escaped}'")
            else:
                values.append(str(val))
        
        cols = ', '.join(col_names)
        vals = ', '.join(values)
        output.append(f"INSERT INTO {table_name} ({cols}) VALUES ({vals});")

conn.close()

# Write to file
with open('export.sql', 'w') as f:
    f.write('\n'.join(output))

print("Exported to export.sql")
```

### Step 2: Get Railway PostgreSQL Connection String

1. Go to Railway Dashboard
2. Click on your PostgreSQL database
3. Click "Connect" → "Connection String"
4. Copy the `postgres://...` URL

### Step 3: Import Data to PostgreSQL

Using psql (install PostgreSQL locally first):

```bash
psql "postgres://user:password@host:5432/db" -f export.sql
```

Or using the Railway CLI:

```bash
# Connect to Railway PostgreSQL
railway connect postgresql

# Run the import
psql "postgres://..." -f export.sql
```

### Step 4: Verify Import

Connect to Railway PostgreSQL and verify:

```bash
railway connect postgresql
psql "postgres://..."
```

Then run:
```sql
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM players;
SELECT COUNT(*) FROM match;
```

## Option 3: Use pgloader (Advanced)

[pgloader](https://pgloader.io/) can migrate SQLite to PostgreSQL automatically:

```bash
# Install pgloader
brew install pgloader  # macOS
# or: apt-get install pgloader  # Linux

# Create migration command
load sqlite:////path/to/league_tracker/data/league.db
      postgresql://user:password@host:5432/db
```

## Troubleshooting

### Foreign Key Errors

If you get foreign key errors during import:
1. Disable foreign key checks in PostgreSQL before import:
   ```sql
   SET session_replication_role = 'replica';
   -- run imports
   SET session_replication_role = 'origin';
   ```

### Serial/Identity Columns

PostgreSQL uses SERIAL or IDENTITY for auto-increment. SQLite uses INTEGER PRIMARY KEY. The migration script handles this, but you may need to adjust sequences:

```sql
-- After import, fix sequences
SELECT setval('teams_id_seq', (SELECT MAX(id) FROM teams));
SELECT setval('players_id_seq', (SELECT MAX(id) FROM players));
SELECT setval('match_id_seq', (SELECT MAX(id) FROM "match"));
-- etc for all tables with serial columns
```

### JSON Data Types

SQLite stores JSON as text. PostgreSQL has native JSON. Your draft data (bans, picks, ironman_assignments) will be imported as text. To convert:

```sql
ALTER TABLE draft_games ALTER COLUMN bans_blue TYPE json USING bans_blue::json;
ALTER TABLE draft_games ALTER COLUMN bans_red TYPE json USING bans_red::json;
-- repeat for all JSON columns
```

## Auto-Migration Script

Create this script in `league_tracker/` to handle migrations:

```python
# migrate_db.py
import os
import sys

def migrate_sqlite_to_postgres():
    """Migrate SQLite data to PostgreSQL."""
    from sqlalchemy import create_engine, text
    
    # SQLite connection
    sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'league.db')
    sqlite_url = f'sqlite:///{sqlite_path}'
    
    # Get PostgreSQL URL from environment
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        print("DATABASE_URL not set. Skipping migration.")
        return
    
    sqlite_engine = create_engine(sqlite_url)
    pg_engine = create_engine(postgres_url)
    
    # Read SQLite data
    with sqlite_engine.connect() as sqlite_conn:
        result = sqlite_conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        
        for table in tables:
            print(f"Migrating {table}...")
            result = sqlite_conn.execute(text(f"SELECT * FROM {table}"))
            rows = result.fetchall()
            
            if not rows:
                continue
            
            # Get column names from SQLite
            result = sqlite_conn.execute(text(f"PRAGMA table_info({table})"))
            columns = [row[1] for row in result.fetchall()]
            
            with pg_engine.connect() as pg_conn:
                for row in rows:
                    placeholders = ', '.join([':' + str(i) for i in range(len(columns))])
                    columns_str = ', '.join(columns)
                    insert_stmt = text(f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})")
                    pg_conn.execute(insert_stmt, dict(zip(columns, row)))
                pg_conn.commit()
    
    print("Migration complete!")

if __name__ == '__main__':
    migrate_sqlite_to_postgres()
```

## Environment Variables for Migration

When running the migration script, ensure these are set:

```bash
# Export DATABASE_URL from Railway
export DATABASE_URL="postgres://user:pass@host:5432/db"

# Run migration
cd league_tracker
python migrate_db.py
```

## Schedule the Migration

Add this to your deployment checklist:

1. ☐ Deploy Railway app with PostgreSQL
2. ☐ Get DATABASE_URL from Railway
3. ☐ Run export_sqlite.py to create export.sql
4. ☐ Import export.sql into Railway PostgreSQL
5. ☐ Verify data counts match
6. ☐ Test the application
7. ☐ Update DNS/URLs to point to Railway
