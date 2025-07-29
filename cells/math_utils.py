import numpy as np

def fast_sqrt(x):
    x = np.float32(x)  # Ensure input is float32
    i = x.view(np.int32)  # Reinterpret bits as integer
    i = np.int32(0x5f3759df) - (i >> np.int32(1))
    y = i.view(np.float32)
    return y * (np.float32(1.5) - (np.float32(0.5) * x * y * y)
