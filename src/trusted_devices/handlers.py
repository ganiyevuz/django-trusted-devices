from rest_framework.views import exception_handler


def trusted_device_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to expose the exception's
    `code` alongside `detail` in the JSON response body. Stable error
    codes are part of this library's public contract — clients should
    branch on `code`, not on the human-readable `detail` string.

    Activate by setting in REST_FRAMEWORK:

        "EXCEPTION_HANDLER": "trusted_devices.handlers.trusted_device_exception_handler"
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "default_code", None) or getattr(exc, "code", None)
    if code and isinstance(response.data, dict) and "code" not in response.data:
        response.data["code"] = code

    return response
