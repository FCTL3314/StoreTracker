from typing import Optional

from django.core.cache import cache


def get_cached_data_or_set_new(key: str, callback: callable, timeout: int) -> Optional:
    """
    Checks if the cache exists for the given key. If not present,
    it caches the data obtained from calling the callback function
    for timeout seconds.
    """
    data = cache.get(key)
    if not data:
        data = callback()
        cache.set(key, data, timeout)
    return data
