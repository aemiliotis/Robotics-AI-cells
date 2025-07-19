def process(input_data):
    # Feature tracking between 2 frames (FAST + optical flow)
    prev_pts = input_data["prev_keypoints"]
    curr_pts = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
    )
    return {"delta_x": np.mean(dx), "delta_y": np.mean(dy)}
