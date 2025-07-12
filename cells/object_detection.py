import cv2
import numpy as np

def process(input_data):
    """Sample object detection cell"""
    # input_data contains whatever the frontend sends
    image_data = input_data.get("image_data")
    
    # Mock detection (replace with real model)
    return {
        "objects": [
            {"label": "robot", "x": 100, "y": 150, "confidence": 0.95},
            {"label": "box", "x": 200, "y": 50, "confidence": 0.87}
        ]
    }
