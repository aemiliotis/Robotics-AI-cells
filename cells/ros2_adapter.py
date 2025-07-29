import time
def process(input_data):
    # Converts between your API and ROS2 messages
    return {
        "ros2_header": {
            "stamp": {"sec": int(time.time()), "nanosec": 0},
            "frame_id": input_data.get("frame", "base_link")
        },
        "twist": {
            "linear": {"x": input_data["vel_x"], "y": 0, "z": 0},
            "angular": {"z": input_data["ang_vel"]}
        }
    }
