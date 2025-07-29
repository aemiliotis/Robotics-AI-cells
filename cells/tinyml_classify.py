import tensorflow as tf 
import numpy as np

# Quantized TensorFlow Lite model (50KB)
_interpreter = tf.lite.Interpreter(model_path="mobilenetv2_quant.tflite")
_interpreter.allocate_tensors()  # Allocate tensors

# Get input and output details (optional, for debugging)
input_details = _interpreter.get_input_details()
output_details = _interpreter.get_output_details()
print("Input details:", input_details)
print("Output details:", output_details)

def process(input_data):
    # Get input tensor and ensure it's the correct shape/type
    input_tensor = np.array(input_data["image"], dtype=np.uint8)
    
    # Verify input shape matches model expectation
    if input_tensor.shape != tuple(input_details[0]['shape']):
        raise ValueError(f"Input shape {input_tensor.shape} doesn't match model expectation {input_details[0]['shape']}")
    
    _interpreter.set_tensor(input_details[0]['index'], input_tensor)
    _interpreter.invoke()
    output = _interpreter.get_tensor(output_details[0]['index'])[0]
    
    return {"class_id": int(np.argmax(output)), "confidence": float(np.max(output))}
