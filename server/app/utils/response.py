def success(message, data=None):
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error(message, code=None, request_id=None):
    payload = {
        "success": False,
        "message": message,
    }
    if code:
        payload["error"] = {"code": code, "request_id": request_id}
    return payload
