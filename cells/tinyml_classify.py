import tensorflow as tf 
import numpy as np

# Initialize the interpreter
try:
    _interpreter = tf.lite.Interpreter(model_path="mobilenetv2_quant.tflite")
    _interpreter.allocate_tensors()
except Exception as e:
    raise ValueError(f"Failed to load model: {str(e)}")

# Get input and output details
input_details = _interpreter.get_input_details()
output_details = _interpreter.get_output_details()
print("Input details:", input_details)
print("Output details:", output_details)

def process(input_data):
    try:
        # Convert input to numpy array
        input_tensor = np.array(input_data, dtype=np.uint8)
        
        # Get expected input shape from model (typically [1, height, width, 3])
        expected_shape = input_details[0]['shape']
        print(f"Expected shape: {expected_shape}")
        
        # Resize input to match model expectations
        if input_tensor.ndim == 3:  # If input is [H,W,C]
            # Add batch dimension
            input_tensor = np.expand_dims(input_tensor, axis=0)
        
        # Check if we need to resize the spatial dimensions
        if (input_tensor.shape[1] != expected_shape[1] or 
            input_tensor.shape[2] != expected_shape[2]):
            print(f"Resizing input from {input_tensor.shape} to {expected_shape}")
            import cv2
            input_tensor = np.stack([
                cv2.resize(input_tensor[0,:,:,i], 
                          (expected_shape[2], expected_shape[1]))
                for i in range(3)
            ], axis=-1)
            input_tensor = np.expand_dims(input_tensor, axis=0)
        
        print(f"Final input shape: {input_tensor.shape}")
        
        # Verify input shape matches model expectation
        if input_tensor.shape != tuple(expected_shape):
            raise ValueError(f"Input shape {input_tensor.shape} doesn't match model expectation {expected_shape}")
        
        # Set input and run inference
        _interpreter.set_tensor(input_details[0]['index'], input_tensor)
        _interpreter.invoke()
        
        # Get output
        output = _interpreter.get_tensor(output_details[0]['index'])
        print(f"Raw output: {output}")
        
        if output.size == 0:
            raise ValueError("Model returned empty output")
            
        output = output[0]  # Get first batch if exists
        class_id = int(np.argmax(output))
        confidence = float(np.max(output))
        
        return {
            "class_id": class_id,
            "confidence": confidence,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }
