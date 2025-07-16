# backend/app.py
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import functools
from flask_cors import CORS
from cell_loader import load_cells

app = Flask(__name__)
CORS(app, resources={
    r"/ai-api": {
        "origins": ["https://aemiliotis.github.io/Robotics-AI-cells", "http://localhost:*"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"]  # Allow X-API-Key
    },
    r"/list-cells": {
        "origins": "*",  # More open for listing
        "methods": ["GET", "OPTIONS"]
    },
    r"/register": {
        "origins": "*",
        "methods": ["POST", "OPTIONS"]
    }
})

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Use SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Cell Loading
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

# Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    api_key = db.Column(db.String(36), unique=True, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

# API Key Validation Decorator
def require_api_key(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return _corsify_response(jsonify({"success": False, "error": "API key is missing"})), 401

        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return _corsify_response(jsonify({"success": False, "error": "Invalid API key"})), 401

        return f(*args, **kwargs)
    return decorated_function

# Registration Endpoint
@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')  # Get password from request

    if not email or not password:
        return _corsify_response(jsonify({"success": False, "error": "Email and password are required"})), 400

    if User.query.filter_by(email=email).first():
        return _corsify_response(jsonify({"success": False, "error": "Email already registered"})), 400

    api_key = secrets.token_hex(18)  # 36 characters

    new_user = User(email=email, api_key=api_key)
    new_user.set_password(password)  # Hash the password
    db.session.add(new_user)
    db.session.commit()

    return _corsify_response(jsonify({
        "success": True,
        "message": "User registered successfully",
        "api_key": api_key  # Return the API key
    })), 201

# AI API Endpoint (Protected)
@app.route('/ai-api', methods=['POST', 'OPTIONS'])
@require_api_key  # Apply the API key validation
def handle_request():
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
            "error": str(e),
            "received_data": request_data
        })), 500

# CORS support functions
def _build_cors_preflight_response():
    response = jsonify({"message": "Preflight Accepted"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response

def _corsify_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables
    app.run(host='0.0.0.0', port=5000, debug=True)
