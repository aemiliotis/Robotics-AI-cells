from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS
import secrets
import psycopg2
from datetime import datetime, timedelta
import hashlib
import shutil
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import jwt
from functools import wraps
import requests
import json

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ALGORITHM'] = 'HS256'

# Pi Network configuration
PI_NETWORK_CONFIG = {
    'api_key': os.environ.get('PI_API_KEY'),
    'client_id': os.environ.get('PI_CLIENT_ID', 'your_pi_client_id'),
    'client_secret': os.environ.get('PI_CLIENT_SECRET', 'your_pi_client_secret'),
    'redirect_uri': os.environ.get('PI_REDIRECT_URI', 'https://aemiliotis.github.io/Robotics-AI-Cells'),
    'auth_url': 'https://socialchain.app/oauth/authorize',
    'token_url': 'https://api.minepi.com/oauth/token',
    'user_info_url': 'https://api.minepi.com/me'
}

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
    strategy="fixed-window",
    default_limits=["200 per day", "50 per hour"]
)

def get_db():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

# Database setup with Pi Network integration
def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            # Users table with Pi Network integration
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    pi_user_id VARCHAR(100) UNIQUE NOT NULL,
                    username VARCHAR(100),
                    email VARCHAR(255),
                    api_key VARCHAR(64) UNIQUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    pi_access_token TEXT,
                    pi_refresh_token TEXT,
                    token_expires_at TIMESTAMP
                )
            """)
        
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cell_usage (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    cell_name VARCHAR(50) NOT NULL,
                    input_hash VARCHAR(64) NOT NULL,
                    session_id VARCHAR(36) NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    execution_time FLOAT
                )
            """)
        
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(36) PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_active TIMESTAMP
                )
            """)
        
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    api_key VARCHAR(64) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    permissions JSONB DEFAULT '["cells:execute"]',
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
        
            conn.commit()
        conn.close()

# Pi Network OAuth functions
def get_pi_auth_url(state):
    """Generate Pi Network OAuth URL"""
    params = {
        'client_id': PI_NETWORK_CONFIG['client_id'],
        'redirect_uri': PI_NETWORK_CONFIG['redirect_uri'],
        'scope': 'username payments wallet',
        'response_type': 'code',
        'state': state
    }
    return f"{PI_NETWORK_CONFIG['auth_url']}?{requests.compat.urlencode(params)}"

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    try:
        response = requests.post(
            PI_NETWORK_CONFIG['token_url'],
            data={
                'client_id': PI_NETWORK_CONFIG['client_id'],
                'client_secret': PI_NETWORK_CONFIG['client_secret'],
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': PI_NETWORK_CONFIG['redirect_uri']
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"Token exchange failed: {response.text}")
            return None
    except Exception as e:
        app.logger.error(f"Token exchange error: {str(e)}")
        return None

def get_pi_user_info(access_token):
    """Get user info from Pi Network"""
    try:
        response = requests.get(
            PI_NETWORK_CONFIG['user_info_url'],
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"User info fetch failed: {response.text}")
            return None
    except Exception as e:
        app.logger.error(f"User info error: {str(e)}")
        return None

# Authentication decorators
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
            
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check both users table (legacy) and api_keys table
                cur.execute("""
                    SELECT u.id, u.username, u.pi_user_id, ak.permissions, ak.expires_at
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.id
                    WHERE ak.api_key = %s AND ak.is_active = TRUE
                    AND (ak.expires_at IS NULL OR ak.expires_at > NOW())
                """, (api_key,))
                api_key_info = cur.fetchone()
                
                if not api_key_info:
                    # Fallback to legacy user api_key
                    cur.execute("""
                        SELECT id, username, pi_user_id FROM users 
                        WHERE api_key = %s AND is_active = TRUE
                    """, (api_key,))
                    user = cur.fetchone()
                    if not user:
                        return jsonify({"error": "Invalid API key"}), 401
                    
                    api_key_info = (user[0], user[1], user[2], '["cells:execute"]', None)
                
                request.user_id = api_key_info[0]
                request.username = api_key_info[1]
                request.pi_user_id = api_key_info[2]
                request.permissions = json.loads(api_key_info[3]) if api_key_info[3] else ["cells:execute"]
                
                # Update last login
                cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (request.user_id,))
                conn.commit()
                
        return f(*args, **kwargs)
    return decorated_function

# CORS Configuration
CORS(app, resources={
    r"/.*": {
        "origins": [
            "https://aemiliotis.github.io",
            "https://aemiliotis.github.io/Robotics-AI-Cells",
            "http://localhost:*",
            "http://127.0.0.1:*"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Session-Id", "X-Request-Id"],
        "supports_credentials": True
    }
})

# Load AI cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

# User isolation lock
user_locks = threading.Lock()
user_lock_dict = {}

def get_user_lock(user_id):
    with user_locks:
        if user_id not in user_lock_dict:
            user_lock_dict[user_id] = threading.Lock()
        return user_lock_dict[user_id]

# Pi Network Authentication Endpoints
@app.route('/auth/pi/url', methods=['GET'])
@limiter.limit("10000 per minute")
def get_pi_auth():
    """Get Pi Network OAuth URL"""
    state = secrets.token_urlsafe(16)
    auth_url = get_pi_auth_url(state)
    return jsonify({
        "success": True,
        "auth_url": auth_url,
        "state": state
    })

@app.route('/auth/pi/callback', methods=['POST'])
@limiter.limit("10000 per minute")
def pi_auth_callback():
    """Handle Pi Network OAuth callback"""
    try:
        data = request.get_json()
        if not data or 'code' not in data or 'state' not in data:
            return jsonify({"error": "Code and state required"}), 400
        
        # Exchange code for tokens
        token_data = exchange_code_for_token(data['code'])
        if not token_data:
            return jsonify({"error": "Failed to authenticate with Pi Network"}), 401
        
        # Get user info
        user_info = get_pi_user_info(token_data['access_token'])
        if not user_info:
            return jsonify({"error": "Failed to fetch user info"}), 401
        
        # Create or update user
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (pi_user_id, username, email, pi_access_token, pi_refresh_token, token_expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (pi_user_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        email = EXCLUDED.email,
                        pi_access_token = EXCLUDED.pi_access_token,
                        pi_refresh_token = EXCLUDED.pi_refresh_token,
                        token_expires_at = EXCLUDED.token_expires_at,
                        last_login = NOW()
                    RETURNING id, username, api_key
                """, (
                    user_info.get('uid'),
                    user_info.get('username'),
                    user_info.get('email'),
                    token_data['access_token'],
                    token_data.get('refresh_token'),
                    datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
                ))
                
                user = cur.fetchone()
                user_id, username, api_key = user
                
                # Generate a main API key for the user if they don't have one
                if not api_key:
                    api_key = secrets.token_hex(32)
                    cur.execute("UPDATE users SET api_key = %s WHERE id = %s", (api_key, user_id))
                
                conn.commit()
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "username": username,
            "pi_user_id": user_info.get('uid'),
            "api_key": api_key,
            "message": "Authentication successful"
        })
        
    except Exception as e:
        app.logger.error(f"Pi auth error: {str(e)}")
        return jsonify({"error": "Authentication failed"}), 500

# API Key Management Endpoints
@app.route('/api-keys', methods=['GET'])
@require_api_key
@limiter.limit("10000 per minute")
def list_api_keys():
    """Get user's API keys"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ak.api_key, ak.name, ak.permissions, ak.created_at, ak.expires_at, ak.is_active
                    FROM api_keys ak
                    WHERE ak.user_id = %s
                    ORDER BY ak.created_at DESC
                """, (request.user_id,))
                
                keys = []
                for row in cur.fetchall():
                    keys.append({
                        "api_key": row[0][:8] + "..." if row[5] else "********",
                        "name": row[1],
                        "permissions": row[2],
                        "created_at": row[3].isoformat() if row[3] else None,
                        "expires_at": row[4].isoformat() if row[4] else None,
                        "is_active": row[5]
                    })
                
                # Include main API key
                cur.execute("SELECT api_key FROM users WHERE id = %s", (request.user_id,))
                main_key = cur.fetchone()
                if main_key and main_key[0]:
                    keys.insert(0, {
                        "api_key": main_key[0][:8] + "...",
                        "name": "Main API Key",
                        "permissions": ["cells:execute", "api-keys:manage"],
                        "created_at": None,
                        "expires_at": None,
                        "is_active": True
                    })
        
        return jsonify({
            "success": True,
            "api_keys": keys
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api-keys', methods=['POST'])
@require_api_key
@limiter.limit("10000 per minute")
def create_api_key():
    """Create a new API key"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Key name required"}), 400
        
        name = data['name'].strip()
        permissions = data.get('permissions', ['cells:execute'])
        expires_days = data.get('expires_days')
        
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        new_api_key = secrets.token_hex(32)
        
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO api_keys (user_id, api_key, name, permissions, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING api_key, created_at, expires_at
                """, (request.user_id, new_api_key, name, json.dumps(permissions), expires_at))
                
                result = cur.fetchone()
                conn.commit()
        
        return jsonify({
            "success": True,
            "api_key": new_api_key,
            "name": name,
            "permissions": permissions,
            "created_at": result[1].isoformat(),
            "expires_at": result[2].isoformat() if result[2] else None,
            "warning": "Save this API key securely - it won't be shown again!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api-keys/<key_prefix>', methods=['DELETE'])
@require_api_key
@limiter.limit("10000 per minute")
def revoke_api_key(key_prefix):
    """Revoke an API key"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # For main API key
                if len(key_prefix) <= 8:
                    cur.execute("UPDATE users SET api_key = NULL WHERE id = %s AND api_key LIKE %s", 
                               (request.user_id, f"{key_prefix}%"))
                else:
                    # For managed API keys
                    cur.execute("UPDATE api_keys SET is_active = FALSE WHERE user_id = %s AND api_key LIKE %s", 
                               (request.user_id, f"{key_prefix}%"))
                
                if cur.rowcount == 0:
                    return jsonify({"error": "API key not found"}), 404
                
                conn.commit()
        
        return jsonify({"success": True, "message": "API key revoked"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Core API Endpoint
@app.route('/ai-api', methods=['POST'])
@limiter.limit("10000 per minute")
@require_api_key
def handle_request():
    try:
        # Check permissions
        if 'cells:execute' not in request.permissions:
            return jsonify({"error": "Insufficient permissions"}), 403
            
        request_data = request.json
        user_id = request.user_id
        session_id = request.headers.get('X-Session-Id', secrets.token_hex(16))
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})
        
        # Validate input
        if not cell_names or not isinstance(cell_names, list):
            return jsonify({"error": "Invalid cells parameter"}), 400
        
        # Get user-specific lock
        user_lock = get_user_lock(user_id)
        
        results = {}
        execution_times = {}
        
        with user_lock:
            for cell_name in cell_names:
                if cell_name not in ai_cells:
                    continue
                    
                try:
                    work_dir = f"/tmp/cell_{user_id}_{session_id}"
                    os.makedirs(work_dir, exist_ok=True)
                    
                    cell_input = input_data.get(cell_name, {})
                    cell_input['_user_context'] = {
                        'user_id': user_id,
                        'session_id': session_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    start_time = datetime.utcnow()
                    results[cell_name] = ai_cells[cell_name](cell_input)
                    exec_time = (datetime.utcnow() - start_time).total_seconds()
                    execution_times[cell_name] = exec_time
                    
                except Exception as e:
                    app.logger.error(f"Cell {cell_name} error for user {user_id}: {str(e)}")
                    results[cell_name] = {"error": str(e)}
                finally:
                    shutil.rmtree(work_dir, ignore_errors=True)
        
        # Log usage
        with get_db() as conn:
            with conn.cursor() as cur:
                for cell_name, exec_time in execution_times.items():
                    input_hash = hashlib.sha256(
                        str(input_data.get(cell_name, {})).encode()
                    ).hexdigest()
                    
                    cur.execute("""
                        INSERT INTO cell_usage 
                        (user_id, cell_name, input_hash, session_id, execution_time)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, cell_name, input_hash, session_id, exec_time))
                
                cur.execute("""
                    INSERT INTO user_sessions 
                    (session_id, user_id, ip_address, user_agent, last_active)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (session_id) 
                    DO UPDATE SET last_active = NOW()
                """, (session_id, user_id, request.remote_addr, request.headers.get('User-Agent')))
                
                conn.commit()
        
        return jsonify({
            "success": True,
            "results": results,
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "cell_count": len(results)
            }
        })
        
    except Exception as e:
        app.logger.error(f"API Error for user {getattr(request, 'user_id', 'unknown')}: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500

# Utility Endpoints
@app.route('/list-cells', methods=['GET'])
@limiter.limit("10000 per minute")
def list_cells():
    return jsonify({
        "success": True,
        "available_cells": list(ai_cells.keys()),
        "count": len(ai_cells)
    })

@app.route('/ping', methods=['GET'])
@limiter.limit("10000 per minute")
def ping():
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "cells_loaded": len(ai_cells),
        "version": "2.0.0"
    })

@app.route('/usage', methods=['GET'])
@require_api_key
@limiter.limit("10000 per minute")
def get_usage():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get user's cell usage stats
                cur.execute("""
                    SELECT cell_name, COUNT(*) as count, 
                    AVG(execution_time) as avg_time 
                    FROM cell_usage 
                    WHERE user_id = %s
                    GROUP BY cell_name
                    ORDER BY count DESC
                """, (request.user_id,))
                usage_stats = [
                    {"cell": row[0], "count": row[1], "avg_time": row[2]} 
                    for row in cur.fetchall()
                ]
                
                # Get session info
                cur.execute("""
                    SELECT session_id, created_at, last_active 
                    FROM user_sessions 
                    WHERE user_id = %s
                    ORDER BY last_active DESC
                    LIMIT 5
                """, (request.user_id,))
                sessions = [
                    {"session_id": row[0], "created": row[1], "last_active": row[2]}
                    for row in cur.fetchall()
                ]
        
        return jsonify({
            "success": True,
            "usage": usage_stats,
            "recent_sessions": sessions,
            "username": request.username
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/user/profile', methods=['GET'])
@require_api_key
@limiter.limit("10000 per minute")
def get_user_profile():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT username, pi_user_id, created_at, last_login
                    FROM users WHERE id = %s
                """, (request.user_id,))
                user = cur.fetchone()
                
                if not user:
                    return jsonify({"error": "User not found"}), 404
                
                cur.execute("""
                    SELECT COUNT(*) FROM cell_usage WHERE user_id = %s
                """, (request.user_id,))
                total_executions = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT COUNT(DISTINCT session_id) FROM user_sessions WHERE user_id = %s
                """, (request.user_id,))
                total_sessions = cur.fetchone()[0]
        
        return jsonify({
            "success": True,
            "profile": {
                "username": user[0],
                "pi_user_id": user[1],
                "member_since": user[2].isoformat(),
                "last_login": user[3].isoformat() if user[3] else None,
                "total_executions": total_executions,
                "total_sessions": total_sessions
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded"}), 429

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
