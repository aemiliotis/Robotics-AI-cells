def process(input_data):
    # Pack sensor data into single 12-byte message:
    # [1:temp][2:hum][4:accel_x][2:bat][3:status]
    temp = int(input_data["temp"] * 10).to_bytes(1, 'big', signed=True)
    hum = int(input_data["humidity"]).to_bytes(1, 'big')
    accel = int(input_data["accel_x"] * 100).to_bytes(2, 'big', signed=True)
    bat = int(input_data["battery"] * 10).to_bytes(1, 'big')
    return {"lora_packet": temp + hum + accel + bat}
