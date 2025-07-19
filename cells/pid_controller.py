def process(input_data):
    """PID controller using Q15 fixed-point arithmetic"""
    try:
        # Fixed-point coefficients (Q15 format)
        Kp, Ki, Kd = 32768, 1638, 6553  # 1.0, 0.05, 0.2 in Q15
        
        # Convert inputs to fixed-point
        error = int(round(float(input_data["error"]) * 32768))
        last_error = int(round(float(input_data.get("last_error", 0)) * 32768))
        integral = int(round(float(input_data.get("integral", 0)) * 32768))
        
        # Calculate integral term with anti-windup
        new_integral = integral + error
        integral = min(max(new_integral, -2**31), 2**31-1)  # 32-bit clamping
        
        # Calculate derivative term
        derivative = error - last_error
        
        # Calculate PID output (using integer arithmetic)
        output = (Kp * error + Ki * integral + Kd * derivative) // 32768  # Use floor division instead of >>
        
        # Convert back to floating point
        return {
            "output": float(output) / 32768.0,
            "integral": float(integral) / 32768.0,
            "last_error": float(error) / 32768.0
        }
        
    except (KeyError, ValueError) as e:
        # Handle missing or invalid input data
        return {
            "output": 0.0,
            "integral": 0.0,
            "last_error": 0.0,
            "error": f"Invalid input: {str(e)}"
        }
