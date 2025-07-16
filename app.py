from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS
import sqlite3
import secrets
import hashlib
import datetime
import re
from functools import wraps
import uuid

app = Flask(__name__)
CORS(app, resources={
    r"/ai-api": {
        "origins": ["https://aemiliotis.github.io/Robotics-AI-cells", "http://localhost:*"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Key"]
    },
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Key"]
    }
})

# Load cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

# Database setup
DATABASE_PATH = 'api_management.db'

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # API Keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT UNIQUE NOT NULL,
            secret_key TEXT NOT NULL,
            email TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            usage_count INTEGER DEFAULT 0,
            rate_limit INTEGER DEFAULT 1000,
            description TEXT
        )
    ''')
    
    # Usage logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            cell_name TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN,
            error_message TEXT,
            input_data TEXT,
            execution_time REAL,
            ip_address TEXT,
            FOREIGN KEY (api_key) REFERENCES api_keys (api_key)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

def generate_api_key():
    """Generate a secure API key"""
    return f"rai_{secrets.token_urlsafe(32)}"

def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_urlsafe(48)

def hash_secret(secret_key):
    """Hash the secret key for storage"""
    return hashlib.sha256(secret_key.encode()).hexdigest()

def validate_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_api_key_info(api_key):
    """Get API key information from database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT api_key, secret_key, email, name, is_active, usage_count, rate_limit
        FROM api_keys 
        WHERE api_key = ? AND is_active = 1
    ''', (api_key,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'api_key': result[0],
            'secret_key': result[1],
            'email': result[2],
            'name': result[3],
            'is_active': result[4],
            'usage_count': result[5],
            'rate_limit': result[6]
        }
    return None

def log_usage(api_key, cell_name, success, error_message=None, input_data=None, execution_time=None, ip_address=None):
    """Log API usage"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO usage_logs (api_key, cell_name, success, error_message, input_data, execution_time, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (api_key, cell_name, success, error_message, str(input_data), execution_time, ip_address))
    
    # Update usage count and last used
    cursor.execute('''
        UPDATE api_keys 
        SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
        WHERE api_key = ?
    ''', (api_key,))
    
    conn.commit()
    conn.close()

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key required. Include X-API-Key header."
            }), 401
        
        key_info = get_api_key_info(api_key)
        if not key_info:
            return jsonify({
                "success": False,
                "error": "Invalid API key"
            }), 401
        
        # Check rate limit (simple daily limit)
        if key_info['usage_count'] >= key_info['rate_limit']:
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded"
            }), 429
        
        # Add key info to request context
        request.api_key_info = key_info
        return f(*args, **kwargs)
    
    return decorated_function

# CORS helper functions
def _build_cors_preflight_response():
    response = jsonify({"message": "Preflight Accepted"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

def _corsify_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# API Management Endpoints

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register_api_key():
    """Register a new API key"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.json
        email = data.get('email')
        name = data.get('name', '')
        description = data.get('description', '')
        
        # Validate input
        if not email or not validate_email(email):
            return _corsify_response(jsonify({
                "success": False,
                "error": "Valid email address required"
            })), 400
        
        # Check if email already exists
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT api_key FROM api_keys WHERE email = ?', (email,))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return _corsify_response(jsonify({
                "success": False,
                "error": "Email already registered"
            })), 409
        
        # Generate keys
        api_key = generate_api_key()
        secret_key = generate_secret_key()
        secret_hash = hash_secret(secret_key)
        
        # Store in database
        cursor.execute('''
            INSERT INTO api_keys (api_key, secret_key, email, name, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (api_key, secret_hash, email, name, description))
        
        conn.commit()
        conn.close()
        
        return _corsify_response(jsonify({
            "success": True,
            "api_key": api_key,
            "secret_key": secret_key,
            "message": "API key created successfully. Store your secret key securely - it won't be shown again."
        }))
    
    except Exception as e:
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e)
        })), 500

@app.route('/api/validate', methods=['POST', 'OPTIONS'])
def validate_api_key():
    """Validate an API key"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.json
        api_key = data.get('api_key')
        
        if not api_key:
            return _corsify_response(jsonify({
                "success": False,
                "error": "API key required"
            })), 400
        
        key_info = get_api_key_info(api_key)
        if not key_info:
            return _corsify_response(jsonify({
                "success": False,
                "error": "Invalid API key"
            })), 401
        
        return _corsify_response(jsonify({
            "success": True,
            "valid": True,
            "email": key_info['email'],
            "name": key_info['name'],
            "usage_count": key_info['usage_count'],
            "rate_limit": key_info['rate_limit']
        }))
    
    except Exception as e:
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e)
        })), 500

@app.route('/api/usage', methods=['GET', 'OPTIONS'])
@require_api_key
def get_usage_stats():
    """Get usage statistics for the authenticated API key"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        api_key = request.api_key_info['api_key']
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get recent usage
        cursor.execute('''
            SELECT cell_name, COUNT(*) as count, 
                   AVG(execution_time) as avg_time,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM usage_logs 
            WHERE api_key = ? AND timestamp > datetime('now', '-7 days')
            GROUP BY cell_name
            ORDER BY count DESC
        ''', (api_key,))
        
        usage_stats = []
        for row in cursor.fetchall():
            usage_stats.append({
                'cell_name': row[0],
                'count': row[1],
                'avg_execution_time': row[2],
                'success_count': row[3],
                'success_rate': (row[3] / row[1]) * 100 if row[1] > 0 else 0
            })
        
        conn.close()
        
        return _corsify_response(jsonify({
            "success": True,
            "usage_stats": usage_stats,
            "total_usage": request.api_key_info['usage_count'],
            "rate_limit": request.api_key_info['rate_limit']
        }))
    
    except Exception as e:
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e)
        })), 500

# Enhanced cell execution endpoint with API key support
@app.route('/api/execute', methods=['POST', 'OPTIONS'])
@require_api_key
def execute_cells_api():
    """Execute cells with API key authentication"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    start_time = datetime.datetime.now()
    
    try:
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})
        
        if not cell_names:
            return _corsify_response(jsonify({
                "success": False,
                "error": "No cells specified"
            })), 400
        
        results = {}
        
        for cell_name in cell_names:
            cell_start_time = datetime.datetime.now()
            
            if cell_name in ai_cells:
                try:
                    cell_input = input_data.get(cell_name, {})
                    results[cell_name] = ai_cells[cell_name](cell_input)
                    
                    # Log successful execution
                    execution_time = (datetime.datetime.now() - cell_start_time).total_seconds()
                    log_usage(
                        request.api_key_info['api_key'],
                        cell_name,
                        True,
                        None,
                        cell_input,
                        execution_time,
                        request.remote_addr
                    )
                    
                except Exception as cell_error:
                    # Log failed execution
                    execution_time = (datetime.datetime.now() - cell_start_time).total_seconds()
                    log_usage(
                        request.api_key_info['api_key'],
                        cell_name,
                        False,
                        str(cell_error),
                        input_data.get(cell_name, {}),
                        execution_time,
                        request.remote_addr
                    )
                    
                    results[cell_name] = {
                        "error": str(cell_error)
                    }
            else:
                results[cell_name] = {
                    "error": f"Cell '{cell_name}' not found"
                }
        
        total_time = (datetime.datetime.now() - start_time).total_seconds()
        
        return _corsify_response(jsonify({
            "success": True,
            "results": results,
            "execution_time": total_time,
            "timestamp": datetime.datetime.now().isoformat()
        }))
    
    except Exception as e:
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e)
        })), 500

# Original endpoints (maintained for backward compatibility)
@app.route('/ai-api', methods=['POST', 'OPTIONS'])
def handle_request():
    """Original endpoint - maintained for backward compatibility"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})
        
        results = {}
        
        for cell_name in cell_names:
            if cell_name in ai_cells:
                cell_input = input_data.get(cell_name, {})
                results[cell_name] = ai_cells[cell_name](cell_input)
        
        return _corsify_response(jsonify({
            "success": True,
            "results": results
        }))
    
    except Exception as e:
        app.logger.error(f"API Error: {str(e)}")
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e)
        })), 500

@app.route('/list-cells', methods=['GET', 'OPTIONS'])
def list_cells():
    """Endpoint to see available cells"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    cell_info = {}
    for cell_name in ai_cells.keys():
        # You can expand this to include more cell metadata
        cell_info[cell_name] = {
            "name": cell_name,
            "available": True
        }
    
    return _corsify_response(jsonify({
        "success": True,
        "available_cells": list(ai_cells.keys()),
        "cell_info": cell_info,
        "total_cells": len(ai_cells)
    }))

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return _corsify_response(jsonify({
        "status": "alive",
        "cells": list(ai_cells.keys()),
        "timestamp": datetime.datetime.now().isoformat()
    }))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
