from flask import Flask, request, jsonify, g, session
from flask_cors import CORS
from cell_loader import load_cells
import os
import time
import json
import traceback
import psycopg2
from datetime import timedelta
from functools import wraps
from database import (
    get_user_by_email, create_user, verify_password, update_last_login,
    create_api_key, get_api_keys_by_user, get_api_key_details,
    update_api_key_usage, deactivate_api_key, log_api_usage
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')  # Change in production

# Configure CORS
CORS(app, resources={
    r"/ai-api": {
        "origins": ["https://aemiliotis.github.io", "https://aemiliotis.github.io/Robotics-AI-cells", "http://localhost:*"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    },
    r"/list-cells": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"]
    },
    r"/auth/*": {
        "origins": ["https://aemiliotis.github.io", "https://aemiliotis.github.io/Robotics-AI-cells", "http://localhost:*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    },
    r"/api-keys/*": {
        "origins": ["https://aemiliotis.github.io", "https://aemiliotis.github.io/Robotics-AI-cells", "http://localhost:*"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Session configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1)
)
    
# Load cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

# Authentication decorator for web session (browser)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

# API key authentication decorator
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"success": False, "error": "API key required"}), 401
        
        api_key_details = get_api_key_details(api_key)
        if not api_key_details:
            return jsonify({"success": False, "error": "Invalid or inactive API key"}), 401
        
        # Store API key details for the request
        g.api_key_id = api_key_details['id']
        g.user_id = api_key_details['user_id']
        
        return f(*args, **kwargs)
    return decorated_function

# CORS support functions
def _build_cors_preflight_response():
    response = jsonify({"message": "Preflight Accepted"})
    request_origin = request.headers.get('Origin')
    if request_origin in [
        "https://aemiliotis.github.io",
        "http://localhost:*",
        "https://aemiliotis.github.io/Robotics-AI-cells"
    ]:
        response.headers.add("Access-Control-Allow-Origin", request_origin)
        response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
    return response

def _corsify_response(response):
    # Get the origin from the request
    request_origin = request.headers.get('Origin')
    if request_origin in [
        "https://aemiliotis.github.io",
        "http://localhost:*",
        "https://aemiliotis.github.io/Robotics-AI-cells"
    ]:
        response.headers.add("Access-Control-Allow-Origin", request_origin)
        response.headers.add("Access-Control-Allow-Credentials", "true")
    return response
    
# Authentication endpoints
@app.route('/auth/register', methods=['POST'])
def register():
    try:
        if not request.is_json:
            return jsonify({"error": "JSON required"}), 400
            
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400
        
        # Check existing user
        if get_user_by_email(email):
            return jsonify({"error": "Email already registered"}), 409
        
        # Create user
        user = create_user(email, password)
        
        # Create initial API key
        api_key = create_api_key(user['id'], "Default Key")
        
        # Set session
        session['user_id'] = user['id']
        session['email'] = user['email']
        
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "email": user['email']
            },
            "api_key": {  # Include API key data
                "key": api_key['api_key'],
                "secret": api_key['secret_key']
            }
        })
        
    except Exception as e:
        app.logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500
        
@app.route('/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Validate request format
        if not request.is_json:
            app.logger.error("Login attempt with non-JSON request")
            return _corsify_response(jsonify({
                "success": False,
                "error": "Request must be JSON"
            })), 400

        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')

        # Validate inputs
        if not email or not password:
            app.logger.warning(f"Missing credentials in login attempt (email: {bool(email)}, password: {bool(password)})")
            return _corsify_response(jsonify({
                "success": False,
                "error": "Email and password are required"
            })), 400

        # Debug logging
        app.logger.info(f"Login attempt for email: {email}")

        # Get user from database
        user = get_user_by_email(email)
        if not user:
            app.logger.warning(f"No user found for email: {email}")
            return _corsify_response(jsonify({
                "success": False,
                "error": "Invalid credentials"
            })), 401

        # Handle both tuple and dict responses
        if isinstance(user, dict):
            user_id = user.get('id')
            password_hash = user.get('password_hash')
            user_email = user.get('email')
        else:  # Assume tuple
            user_id = user[0]
            password_hash = user[2]  # Adjust index based on your schema
            user_email = user[1]

        # Verify password
        if not password_hash or not verify_password(password_hash, password):
            app.logger.warning(f"Password verification failed for user: {email}")
            return _corsify_response(jsonify({
                "success": False,
                "error": "Invalid credentials"
            })), 401

        # Establish session
        session.clear()
        session['user_id'] = user_id
        session['email'] = user_email
        session.permanent = True
        update_last_login(user_id)

        app.logger.info(f"Successful login for user: {email}")

        response = _corsify_response(jsonify({
            "success": True,
            "user": {
                "id": user_id,
                "email": user_email
            }
        }))
        
        return response

    except Exception as e:
        app.logger.error(f"Critical login error: {str(e)}\n{traceback.format_exc()}")
        return _corsify_response(jsonify({
            "success": False,
            "error": "An unexpected error occurred"
        })), 500

@app.route('/auth/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    session.clear()
    return _corsify_response(jsonify({
        "success": True
    }))

@app.route('/auth/status', methods=['GET'])
def status():
    if 'user_id' not in session:
        return _corsify_response(jsonify({
            "success": True,
            "authenticated": False
        }))
    
    return _corsify_response(jsonify({
        "success": True,
        "authenticated": True,
        "user": {
            "id": session['user_id'],
            "email": session.get('email')
        }
    }))

# API key management endpoints
@app.route('/api-keys', methods=['GET', 'OPTIONS'])
@login_required
def get_api_keys():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    user_id = session['user_id']
    keys = get_api_keys_by_user(user_id)
    
    return _corsify_response(jsonify({
        "success": True,
        "api_keys": keys
    }))

@app.route('/api-keys', methods=['POST', 'OPTIONS'])
@login_required
def create_new_api_key():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    user_id = session['user_id']
    data = request.json
    name = data.get('name', 'API Key')
    
    api_key = create_api_key(user_id, name)
    
    return _corsify_response(jsonify({
        "success": True,
        "api_key": api_key
    }))

@app.route('/api-keys/<key_id>', methods=['DELETE', 'OPTIONS'])
@login_required
def delete_api_key(key_id):
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    user_id = session['user_id']
    success = deactivate_api_key(key_id, user_id)
    
    if success:
        return _corsify_response(jsonify({
            "success": True
        }))
    else:
        return _corsify_response(jsonify({
            "success": False,
            "error": "Failed to delete API key"
        })), 404

# AI Cell API endpoints
@app.route('/ai-api', methods=['POST', 'OPTIONS'])
@api_key_required
def handle_request():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    start_time = time.time()
    
    try:
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})
        
        results = {}
        
        for cell_name in cell_names:
            if cell_name in ai_cells:
                cell_input = input_data.get(cell_name, {})
                results[cell_name] = ai_cells[cell_name](cell_input)
        
        response_data = {
            "success": True,
            "results": results
        }
        
        # Log API usage
        execution_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        log_api_usage(
            g.api_key_id,
            '/ai-api',
            json.dumps(request_data),
            json.dumps(response_data),
            execution_time,
            200
        )
        
        # Update API key usage timestamp
        update_api_key_usage(g.api_key_id)
        
        return _corsify_response(jsonify(response_data))
    
    except Exception as e:
        app.logger.error(f"API Error: {str(e)}")
        
        response_data = {
            "success": False,
            "error": str(e)
        }
        
        # Log API usage with error
        execution_time = int((time.time() - start_time) * 1000)
        log_api_usage(
            g.api_key_id,
            '/ai-api',
            json.dumps(request.json if request.is_json else {}),
            json.dumps(response_data),
            execution_time,
            500
        )
        
        return _corsify_response(jsonify(response_data)), 500

@app.route('/list-cells', methods=['GET', 'OPTIONS'])
@api_key_required
def list_cells():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    start_time = time.time()
    
    response_data = {
        "success": True,
        "available_cells": list(ai_cells.keys())
    }
    
    # Log API usage
    execution_time = int((time.time() - start_time) * 1000)
    log_api_usage(
        g.api_key_id,
        '/list-cells',
        '',
        json.dumps(response_data),
        execution_time,
        200
    )
    
    # Update API key usage timestamp
    update_api_key_usage(g.api_key_id)
    
    return _corsify_response(jsonify(response_data))

@app.route('/ping', methods=['GET'])
def ping():
    return _corsify_response(jsonify({
        "status": "alive",
        "cells": list(ai_cells.keys())
    }))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
