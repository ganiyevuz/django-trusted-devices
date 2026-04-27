from django.conf import settings
from typing import Any

_TRUSTED_DEVICE_DEFAULTS = {
    "DELETE_DELAY_MINUTES": 1440,
    "UPDATE_DELAY_MINUTES": 60,
    "ALLOW_GLOBAL_DELETE": True,
    "ALLOW_GLOBAL_UPDATE": True,
    "MAX_DEVICES_PER_USER": None,
    "GEOLOCATION_BACKEND": "trusted_devices.utils.get_location_data",
    "DEFAULT_CAN_UPDATE_OTHER_DEVICES": True,
    "DEFAULT_CAN_DELETE_OTHER_DEVICES": True,
    # Set True only when the app sits behind a known reverse proxy that
    # appends the real client IP to X-Forwarded-For. False = trust REMOTE_ADDR.
    "USE_X_FORWARDED_FOR": False,
    # Number of trusted reverse proxies between the client and the app.
    # The client IP is taken at position -(TRUSTED_PROXY_DEPTH+1) from the
    # right of X-Forwarded-For so spoofed leftmost entries are ignored.
    "TRUSTED_PROXY_DEPTH": 1,
    # Geolocation lookup cache TTL. 0 disables caching.
    "GEOLOCATION_CACHE_SECONDS": 60 * 60 * 24,
    # If True, the auth layer compares incoming IP to the device's last_ip
    # within CONCURRENT_SESSION_WINDOW_SECONDS. A mismatch triggers session
    # invalidation and a `device_compromised` signal.
    "DETECT_CONCURRENT_SESSIONS": True,
    "CONCURRENT_SESSION_WINDOW_SECONDS": 60,
}


class TrustedDeviceSettings:
    def __init__(self, defaults: dict[str, Any] | None = None):
        self._defaults = defaults or _TRUSTED_DEVICE_DEFAULTS

    def __getattr__(self, attr: str) -> Any:
        if attr.startswith("_"):
            raise AttributeError(attr)
        if attr not in self._defaults:
            raise AttributeError(f"Invalid TRUSTED_DEVICE setting: '{attr}'")
        user_settings = getattr(settings, "TRUSTED_DEVICE", {})
        return user_settings.get(attr, self._defaults[attr])

    def __dir__(self):
        return list(self._defaults.keys())


trusted_device_settings = TrustedDeviceSettings()
