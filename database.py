import sqlite3
import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

# Database setup
DB_PATH = os.environ.get('DATABASE_URL', 'robotics_ai_hub.db')
USE_SQLITE = False  # Set to True if using SQLite, False for PostgreSQL

# Improved detection of PostgreSQL connection strings
def is_postgres_url(url):
    return url.startswith('postgresql://') or url.startswith('postgres://')

def get_db_connection():
    """Get database connection based on environment"""
    if is_postgres_url(DB_PATH):
        # For PostgreSQL (Neon.tech)
        db_url = DB_PATH
        # Handle both postgres:// and postgresql:// formats
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(db_url)
        conn.cursor_factory = RealDictCursor
        return conn
    else:
        # For SQLite (local development)
        # Ensure the directory exists
        db_dir = os.path.dirname(os.path.abspath(DB_PATH))
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        last_login TIMESTAMP
    )
    ''')
    
    # Create API keys table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_keys (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        secret_key TEXT NOT NULL,
        name TEXT,
        created_at TIMESTAMP NOT NULL,
        last_used TIMESTAMP,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create API usage logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_usage (
        id TEXT PRIMARY KEY,
        api_key_id TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        request_data TEXT,
        response_data TEXT,
        timestamp TIMESTAMP NOT NULL,
        execution_time_ms INTEGER,
        status_code INTEGER,
        FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# User management functions
# Change from SQLite to PostgreSQL syntax
def create_user(email, password):
    password_hash = generate_password_hash(password)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (%s, %s, %s) RETURNING id, email",
            (email, password_hash, datetime.utcnow())
        )
        user = cursor.fetchone()
        conn.commit()
        return {'id': user[0], 'email': user[1]}
    except psycopg2.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    conn.close()
    
    return dict(user) if user else None

def verify_password(stored_hash, password):
    """Verify a password against its hash"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == stored_hash

def hash_password(password):
    """Hash a password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def update_last_login(user_id):
    """Update user's last login timestamp"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now().isoformat(), user_id)
    )
    conn.commit()
    conn.close()

# API key management functions
def generate_api_key():
    """Generate a new API key"""
    return secrets.token_urlsafe(32)

def generate_secret_key():
    """Generate a new secret key"""
    return secrets.token_hex(32)

def create_api_key(user_id, name=None):
    """Create a new API key for a user"""
    api_key_id = str(uuid.uuid4())
    api_key = generate_api_key()
    secret_key = generate_secret_key()
    created_at = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO api_keys (id, user_id, api_key, secret_key, name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (api_key_id, user_id, api_key, secret_key, name, created_at)
    )
    conn.commit()
    conn.close()
    
    return {
        "id": api_key_id,
        "api_key": api_key,
        "secret_key": secret_key,
        "name": name,
        "created_at": created_at
    }

def get_api_keys_by_user(user_id):
    """Get all API keys for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, api_key, name, created_at, last_used, is_active FROM api_keys WHERE user_id = ?",
        (user_id,)
    )
    keys = cursor.fetchall()
    conn.close()
    
    return [dict(key) for key in keys]

def get_api_key_details(api_key):
    """Get API key details by the key itself"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM api_keys WHERE api_key = ? AND is_active = 1",
        (api_key,)
    )
    key = cursor.fetchone()
    conn.close()
    
    return dict(key) if key else None

def update_api_key_usage(api_key_id):
    """Update the last used timestamp for an API key"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE api_keys SET last_used = ? WHERE id = ?",
        (datetime.now().isoformat(), api_key_id)
    )
    conn.commit()
    conn.close()

def deactivate_api_key(api_key_id, user_id):
    """Deactivate an API key"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE api_keys SET is_active = 0 WHERE id = ? AND user_id = ?",
        (api_key_id, user_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0

# API usage logging
def log_api_usage(api_key_id, endpoint, request_data, response_data, execution_time_ms, status_code):
    """Log API usage for analytics and rate limiting"""
    log_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO api_usage 
           (id, api_key_id, endpoint, request_data, response_data, timestamp, execution_time_ms, status_code) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (log_id, api_key_id, endpoint, request_data, response_data, timestamp, execution_time_ms, status_code)
    )
    conn.commit()
    conn.close()

def get_api_usage_stats(api_key_id, days=30):
    """Get API usage statistics for an API key"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    since_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor.execute(
        """SELECT 
           COUNT(*) as total_requests,
           AVG(execution_time_ms) as avg_execution_time,
           COUNT(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 END) as successful_requests,
           COUNT(CASE WHEN status_code >= 400 THEN 1 END) as failed_requests
           FROM api_usage 
           WHERE api_key_id = ? AND timestamp > ?""",
        (api_key_id, since_date)
    )
    stats = cursor.fetchone()
    conn.close()
    
    return dict(stats) if stats else None

# Initialize the database when this module is imported
init_db()
