# Кэш для хранения результатов парсинга
cache = {}

def get_from_cache(key):
    return cache.get(key)

def save_to_cache(key, value):
    cache[key] = value
