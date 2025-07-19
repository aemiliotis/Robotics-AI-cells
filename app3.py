from flask import Flask, requests, jsonify
from cell_loader import load_cells
import os
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={
    r"/ai-api": {
        "origins": ["https://*.github.io", "https://*.github.io/*", "http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/list-cells": {
        "origins": "*",
        "methods": ["GET", "OPTIONS"]
    }
    r"/ping": {
    "origins": "*",
    "methods": ["GET"]
}
})

# Load cells
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/ai-api', methods=['POST', 'OPTIONS'])
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
