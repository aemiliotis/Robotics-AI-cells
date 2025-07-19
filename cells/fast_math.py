import math
import numpy as np

# Precompute LUT with 0.1° resolution (3600 points)
_SIN_LUT = [math.sin(math.radians(angle/10)) for angle in range(0, 3600)]
_COS_LUT = [math.cos(math.radians(angle/10)) for angle in range(0, 3600)]

def process(input_data):
    """Returns sin/cos with 0.1° precision using precomputed LUTs"""
    angle_deg = input_data["angle"] % 360.0  # Normalize to [0,360)
    idx = int(round(angle_deg * 10)) % 3600  # Convert to LUT index
    
    return {
        "sin": _SIN_LUT[idx],
        "cos": _COS_LUT[idx],
        "precision_deg": 0.1,
        "method": "LUT"
    }
