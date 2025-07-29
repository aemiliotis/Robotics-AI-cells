_ERROR_DB = {
    0x01: "Motor driver fault - restart driver",
    0x02: "Low voltage - reduce speed by 30%"
}

def process(input_data):
    error_code = int(input_data["error_code"], 16)  # Convert hex string to integer
    solution = _ERROR_DB.get(error_code & 0xF0, "Check connections")
    return {
        "severity": (error_code >> 4) & 0x0F,
        "action": solution,
        "log_code": f"ERR{error_code:02X}"
    }
