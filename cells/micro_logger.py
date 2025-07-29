import time

_LOG_BUFFER = []
def process(input_data):
    # Circular buffer with 8 entries
    _LOG_BUFFER.append({
        "t": time.time(),
        "event": input_data["event"],
        "value": round(input_data["value"], 2)
    })
    if len(_LOG_BUFFER) > 8:
        _LOG_BUFFER.pop(0)
    return {"logged": True, "buffer_size": len(_LOG_BUFFER)}
