def process(input_data):
    # Simple insolation model
    month = input_data["month"]
    latitude = input_data["lat"]
    peak_hours = max(0, 4.5 - abs(latitude/20 - month*0.2))
    return {
        "charge_hours": peak_hours,
        "recommended_usage": 0.8*peak_hours*input_data["panel_w"]
