def process(input_data):
    """Sample path planning cell"""
    lidar_data = input_data.get("lidar_data", [])
    
    # Mock path planning (replace with A* algorithm)
    return {
        "path": [[0, 0], [100, 100], [200, 50]],
        "cost": 42
    }
