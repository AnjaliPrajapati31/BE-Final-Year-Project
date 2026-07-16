def success(message, data=None):
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error(message):
    return {
        "success": False,
        "message": message,
    }
