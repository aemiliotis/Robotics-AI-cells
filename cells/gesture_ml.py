# Edge Impulse model (20KB)
_GESTURES = ["stop", "move", "rotate"]
def process(input_data):
    features = extract_imu_features(input_data["accel"], input_data["gyro"])
    pred = _model.predict([features])[0]
    return {"gesture": _GESTURES[np.argmax(pred)], "confidences": pred.tolist()}
