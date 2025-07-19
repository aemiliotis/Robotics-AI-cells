_CACHE = {}

   def get_cache(key):
       return _CACHE.get(key)

   def set_cache(key, value, ttl=10):
       _CACHE[key] = (value, time.time() + ttl)
