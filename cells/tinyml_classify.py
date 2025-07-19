# Quantized TensorFlow Lite model (50KB)
_interpreter = tf.lite.Interpreter(model_path="mobilenetv2_quant.tflite")
def process(input_data):
    input_tensor = np.array(input_data["image"], dtype=np.uint8)
    _interpreter.set_tensor(0, input_tensor)
    _interpreter.invoke()
    output = _interpreter.get_tensor(1)[0]
    return {"class_id": np.argmax(output), "confidence": float(np.max(output))}
