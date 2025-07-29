import time

_CACHE = {}

def get_cache(key):
    cached = _CACHE.get(key)
    if cached is None:
        return None
        
    value, expiration = cached
    if time.time() > expiration:
        del _CACHE[key]  # Remove expired item
        return None
        
    return value

def set_cache(key, value, ttl=10):
    _CACHE[key] = (value, time.time() + ttl)
