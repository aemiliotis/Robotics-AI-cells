from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS
from auth_utils import require_api_key, generate_api_key
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import psycopg2

# Initialize after app creation
app = Flask(__name__)
init_db()

CORS(app, resources={
    r"/ai-api": {
        "origins": [
            "https://aemiliotis.github.io",
            "https://aemiliotis.github.io/Robotics-AI-Cells",
            "http://localhost:*"
        ],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"],
        "supports_credentials": True
    },
    r"/register": {  # Explicit CORS for registration
        "origins": [
            "https://aemiliotis.github.io",
            "https://aemiliotis.github.io/Robotics-AI-Cells",
            "http://localhost:*"
        ],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/list-cells": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"]
    }
})

# Load cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

@app.route('/ai-api', methods=['POST', 'OPTIONS'])
@require_api_key
def handle_request():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})  # Changed from direct data access
        
        results = {}
        
        for cell_name in cell_names:
            if cell_name in ai_cells:
                # Pass only the relevant portion of input data
                cell_input = input_data.get(cell_name, {})
                results[cell_name] = ai_cells[cell_name](cell_input)  # Changed from passing full data

        with get_db() as conn:
            with conn.cursor() as cur:
                for cell_name in cell_names:
                    cur.execute(
                        "INSERT INTO cell_usage (user_id, cell_name) VALUES (%s, %s)",
                        (request.user_id, cell_name)
                    )
                conn.commit()
        
        return _corsify_response(jsonify({
            "success": True,
            "results": results
        }))
    
    except Exception as e:
        app.logger.error(f"API Error: {str(e)}")  # Added logging
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e),
            "received_data": request_data  # For debugging
        })), 500

# NEW CORS support functions
def _build_cors_preflight_response():
    response = jsonify({"message": "Preflight Accepted"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

def _corsify_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password required"}), 400

        # Generate secure password hash
        password_hash = generate_password_hash(data['password'])
        api_key = secrets.token_hex(32)

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash, api_key) VALUES (%s, %s, %s) RETURNING id",
                    (data['username'], password_hash, api_key)
                )
                conn.commit()

        response = jsonify({
            "success": True,
            "api_key": api_key,
            "message": "Keep your API key secure!"
        })
        response.headers.add('Access-Control-Allow-Origin', 'https://aemiliotis.github.io')
        return response

    except psycopg2.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    except Exception as e:
        error_response = jsonify({
            "error": str(e),
            "message": "Registration failed"
        })
        error_response.status_code = 500
        error_response.headers.add('Access-Control-Allow-Origin', 'https://aemiliotis.github.io')
        return error_response

@app.route('/logout', methods=['POST', 'OPTIONS'])
@require_api_key
def logout():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Invalidate the API key
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET api_key = NULL WHERE api_key = %s",
                    (request.headers.get('X-API-Key'),)
                )
                conn.commit()
        
        return _corsify_response(jsonify({
            "success": True,
            "message": "Logged out successfully"
        }))
    
    except Exception as e:
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e)
        })), 500

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
