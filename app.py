from flask import Flask, request, jsonify
from cell_loader import load_cells
import os

app = Flask(__name__)

# Load all cells at startup
CELLS_DIR = os.path.join(os.path.dirname(__file__), "cells")
ai_cells = load_cells(CELLS_DIR)

@app.route('/ai-api', methods=['POST'])
def handle_request():
    try:
        data = request.json
        results = {}
        
        # Execute requested cells
        for cell_name in data.get("cells", []):
            if cell_name in ai_cells:
                results[cell_name] = ai_cells[cell_name](data)
        
        return jsonify({
            "success": True,
            "results": results,
            "available_cells": list(ai_cells.keys())
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/list-cells', methods=['GET'])
def list_cells():
    """Endpoint to see available cells"""
    return jsonify({
        "available_cells": list(ai_cells.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
