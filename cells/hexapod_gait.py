_GAIT_PATTERNS = {
    "tripod": [(1,0,1,0,1,0), (0,1,0,1,0,1)],  # Binary leg states
    "wave": [(1,0,0,0,0,0), (0,1,0,0,0,0), ...]
}
def process(input_data):
    gait = _GAIT_PATTERNS[input_data.get("gait", "tripod")]
    phase = input_data["step_count"] % len(gait)
    return {"leg_commands": gait[phase], "next_phase": (phase+1)%len(gait)}
