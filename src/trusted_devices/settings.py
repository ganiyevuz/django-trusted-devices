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
}


class TrustedDeviceSettings:
    def __init__(self, defaults: dict[str, Any] = None):
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
