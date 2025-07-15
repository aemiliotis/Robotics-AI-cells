import cv2
import numpy as np

def process(input_data):
    """Lightweight object detection"""
    img_data = input_data.get("image")
    if not img_data:
        return {"error": "No image data"}
    
    # Convert to grayscale (saves 75% processing)
    if isinstance(img_data, list):
        img = np.array(img_data, dtype=np.uint8)
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Ultra-light edge detection (vs full CNN)
    edges = cv2.Canny(img, 50, 150)
    
    # Fast blob detection
    params = cv2.SimpleBlobDetector_Params()
    params.filterByArea = True
    params.minArea = 100
    detector = cv2.SimpleBlobDetector_create(params)
    keypoints = detector.detect(edges)
    
    return {
        "objects": len(keypoints),
        "keypoints": [{"x": k.pt[0], "y": k.pt[1]} for k in keypoints],
        "processing_time_ms": cv2.getTickCount() * 1000 / cv2.getTickFrequency()
    }
