from flask import Flask, request, jsonify, g, session
from flask_cors import CORS
from cell_loader import load_cells
import os
import time
import json
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
@app.route('/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required"
            }), 400
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            return jsonify({
                "success": False,
                "error": "Email already registered"
            }), 409
        
        # Create new user
        user = create_user(email, password)
        if not user:
            return jsonify({
                "success": False,
                "error": "Failed to create user"
            }), 500
        
        # Create initial API key
        api_key = create_api_key(user['id'], "Default Key")
        
        # Set session
        session['user_id'] = user['id']
        session['email'] = user['email']
        
        response = jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "email": user['email']
            },
            "api_key": {
                "api_key": api_key['api_key'],
                "secret_key": api_key['secret_key']
            }
        })
        
        return _corsify_response(response)
    
    except Exception as e:
        app.logger.error(f"Registration error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500
        
@app.route('/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return _corsify_response(jsonify({
            "success": False,
            "error": "Email and password are required"
        })), 400
    
    # Check if user exists
    user = get_user_by_email(email)
    if not user or not verify_password(user['password_hash'], password):
        return _corsify_response(jsonify({
            "success": False,
            "error": "Invalid email or password"
        })), 401
    
    # Update last login
    update_last_login(user['id'])
    
    # Set session
    session['user_id'] = user['id']
    session['email'] = user['email']
    
    return _corsify_response(jsonify({
        "success": True,
        "user": {
            "id": user['id'],
            "email": user['email']
        }
    }))

@app.route('/auth/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    session.clear()
    return _corsify_response(jsonify({
        "success": True
    }))

@app.route('/auth/status', methods=['GET', 'OPTIONS'])
def status():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    if 'user_id' in session:
        return _corsify_response(jsonify({
            "success": True,
            "authenticated": True,
            "user": {
                "id": session['user_id'],
                "email": session['email']
            }
        }))
    else:
        return _corsify_response(jsonify({
            "success": True,
            "authenticated": False
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
