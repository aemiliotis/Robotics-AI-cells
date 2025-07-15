from functools import wraps
from flask import request, jsonify
from models import APIKey, APILog, db
from datetime import datetime

def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        secret_key = request.headers.get('X-SECRET-KEY')
        
        if not api_key or not secret_key:
            return jsonify({
                "success": False,
                "error": "API key and secret key required"
            }), 401
        
        key = APIKey.query.filter_by(
            api_key=api_key,
            secret_key=secret_key,
            is_active=True
        ).first()
        
        if not key:
            return jsonify({
                "success": False,
                "error": "Invalid API credentials"
            }), 403
            
        # Log the request
        log = APILog(
            api_key_id=key.id,
            endpoint=request.path,
            ip_address=request.remote_addr,
            request_data=request.json if request.method == 'POST' else None
        )
        db.session.add(log)
        
        # Update last used
        key.last_used = datetime.utcnow()
        db.session.commit()
        
        # Attach the key to the request for later use
        request.api_key = key
        
        return f(*args, **kwargs)
    return decorated_function
