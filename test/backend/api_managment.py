from flask import Blueprint, request, jsonify
from models import User, APIKey, db
from auth import api_key_required
import datetime

api_management = Blueprint('api_management', __name__)

@api_management.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return _corsify_response(jsonify({"success": False, "error": "Email and password required"})), 400
        
        if User.query.filter_by(email=email).first():
            return _corsify_response(jsonify({"success": False, "error": "Email already registered"})), 400
        
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return _corsify_response(jsonify({
            "success": True,
            "message": "User registered successfully"
        }))
    
    except Exception as e:
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e)
        })), 500

@api_management.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid credentials"}), 401
    
    # Find or create a default API key for the user
    api_key = APIKey.query.filter_by(user_id=user.id).first()
    if not api_key:
        keys = APIKey.generate_keys()
        api_key = APIKey(
            user_id=user.id,
            api_key=keys['api_key'],
            secret_key=keys['secret_key'],
            name="Default Key",
            description="Automatically generated key"
        )
        db.session.add(api_key)
        db.session.commit()
    
    return jsonify({
        "success": True,
        "api_key": api_key.api_key,
        "secret_key": api_key.secret_key,
        "user": {
            "email": user.email,
            "is_admin": user.is_admin
        }
    })

@api_management.route('/create-api-key', methods=['POST'])
@api_key_required
def create_api_key():
    data = request.json
    user = request.api_key.user
    
    keys = APIKey.generate_keys()
    new_key = APIKey(
        user_id=user.id,
        api_key=keys['api_key'],
        secret_key=keys['secret_key'],
        name=data.get('name', 'New API Key'),
        description=data.get('description', ''),
        allowed_cells=data.get('allowed_cells', [])
    )
    
    db.session.add(new_key)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "api_key": keys['api_key'],
        "secret_key": keys['secret_key'],
        "message": "API key created successfully. Store these securely as they won't be shown again."
    })

@api_management.route('/list-keys', methods=['GET'])
@api_key_required
def list_keys():
    user = request.api_key.user
    keys = APIKey.query.filter_by(user_id=user.id).all()
    
    return jsonify({
        "success": True,
        "keys": [{
            "id": k.id,
            "name": k.name,
            "created_at": k.created_at.isoformat(),
            "last_used": k.last_used.isoformat() if k.last_used else None,
            "is_active": k.is_active,
            "rate_limit": k.rate_limit,
            "allowed_cells": k.allowed_cells
        } for k in keys]
    })

@api_management.route('/revoke-key/<int:key_id>', methods=['POST'])
@api_key_required
def revoke_key(key_id):
    user = request.api_key.user
    key = APIKey.query.filter_by(id=key_id, user_id=user.id).first()
    
    if not key:
        return jsonify({"success": False, "error": "Key not found"}), 404
    
    key.is_active = False
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "API key revoked"
    })
