from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={
    r"/ai-api": {
        "origins": ["https://aemiliotis.github.io/Robotics-AI-cells", "http://localhost:*"],
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
        request_data = request.json
        cell_names = request_data.get("cells", [])
        input_data = request_data.get("data", {})  # Changed from direct data access
        
        results = {}
        
        for cell_name in cell_names:
            if cell_name in ai_cells:
                # Pass only the relevant portion of input data
                cell_input = input_data.get(cell_name, {})
                results[cell_name] = ai_cells[cell_name](cell_input)  # Changed from passing full data
        
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
