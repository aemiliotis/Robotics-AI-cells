from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import psycopg2
from datetime import datetime, timedelta
import hashlib
import shutil
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import redis
import jwt
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ALGORITHM'] = 'HS256'

# Rate limiting with Redis
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=6379,
    decode_responses=True
)

limiter = Limiter(
    app=app,
    key_func=lambda: request.headers.get('X-API-Key'),
    storage_uri="redis://localhost:6379",
    strategy="fixed-window"
)

def get_db():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

# Database setup
def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            # Create tables if they don't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(256) NOT NULL,
                    api_key VARCHAR(64) UNIQUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP
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
        
            conn.commit()
        conn.close()

# JWT Authentication
def generate_jwt(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])

def verify_jwt(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

# Authentication decorators
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
            
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username FROM users WHERE api_key = %s
                """, (api_key,))
                user = cur.fetchone()
                
                if not user:
                    return jsonify({"error": "Invalid API key"}), 401
                
                # Update last active time
                cur.execute("""
                    UPDATE users SET last_login = NOW() WHERE id = %s
                """, (user[0],))
                conn.commit()
                
                request.user_id = user[0]
                request.username = user[1]
        
        return f(*args, **kwargs)
    return decorated_function

# CORS Configuration
CORS(app, resources={
    r"/ai-api": {
        "origins": [
            "https://aemiliotis.github.io",
            "https://aemiliotis.github.io/Robotics-AI-Cells",
            "http://localhost:*"
        ],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Session-ID"],
        "supports_credentials": True
    },
    r"/register": {
        "origins": [
            "https://aemiliotis.github.io",
            "https://aemiliotis.github.io/Robotics-AI-Cells",
            "http://localhost:*"
        ],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": False
    },
    r"/usage": {
        "origins": [
            "https://aemiliotis.github.io",
            "https://aemiliotis.github.io/Robotics-AI-Cells", 
            "http://localhost:*"
        ],
        "methods": ["GET", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"],
        "supports_credentials": True,
        "max_age": 600  # Cache preflight response for 10 minutes
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

# Core API Endpoint
@app.route('/ai-api', methods=['POST'])
@limiter.limit("10 per second")
@require_api_key
def handle_request():
    try:
        request_data = request.json
        user_id = request.user_id
        session_id = request.headers.get('X-Session-ID', secrets.token_hex(16))
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
                    # Create isolated workspace
                    work_dir = f"/tmp/cell_{user_id}_{session_id}"
                    os.makedirs(work_dir, exist_ok=True)
                    
                    # Prepare input with context
                    cell_input = input_data.get(cell_name, {})
                    cell_input['_user_context'] = {
                        'user_id': user_id,
                        'session_id': session_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Execute cell with timing
                    start_time = datetime.utcnow()
                    results[cell_name] = ai_cells[cell_name](cell_input, work_dir)
                    exec_time = (datetime.utcnow() - start_time).total_seconds()
                    execution_times[cell_name] = exec_time
                    
                except Exception as e:
                    app.logger.error(f"Cell {cell_name} error for user {user_id}: {str(e)}")
                    results[cell_name] = {"error": str(e)}
                finally:
                    # Clean up workspace
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
                
                # Update session activity
                cur.execute("""
                    INSERT INTO user_sessions 
                    (session_id, user_id, ip_address, user_agent, last_active)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (session_id) 
                    DO UPDATE SET last_active = NOW()
                """, (
                    session_id,
                    user_id,
                    request.remote_addr,
                    request.headers.get('User-Agent')
                ))
                
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

# User Management Endpoints
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password required"}), 400
        
        username = data['username'].strip()
        password = data['password']
        
        if len(username) < 4 or len(password) < 8:
            return jsonify({"error": "Username (min 4) and password (min 8) length requirements"}), 400
        
        password_hash = generate_password_hash(password)
        api_key = secrets.token_hex(32)
        
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO users 
                    (username, password_hash, api_key) 
                    VALUES (%s, %s, %s) 
                    RETURNING id""",
                    (username, password_hash, api_key)
                )
                user_id = cur.fetchone()[0]
                conn.commit()
        
        return jsonify({
            "success": True,
            "api_key": api_key,
            "user_id": user_id,
            "message": "Account created. Keep your API key secure!"
        })
        
    except psycopg2.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    except Exception as e:
        return jsonify({
            "error": "Registration failed",
            "message": str(e)
        }), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password required"}), 400
        
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, password_hash FROM users WHERE username = %s",
                    (data['username'],)
                )
                user = cur.fetchone()
                
                if not user or not check_password_hash(user[1], data['password']):
                    return jsonify({"error": "Invalid credentials"}), 401
                
                # Generate new API key on login
                new_api_key = secrets.token_hex(32)
                cur.execute(
                    "UPDATE users SET api_key = %s, last_login = NOW() WHERE id = %s",
                    (new_api_key, user[0])
                )
                conn.commit()
        
        return jsonify({
            "success": True,
            "api_key": new_api_key,
            "user_id": user[0]
        })
        
    except Exception as e:
        return jsonify({
            "error": "Login failed",
            "message": str(e)
        }), 500

@app.route('/logout', methods=['POST'])
@require_api_key
def logout():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET api_key = NULL WHERE id = %s",
                    (request.user_id,)
                )
                conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Utility Endpoints
@app.route('/list-cells', methods=['GET'])
def list_cells():
    return jsonify({
        "success": True,
        "available_cells": list(ai_cells.keys()),
        "count": len(ai_cells)
    })

@app.route('/ping', methods=['GET'])
def ping():
    return _corsify_response(jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "cells_loaded": len(ai_cells)
    }))

@app.route('/usage', methods=['GET'])
@require_api_key  # Your existing auth decorator
@limiter.limit("5/minute")  # Rate limiting
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
            "recent_sessions": sessions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper functions
def _build_cors_preflight_response():
    response = jsonify({"message": "Preflight Accepted"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

def _corsify_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# Initialize database and run app
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
