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

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Application starting up...")

# Configure CORS
logger.info("Configuring CORS settings...")
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
logger.info("CORS configuration complete")

# Session configuration
logger.info("Configuring session settings...")
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1)
)
logger.info("Session configuration complete")

# Load cells
logger.info("Loading AI cells...")
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)
logger.info(f"Loaded {len(ai_cells)} AI cells")

# Authentication decorator for web session (browser)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"Checking login requirement for {request.path}")
        if 'user_id' not in session:
            logger.warning("Unauthorized access attempt - no user_id in session")
            return jsonify({"success": False, "error": "Authentication required"}), 401
        logger.info(f"User {session['user_id']} authorized for {request.path}")
        return f(*args, **kwargs)
    return decorated_function

# API key authentication decorator
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"Validating API key for {request.path}")
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            logger.warning("API key missing from request")
            return jsonify({"success": False, "error": "API key required"}), 401
        
        api_key_details = get_api_key_details(api_key)
        if not api_key_details:
            logger.warning(f"Invalid API key attempt: {api_key}")
            return jsonify({"success": False, "error": "Invalid or inactive API key"}), 401
        
        # Store API key details for the request
        g.api_key_id = api_key_details['id']
        g.user_id = api_key_details['user_id']
        logger.info(f"API key validated for user {g.user_id}")
        
        return f(*args, **kwargs)
    return decorated_function

# CORS support functions
def _build_cors_preflight_response():
    logger.debug("Building CORS preflight response")
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
    logger.debug("CORSifying response")
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
    logger.info("Registration request received")
    try:
        if not request.is_json:
            logger.warning("Registration attempt with non-JSON request")
            return jsonify({"error": "JSON required"}), 400
            
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        logger.debug(f"Registration attempt for email: {email}")
        
        if not email or not password:
            logger.warning("Missing email or password in registration")
            return jsonify({"error": "Email and password required"}), 400
        
        # Check existing user
        if get_user_by_email(email):
            logger.warning(f"Registration attempt with existing email: {email}")
            return jsonify({"error": "Email already registered"}), 409
        
        # Create user
        logger.info(f"Creating new user: {email}")
        user = create_user(email, password)
        
        # Create initial API key
        logger.info(f"Creating API key for new user: {user['id']}")
        api_key = create_api_key(user['id'], "Default Key")
        
        # Set session
        session['user_id'] = user['id']
        session['email'] = user['email']
        logger.info(f"User {user['id']} registered and logged in successfully")
        
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "email": user['email']
            },
            "api_key": {
                "key": api_key['api_key'],
                "secret": api_key['secret_key']
            }
        })
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Registration failed"}), 500
        
@app.route('/auth/login', methods=['POST', 'OPTIONS'])
def login():
    logger.info("Login request received")
    if request.method == 'OPTIONS':
        logger.debug("Login OPTIONS preflight request")
        return _build_cors_preflight_response()
    
    try:
        # Validate request format
        if not request.is_json:
            logger.warning("Login attempt with non-JSON request")
            return _corsify_response(jsonify({
                "success": False,
                "error": "Request must be JSON"
            })), 400

        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        logger.debug(f"Login attempt for email: {email}")

        # Validate inputs
        if not email or not password:
            logger.warning(f"Missing credentials in login attempt (email: {bool(email)}, password: {bool(password)})")
            return _corsify_response(jsonify({
                "success": False,
                "error": "Email and password are required"
            })), 400

        # Get user from database
        logger.debug(f"Looking up user: {email}")
        user = get_user_by_email(email)
        if not user:
            logger.warning(f"No user found for email: {email}")
            return _corsify_response(jsonify({
                "success": False,
                "error": "Invalid credentials"
            })), 401

        # Handle both tuple and dict responses
        if isinstance(user, dict):
            user_id = user.get('id')
            password_hash = user.get('password_hash')
            user_email = user.get('email')
        else:
            user_id = user[0]
            password_hash = user[2]
            user_email = user[1]

        # Verify password
        if not password_hash or not verify_password(password_hash, password):
            logger.warning(f"Password verification failed for user: {email}")
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
        logger.info(f"Successful login for user: {email}")

        response = _corsify_response(jsonify({
            "success": True,
            "user": {
                "id": user_id,
                "email": user_email
            }
        }))
        
        return response

    except Exception as e:
        logger.error(f"Critical login error: {str(e)}\n{traceback.format_exc()}")
        return _corsify_response(jsonify({
            "success": False,
            "error": "An unexpected error occurred"
        })), 500

@app.route('/auth/logout', methods=['POST', 'OPTIONS'])
def logout():
    logger.info("Logout request received")
    if request.method == 'OPTIONS':
        logger.debug("Logout OPTIONS preflight request")
        return _build_cors_preflight_response()
    
    user_id = session.get('user_id', 'unknown')
    session.clear()
    logger.info(f"User {user_id} logged out successfully")
    return _corsify_response(jsonify({
        "success": True
    }))

@app.route('/auth/status', methods=['GET'])
def status():
    logger.info("Auth status check request received")
    try:
        if 'user_id' not in session:
            logger.debug("No active session found")
            return _corsify_response(jsonify({
                "success": True,
                "authenticated": False
            }))
        
        logger.info(f"Active session found for user {session['user_id']}")
        return _corsify_response(jsonify({
            "success": True,
            "authenticated": True,
            "user": {
                "id": session['user_id'],
                "email": session.get('email')
            }
        }))
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}\n{traceback.format_exc()}")
        return _corsify_response(jsonify({
            "success": False,
            "error": "Error checking authentication status"
        })), 500

# API key management endpoints
@app.route('/api-keys', methods=['GET', 'OPTIONS'])
@login_required
def get_api_keys():
    logger.info("API keys list request received")
    if request.method == 'OPTIONS':
        logger.debug("API keys OPTIONS preflight request")
        return _build_cors_preflight_response()
    
    user_id = session['user_id']
    logger.debug(f"Fetching API keys for user {user_id}")
    keys = get_api_keys_by_user(user_id)
    logger.info(f"Found {len(keys)} API keys for user {user_id}")
    
    return _corsify_response(jsonify({
        "success": True,
        "api_keys": keys
    }))

@app.route('/api-keys', methods=['POST', 'OPTIONS'])
@login_required
def create_new_api_key():
    logger.info("API key creation request received")
    if request.method == 'OPTIONS':
        logger.debug("API key creation OPTIONS preflight request")
        return _build_cors_preflight_response()
    
    user_id = session['user_id']
    data = request.json
    name = data.get('name', 'API Key')
    logger.info(f"Creating new API key for user {user_id} with name: {name}")
    
    api_key = create_api_key(user_id, name)
    logger.info(f"API key created successfully for user {user_id}")
    
    return _corsify_response(jsonify({
        "success": True,
        "api_key": api_key
    }))

@app.route('/api-keys/<key_id>', methods=['DELETE', 'OPTIONS'])
@login_required
def delete_api_key(key_id):
    logger.info(f"API key deletion request received for key {key_id}")
    if request.method == 'OPTIONS':
        logger.debug("API key deletion OPTIONS preflight request")
        return _build_cors_preflight_response()
    
    user_id = session['user_id']
    logger.info(f"Attempting to delete key {key_id} for user {user_id}")
    success = deactivate_api_key(key_id, user_id)
    
    if success:
        logger.info(f"Successfully deleted API key {key_id}")
        return _corsify_response(jsonify({
            "success": True
        }))
    else:
        logger.warning(f"Failed to delete API key {key_id}")
        return _corsify_response(jsonify({
            "success": False,
            "error": "Failed to delete API key"
        })), 404

# AI Cell API endpoints
@app.route('/ai-api', methods=['POST', 'OPTIONS'])
@api_key_required
def handle_request():
    logger.info("AI API request received")
    start_time = time.time()
    
    try:
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})
        logger.debug(f"Processing request for cells: {cell_names}")
        
        results = {}
        
        for cell_name in cell_names:
            if cell_name in ai_cells:
                logger.debug(f"Executing cell: {cell_name}")
                cell_input = input_data.get(cell_name, {})
                results[cell_name] = ai_cells[cell_name](cell_input)
            else:
                logger.warning(f"Requested cell not found: {cell_name}")
        
        response_data = {
            "success": True,
            "results": results
        }
        
        # Log API usage
        execution_time = int((time.time() - start_time) * 1000)
        log_api_usage(
            g.api_key_id,
            '/ai-api',
            json.dumps(request_data),
            json.dumps(response_data),
            execution_time,
            200
        )
        logger.info(f"Request processed successfully in {execution_time}ms")
        
        # Update API key usage timestamp
        update_api_key_usage(g.api_key_id)
        
        return _corsify_response(jsonify(response_data))
    
    except Exception as e:
        logger.error(f"API Error: {str(e)}\n{traceback.format_exc()}")
        
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
    logger.info("List cells request received")
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
    logger.info(f"List cells request processed in {execution_time}ms")
    
    # Update API key usage timestamp
    update_api_key_usage(g.api_key_id)
    
    return _corsify_response(jsonify(response_data))

@app.route('/ping', methods=['GET'])
def ping():
    logger.info("Ping request received")
    return _corsify_response(jsonify({
        "status": "alive",
        "cells": list(ai_cells.keys())
    }))

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
