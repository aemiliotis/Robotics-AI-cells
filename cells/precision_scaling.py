def scale_precision(arr, factor=100):
       """Convert floats to scaled integers"""
       return (np.array(arr) * factor).astype(np.int16)
