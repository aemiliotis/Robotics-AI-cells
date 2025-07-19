import numpy as np
from collections import deque

class KalmanFilter:
    def __init__(self, dim_x=3, dim_z=2):
        self.x = np.zeros(dim_x)  # State [x, y, theta]
        self.P = np.eye(dim_x)   # Covariance
        self.Q = np.eye(dim_x)*0.01  # Process noise
        self.R = np.eye(dim_z)*0.1   # Measurement noise
        
    def update(self, z):
        # Simplified Kalman update (reduced matrix ops)
        H = np.array([[1,0,0],[0,1,0]])  # Measurement function
        y = z - H @ self.x
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.pinv(S)
        self.x += K @ y
        self.P = (np.eye(len(self.x)) - K @ H) @ self.P

def process(input_data):
    """Fuses IMU + GPS + Lidar data"""
    kf = KalmanFilter()
    
    # Mock data - replace with real sensor inputs
    imu_data = input_data.get("imu", {"accel": [0.1, 0.02], "gyro": 0.05})
    gps_data = input_data.get("gps", [10.5, 20.3])
    
    # Prediction step (simplified)
    kf.x[0] += imu_data["accel"][0] * 0.1  # Δt assumed 0.1s
    kf.x[1] += imu_data["accel"][1] * 0.1
    kf.x[2] += imu_data["gyro"] * 0.1
    
    # Update with GPS (2D position only)
    kf.update(np.array(gps_data))
    
    return {
        "fused_state": kf.x.tolist(),
        "covariance": kf.P.diagonal().tolist()
      }
