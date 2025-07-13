from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS
import time
from typing import Dict, Any

app = Flask(__name__)

# Configure CORS properly
CORS(app)

#CORS(app, resources={
    #r"/ai-api": {"origins": "*", "methods": ["POST", "OPTIONS"]},
    #r"/list-cells": {"origins": "*", "methods": ["GET", "OPTIONS"]},
    #r"/ping": {"origins": "*"}
#})

# Constants
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB
RATE_LIMIT = 60  # Requests per minute

# Load cells with error handling
try:
    CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
    ai_cells = load_cells(CELLS_DIR)
except Exception as e:
    print(f"⚠️ Critical: Failed to load AI cells: {e}")
    ai_cells = {}

# Middleware for security and performance
@app.before_request
def before_request():
    # Rate limiting
    client_ip = request.remote_addr
    current_minute = int(time.time() / 60)
    
    # Payload size check
    if request.content_length and request.content_length > MAX_PAYLOAD_SIZE:
        return jsonify({"error": "Payload too large"}), 413

@app.route('/ai-api', methods=['POST', 'OPTIONS'])
def handle_request():
    """Main AI processing endpoint"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    try:
        # Input validation
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data: Dict[str, Any] = request.get_json()
        if not isinstance(data.get("cells"), list):
            return jsonify({"error": "Invalid cells format"}), 400

        # Process cells
        results = {}
        for cell_name in data["cells"]:
            if cell_name not in ai_cells:
                continue
            try:
                results[cell_name] = ai_cells[cell_name](data)
            except Exception as e:
                results[cell_name] = {"error": str(e)}

        return jsonify({
            "success": True,
            "results": results,
            "timestamp": time.time(),
            "processed_cells": list(results.keys())
        })

    except Exception as e:
        app.logger.error(f"API error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "request_id": request.headers.get("X-Request-ID")
        }), 500

@app.route('/list-cells', methods=['GET'])
def list_cells():
    """Cell discovery endpoint"""
    return jsonify({
        "success": True,
        "cells": list(ai_cells.keys()),
        "count": len(ai_cells)
    })

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy" if ai_cells else "degraded",
        "loaded_cells": len(ai_cells),
        "server_time": time.time()
    })

def _build_cors_preflight_response():
    """Proper CORS headers for preflight requests"""
    response = jsonify({"status": "preflight_ok"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    response.headers.add("Access-Control-Max-Age", "86400")  # 24 hours
    return response

if __name__ == '__main__':
    # Production configuration
    app.run(
        host='0.0.0.0',
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        threaded=True
    )
