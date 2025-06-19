import json
import os
from datetime import datetime

def load_cache():
    """Загружает кэш из файла."""
    try:
        if os.path.exists("cache.json"):
            with open("cache.json", "r") as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_cache(cache):
    """Сохраняет кэш в файл."""
    try:
        with open("cache.json", "w") as f:
            json.dump(cache, f, indent=4)
    except Exception as e:
        print(f"{datetime.now()}: Ошибка при сохранении кэша: {e}")