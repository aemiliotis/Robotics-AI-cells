def process(input_data):
    # Validate and convert temperature (-12.8°C to 12.7°C)
    temp_int = int(input_data["temp"] * 10)
    if not -128 <= temp_int <= 127:
        raise ValueError("Temperature out of range")
    temp = temp_int.to_bytes(1, 'big', signed=True)
    
    # Validate and convert humidity (0% to 100%)
    hum_int = int(input_data["humidity"])
    if not 0 <= hum_int <= 255:
        raise ValueError("Humidity out of range")
    hum = hum_int.to_bytes(1, 'big')
    
    # Validate and convert acceleration (-327.68 to 327.67 m/s²)
    accel_int = int(input_data["accel_x"] * 100)
    if not -32768 <= accel_int <= 32767:
        raise ValueError("Acceleration out of range")
    accel = accel_int.to_bytes(2, 'big', signed=True)
    
    # Validate and convert battery voltage (0V to 25.5V)
    bat_int = int(input_data["battery"] * 10)
    if not 0 <= bat_int <= 255:
        raise ValueError("Battery voltage out of range")
    bat = bat_int.to_bytes(1, 'big')
    
    return {"lora_packet": temp + hum + accel + bat}
