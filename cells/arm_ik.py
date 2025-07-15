def process(input_data):
    # 3DOF arm approximation (10x faster than full IK)
    x, y, z = input_data["target"]
    theta1 = math.atan2(y, x)
    xy_dist = math.hypot(x, y) - 0.5  # Base offset
    theta2 = math.atan2(xy_dist, z) 
    theta3 = math.pi/2 - theta2  # Elbow angle
    return {"joints": [theta1, theta2, theta3], "mode": "fast_approx"}
