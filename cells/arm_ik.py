import math

def process(input_data):
    """
    3DOF Inverse Kinematics Solver (Frontend-Compatible Version)
    Accepts either:
    - {'target': [x, y, z]} (direct API calls)
    - {'target_x': x, 'target_y': y, 'target_z': z} (web interface format)
    
    Returns: {'joints': [theta1, theta2, theta3], 'mode': 'fast_approx'}
    """
    
    # Input handling - support both formats
    try:
        if 'target' in input_data:
            # Direct API call format
            x, y, z = map(float, input_data['target'][:3])
        else:
            # Web interface format (target_x, target_y, target_z)
            x = float(input_data.get('target_x', 0))
            y = float(input_data.get('target_y', 0))
            z = float(input_data.get('target_z', 0))
            
        # Validate input coordinates
        if not all(isinstance(v, (int, float)) for v in (x, y, z)):
            raise ValueError("All target components must be numeric")
            
    except (KeyError, ValueError, TypeError) as e:
        return {
            'error': f'Invalid target input: {str(e)}',
            'received_data': input_data,
            'success': False
        }

    # Safety check - prevent division by zero in atan2 calculations
    if x == 0 and y == 0:
        return {
            'error': 'Target directly above base (x=0, y=0) causes singularity',
            'success': False
        }

    try:
        # 3DOF arm approximation calculations
        theta1 = math.atan2(y, x)  # Base rotation
        
        xy_dist = math.hypot(x, y) - 0.5  # Base offset adjustment
        theta2 = math.atan2(xy_dist, z)  # Shoulder angle
        
        theta3 = math.pi/2 - theta2  # Elbow angle (fixed relative to shoulder)
        
        # Joint limit safety check
        joints = [theta1, theta2, theta3]
        if not all(-math.pi <= angle <= math.pi for angle in joints):
            return {
                'error': 'Calculated joint angles exceed ±π limits',
                'joints': joints,
                'success': False
            }
            
        return {
            'joints': joints,
            'mode': 'fast_approx',
            'success': True
        }
        
    except Exception as e:
        return {
            'error': f'IK calculation failed: {str(e)}',
            'success': False
        }


# Test cases that work with both input formats
if __name__ == "__main__":
    # Web interface format test
    web_format = {
        'target_x': 0.5,
        'target_y': 0.2,
        'target_z': 0.8
    }
    print("Web format result:", process(web_format))
    
    # Direct API format test
    api_format = {
        'target': [0.5, 0.2, 0.8]
    }
    print("API format result:", process(api_format))
    
    # Error case test
    error_format = {
        'target_x': 'invalid',
        'target_y': 0.2,
        'target_z': 0.8
    }
    print("Error case result:", process(error_format))
