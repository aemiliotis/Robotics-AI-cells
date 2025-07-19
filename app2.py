from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from cell_loader import load_cells
import os
from datetime import datetime
import secrets

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={
    r"/ai-api": {
        "origins": ["https://aemiliotis.github.io", "http://localhost:*"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/api/*": {  # Add this for all API management routes
        "origins": ["https://aemiliotis.github.io", "http://localhost:*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-KEY", "X-SECRET-KEY"]
    },
    r"/list-cells": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"]
    },
    r"/ping": {
        "origins": "*",
        "methods": ["GET"]
    }
})


# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///api_keys.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

db = SQLAlchemy(app)

# Import models and routes after db initialization
from models import User, APIKey, APILog
from auth import api_key_required
import api_management

# Register blueprints
app.register_blueprint(api_management.api_management, url_prefix='/api')

# Load AI cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

@app.route('/ai-api', methods=['POST', 'OPTIONS'])
@api_key_required
def handle_request():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})
        
        # Check if user is allowed to access these cells
        allowed_cells = request.api_key.allowed_cells or []
        if allowed_cells:  # If empty list, allow all
            for cell_name in cell_names:
                if cell_name not in allowed_cells:
                    return _corsify_response(jsonify({
                        "success": False,
                        "error": f"Not authorized to access cell: {cell_name}"
                    })), 403
        
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
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    return _corsify_response(jsonify({
        "success": True,
        "available_cells": list(ai_cells.keys())
    }))

@app.route('/ping', methods=['GET'])
def ping():
    return _corsify_response(jsonify({
        "status": "alive",
        "cells": list(ai_cells.keys())
    }))

def _build_cors_preflight_response():
    response = jsonify({"message": "Preflight Accepted"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

def _corsify_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
