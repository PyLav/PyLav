def remove_keys(*keys, data: dict) -> dict:
    for key in keys:
        data.pop(key, None)
    return data
