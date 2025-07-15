_MOTOR_PARAMS = {
    "maxon_ec45": {"kt": 0.042, "r": 2.3, "i_no_load": 0.1}
}
def process(input_data):
    # I = (V - kt*ω)/R + i_no_load
    params = _MOTOR_PARAMS[input_data["motor_type"]]
    voltage = input_data["voltage"]
    rpm = input_data["rpm"]
    current = (voltage - params["kt"]*rpm)/params["r"] + params["i_no_load"]
    return {"current_a": round(current, 2), "warn": current > 2.0}
