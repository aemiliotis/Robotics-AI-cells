def li_ion_degradation_model(cycles, dod, temp):
    """Simplified degradation model (0.1% CPU of full ECMS)"""
    return 0.003 * cycles * (dod/100) * (2 ** ((temp-25)/10))

def process(input_data):
    """Predicts battery health and suggests optimal usage"""
    cycles = input_data.get("charge_cycles", 50)
    dod = input_data.get("avg_dod", 80)  # Depth of discharge
    temp = input_data.get("avg_temp", 30)  # Celsius
    
    degradation = li_ion_degradation_model(cycles, dod, temp)
    remaining_capacity = max(0, 100 - degradation)
    
    # Load balancing suggestion
    suggestion = "normal"
    if remaining_capacity < 80:
        suggestion = "reduce_max_speed_20%"
    elif remaining_capacity < 60:
        suggestion = "disable_secondary_systems"
    
    return {
        "battery_health": f"{remaining_capacity:.1f}%",
        "suggestion": suggestion,
        "critical": remaining_capacity < 50
    }
