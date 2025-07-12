# Uses precomputed LUTs for 0.1° resolution
_sin_lut = [round(math.sin(math.radians(x))*1000) for x in range(0, 3600)]
def process(input_data):
    angle = input_data["angle"] % 360  # Degrees
    idx = int(angle * 10)  # 0.1° resolution
    return {"sin": _sin_lut[idx]/1000, "cos": _sin_lut[(idx + 900) % 3600]/1000}
