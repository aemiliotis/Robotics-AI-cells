def fast_sqrt(x):
       # Quake III inverse sqrt approximation
       i = np.int32(x)
       i = 0x5f3759df - (i >> 1)
       y = np.float32(i)
       return y * (1.5 - 0.5 * x * y * y)
