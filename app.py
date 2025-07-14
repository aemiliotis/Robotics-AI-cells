from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={
    r"/ai-api": {
        "origins": ["https://aemiliotis.github.com", "http://localhost:*"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/list-cells": {
        "origins": "*",  # More open for listing
        "methods": ["GET", "OPTIONS"]
    }
})
# Load cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

@app.route('/ai-api', methods=['POST', 'OPTIONS'])
def handle_request():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        data = request.json
        if not data or 'cells' not in data:
            raise ValueError("Missing 'cells' in request")
            
        # NEW: Structured input handling
        input_data = data.get('data', {})
        results = {}
        
        for cell_name in data["cells"]:
            if cell_name not in ai_cells:
                raise ValueError(f"Invalid cell: {cell_name}")
                
            # NEW: Pass only relevant data to each cell
            cell_input = input_data.get(cell_name, {})
            results[cell_name] = ai_cells[cell_name](cell_input)
        
        return _corsify_response(jsonify({
            "success": True,
            "results": results
        }))
    
    except Exception as e:
        # Enhanced error logging
        app.logger.error(f"API Error: {str(e)}")
        return _corsify_response(jsonify({
            "success": False,
            "error": str(e),
            "request_data": request.json  # For debugging
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
