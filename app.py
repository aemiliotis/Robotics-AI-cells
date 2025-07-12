from flask import Flask, request, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes  # NEW

# Load cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

@app.route('/ai-api', methods=['POST', 'OPTIONS'])  # Added OPTIONS
def handle_request():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()  # NEW
    
    try:
        data = request.json
        results = {}
        
        for cell_name in data.get("cells", []):
            if cell_name in ai_cells:
                results[cell_name] = ai_cells[cell_name](data)
        
        return _corsify_response(jsonify({  # NEW
            "success": True,
            "results": results
        }))
    
    except Exception as e:
        return _corsify_response(jsonify({  # NEW
            "success": False,
            "error": str(e)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
