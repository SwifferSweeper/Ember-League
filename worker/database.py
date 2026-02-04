import os
import json
import sqlite3
from typing import Dict, Any, Optional, List
from cloudflare_d1 import D1Database
from cloudflare_kv import KVNamespace
from cloudflare_workers import Request, Response
from datetime import datetime, timedelta
import hashlib
import secrets

# Import configuration
from config import config, get_db_binding, get_sessions_binding

# Database setup
DB = D1Database(config.D1_DATABASE_NAME, get_db_binding())
SESSIONS = KVNamespace(get_sessions_binding())

# Helper functions

def get_db_connection() -> sqlite3.Connection:
    """Get a database connection."""
    return DB.connection()

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a query and return results as list of dicts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    columns = [column[0] for column in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    conn.close()
    return results

def execute_update(query: str, params: tuple) -> int:
    """Execute an update query and return row count."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    row_count = cursor.rowcount
    conn.close()
    return row_count

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data from KV."""
    session_data = SESSIONS.get(session_id)
    if session_data:
        return json.loads(session_data)
    return None

def set_session(session_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
    """Set session data in KV."""
    SESSIONS.put(session_id, json.dumps(data), ttl=ttl)

def delete_session(session_id: str) -> None:
    """Delete session from KV."""
    SESSIONS.delete(session_id)

def create_session() -> str:
    """Create a new session ID."""
    session_id = secrets.token_urlsafe(32)
    set_session(session_id, {"created_at": datetime.utcnow().isoformat()})
    return session_id

def hash_password(password: str) -> str:
    """Hash a password."""
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + hashed.hex()

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password."""
    salt = bytes.fromhex(stored_password[:32])
    stored_hash = bytes.fromhex(stored_password[32:])
    provided_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
    return stored_hash == provided_hash

def get_current_timestamp() -> str:
    """Get current timestamp as ISO string."""
    return datetime.utcnow().isoformat()

def get_timestamp_days_ago(days: int) -> str:
    """Get timestamp for days ago."""
    return (datetime.utcnow() - timedelta(days=days)).isoformat()

def json_response(data: Any, status: int = 200) -> Response:
    """Create a JSON response."""
    return Response(
        body=json.dumps(data),
        status=status,
        headers={"Content-Type": "application/json"}
    )

def error_response(message: str, status: int = 400) -> Response:
    """Create an error response."""
    return json_response({"error": message}, status)

def validate_request_json(request: Request) -> Optional[Dict[str, Any]]:
    """Validate and parse JSON request body."""
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return None
        return request.json()
    except:
        return None

def require_admin(session: Dict[str, Any]) -> Optional[Response]:
    """Check if user is admin."""
    if not session.get("admin_id"):
        return error_response("Admin access required", 403)
    return None