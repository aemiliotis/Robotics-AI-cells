def process(input_data):
    # Uses 16-bit fixed-point math (Q15 format)
    Kp, Ki, Kd = 32768, 1638, 6553  # 1.0, 0.05, 0.2 in Q15
    error = int(input_data["error"] * 32768)
    integral = min(2**31-1, input_data.get("integral", 0) + error)
    derivative = error - input_data.get("last_error", 0)
    output = (Kp*error + Ki*integral + Kd*derivative) >> 15
    return {"output": output/32768, "integral": integral, "last_error": error}
