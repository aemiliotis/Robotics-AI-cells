import os
import secrets
from functools import wraps
from flask import request, jsonify
from database import get_db

def generate_api_key():
    return secrets.token_hex(32)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
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
