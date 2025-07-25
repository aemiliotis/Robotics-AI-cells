from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import psycopg2
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)

# Database Configuration
def get_db():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            # Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key VARCHAR(64) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Sessions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    session_id VARCHAR(64) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_active TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Cell usage tracking with sessions
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cell_usage (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    session_id VARCHAR(64),
                    cell_name VARCHAR(100) NOT NULL,
                    executed_at TIMESTAMP DEFAULT NOW()
                );
            """)
            conn.commit()

# Auth Utilities
def generate_api_key():
    return secrets.token_hex(32)

def generate_session_id():
    return secrets.token_urlsafe(32)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
            
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE api_key = %s", (api_key,))
                user = cur.fetchone()
                if not user:
                    return jsonify({"error": "Invalid API key"}), 403
                request.user_id = user[0]
        return f(*args, **kwargs)
    return decorated

def require_active_session(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.headers.get('X-Session-ID')
        api_key = request.headers.get('X-API-Key')
        
        if not session_id or not api_key:
            return jsonify({"error": "Session credentials required"}), 401
            
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify session and update last active
                cur.execute("""
                    SELECT u.id FROM users u
                    JOIN sessions s ON u.id = s.user_id
                    WHERE u.api_key = %s AND s.session_id = %s
                    AND s.last_active > NOW() - INTERVAL '1 hour'
                    FOR UPDATE
                    """, (api_key, session_id))
                user = cur.fetchone()
                
                if not user:
                    return jsonify({"error": "Invalid or expired session"}), 403
                
                # Update last active time
                cur.execute("""
                    UPDATE sessions 
                    SET last_active = NOW() 
                    WHERE session_id = %s
                    """, (session_id,))
                conn.commit()
                
                request.user_id = user[0]
                request.session_id = session_id
        return f(*args, **kwargs)
    return decorated

# Initialize app
init_db()
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

# CORS Configuration
CORS(app, resources={
    r"/.*": {
        "origins": [
            "https://aemiliotis.github.io",
            "http://localhost:*"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Session-ID"],
        "supports_credentials": True
    }
})

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'https://aemiliotis.github.io'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# API Endpoints
@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password required"}), 400

        password_hash = generate_password_hash(data['password'])
        api_key = generate_api_key()

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash, api_key) VALUES (%s, %s, %s) RETURNING id",
                    (data['username'], password_hash, api_key)
                )
                conn.commit()

        return jsonify({
            "success": True,
            "api_key": api_key,
            "message": "Keep your API key secure!"
        }), 201
    
    except psycopg2.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/register-session', methods=['POST', 'OPTIONS'])
@require_api_key
def register_session():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"error": "Session ID required"}), 400

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sessions (user_id, session_id)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id) 
                    DO UPDATE SET last_active = NOW()
                    RETURNING id
                    """, (request.user_id, session_id))
                conn.commit()
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ai-api', methods=['POST', 'OPTIONS'])
@require_active_session
def handle_request():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})
        
        results = {}
        
        with get_db() as conn:
            with conn.cursor() as cur:
                # Lock user row for atomic operations
                cur.execute("SELECT 1 FROM users WHERE id = %s FOR UPDATE", (request.user_id,))
                
                for cell_name in cell_names:
                    if cell_name in ai_cells:
                        cell_input = input_data.get(cell_name, {})
                        results[cell_name] = ai_cells[cell_name](cell_input)
                        
                        # Track usage with session
                        cur.execute(
                            "INSERT INTO cell_usage (user_id, session_id, cell_name) VALUES (%s, %s, %s)",
                            (request.user_id, request.session_id, cell_name)
                        )
                
                conn.commit()
        
        return jsonify({
            "success": True,
            "results": results
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/logout', methods=['POST', 'OPTIONS'])
@require_active_session
def logout():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Invalidate session
                cur.execute(
                    "DELETE FROM sessions WHERE session_id = %s",
                    (request.session_id,)
                )
                conn.commit()
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/session-heartbeat', methods=['POST', 'OPTIONS'])
@require_active_session
def session_heartbeat():
    return jsonify({"success": True})

@app.route('/list-cells', methods=['GET', 'OPTIONS'])
def list_cells():
    """Endpoint to see available cells"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    return _corsify_response(jsonify({
        "success": True,
        "available_cells": list(ai_cells.keys())
    }))

# backend/app.py - Add this test endpoint
@app.route('/ping', methods=['GET'])
def ping():
    return _corsify_response(jsonify({
        "status": "alive",
        "cells": list(ai_cells.keys())
    }))

# Helper functions
def _build_cors_preflight_response():
    response = jsonify({"message": "Preflight Accepted"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
