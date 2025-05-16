from django.conf import settings
from functools import lru_cache
from typing import Any

# Private default settings
_TRUSTED_DEVICE_DEFAULTS = {
    "DELETE_DELAY_MINUTES": 2005,
    "UPDATE_DELAY_MINUTES": 60,
    "ALLOW_GLOBAL_DELETE": True,
    "ALLOW_GLOBAL_UPDATE": True,
}


class TrustedDeviceSettings:
    def __init__(
        self, user_settings: dict[str, Any] = None, defaults: dict[str, Any] = None
    ):
        self._user_settings = user_settings or getattr(settings, "TRUSTED_DEVICE", {})
        self._defaults = defaults or _TRUSTED_DEVICE_DEFAULTS

    def __getattr__(self, attr: str) -> Any:
        if attr not in self._defaults:
            raise AttributeError(f"Invalid TRUSTED_DEVICE setting: '{attr}'")
        return self._user_settings.get(attr, self._defaults[attr])

    def __dir__(self):
        return list(self._defaults.keys())


@lru_cache(maxsize=1)
def get_trusted_device_settings() -> TrustedDeviceSettings:
    return TrustedDeviceSettings()


# Singleton instance to import and use
trusted_device_settings = get_trusted_device_settings()
