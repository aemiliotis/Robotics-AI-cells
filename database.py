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

def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.autocommit = False
        return conn
    except Exception as e:
        app.logger.error(f"Database connection failed: {str(e)}")
        raise
        
def get_user_by_email(email):
    """Retrieve user by email with proper error handling"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT id, email, password_hash FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()
            
            if not user:
                app.logger.debug(f"No user found for email: {email}")
                return None
                
            app.logger.debug(f"Retrieved user: {user}")
            return user
            
    except Exception as e:
        app.logger.error(f"Database error in get_user_by_email: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def verify_password(stored_hash, password):
    """Consistent password verification"""
    return check_password_hash(stored_hash, password)

def hash_password(password):
    """Consistent password hashing"""
    return generate_password_hash(password)

# Update user creation to use consistent hashing:
def create_user(email, password):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            """INSERT INTO users (email, password_hash, created_at)
               VALUES (%s, %s, %s) RETURNING id, email""",
            (email, password_hash, datetime.now())
        )
        user = cursor.fetchone()
        conn.commit()
        return {'id': user[0], 'email': user[1]}
    except Exception as e:
        conn.rollback()
        app.logger.error(f"User creation failed: {str(e)}")
        raise
    finally:
        conn.close()

def update_last_login(user_id):
    """Update user's last login timestamp"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET last_login = %s WHERE id = %s",
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
    api_key = secrets.token_urlsafe(32)
    secret_key = secrets.token_hex(32)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Use %s for PostgreSQL instead of ?
        cursor.execute(
            """INSERT INTO api_keys 
               (user_id, api_key, secret_key, name, created_at) 
               VALUES (%s, %s, %s, %s, %s) 
               RETURNING api_key, secret_key""",
            (user_id, api_key, secret_key, name, datetime.now().isoformat())
        )
        
        result = cursor.fetchone()
        conn.commit()
        
        return {
            'api_key': result[0],
            'secret_key': result[1]
        }
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_api_keys_by_user(user_id):
    """Get all API keys for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, api_key, name, created_at, last_used, is_active FROM api_keys WHERE user_id = %s",
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
        "SELECT * FROM api_keys WHERE api_key = %s AND is_active = 1",
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
        "UPDATE api_keys SET last_used = %s WHERE id = %s",
        (datetime.now().isoformat(), api_key_id)
    )
    conn.commit()
    conn.close()

def deactivate_api_key(api_key_id, user_id):
    """Deactivate an API key"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE api_keys SET is_active = 0 WHERE id = %s AND user_id = %s",
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
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
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
           WHERE api_key_id = %s AND timestamp > %s""",
        (api_key_id, since_date)
    )
    stats = cursor.fetchone()
    conn.close()
    
    return dict(stats) if stats else None

# Initialize the database when this module is imported
init_db()
