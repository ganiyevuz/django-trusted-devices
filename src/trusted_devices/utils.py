import logging
from importlib import import_module
from typing import Protocol, TypedDict

from httpx import Client, HTTPError

logger = logging.getLogger(__name__)


class LocationData(TypedDict, total=False):
    """
    Response schema for geolocation backends.
    All keys are optional — return an empty dict on failure.
    """

    country: str | None
    region: str | None
    city: str | None


class GeolocationBackend(Protocol):
    """
    Protocol that custom geolocation backends must implement.

    Accepts an IP address string and returns a LocationData dict
    with optional 'country', 'region', and 'city' keys.

    Example::

        def my_maxmind_backend(ip: str) -> LocationData:
            record = geoip_reader.city(ip)
            return {
                "country": record.country.name,
                "region": record.subdivisions.most_specific.name,
                "city": record.city.name,
            }
    """

    def __call__(self, ip: str) -> LocationData: ...


_VALID_LOCATION_KEYS = frozenset(LocationData.__annotations__.keys())


def get_client_ip(request) -> str:
    """
    Returns the client's real IP address, checking 'X-Forwarded-For' first,
    then falling back to 'REMOTE_ADDR'.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def get_location_data(ip: str) -> LocationData:
    """
    Default geolocation backend. Fetches approximate location data
    (country, region, city) from IP address using the ipapi.co external API.

    Returns empty dict on failure or for private/localhost IPs.
    """
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return {}

    try:
        with Client(timeout=5.0) as client:
            response = client.get(f"https://ipapi.co/{ip}/json/")
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                logger.warning("ipapi.co returned error for IP %s: %s", ip, data)
                return {}
            return {
                "country": data.get("country_name"),
                "region": data.get("region"),
                "city": data.get("city"),
            }
    except (HTTPError, ValueError, KeyError) as exc:
        logger.warning("Failed to fetch location for IP %s: %s", ip, exc)
        return {}


def get_geolocation_backend() -> GeolocationBackend:
    """
    Returns a validated geolocation function configured in TRUSTED_DEVICE settings.
    Defaults to `trusted_devices.utils.get_location_data`.

    The returned function is wrapped to automatically validate the backend's
    response, ensuring it returns a proper LocationData dict. Callers do not
    need to validate the output themselves.

    Custom backends must match the GeolocationBackend protocol:
    accept an IP string and return a LocationData dict.
    """
    from trusted_devices.exceptions import InvalidGeolocationBackend
    from trusted_devices.settings import trusted_device_settings

    backend_path = trusted_device_settings.GEOLOCATION_BACKEND

    if not isinstance(backend_path, str) or not backend_path.strip():
        raise InvalidGeolocationBackend(
            "TRUSTED_DEVICE['GEOLOCATION_BACKEND'] must be a non-empty "
            "dotted path string (e.g. 'myapp.geo.lookup')."
        )

    if "." not in backend_path:
        raise InvalidGeolocationBackend(
            f"TRUSTED_DEVICE['GEOLOCATION_BACKEND'] = '{backend_path}' "
            f"is not a valid dotted path. Expected format: 'module.path.function_name'."
        )

    module_path, func_name = backend_path.rsplit(".", 1)

    try:
        module = import_module(module_path)
    except ImportError as exc:
        raise InvalidGeolocationBackend(
            f"Could not import geolocation backend module '{module_path}'. "
            f"Check that TRUSTED_DEVICE['GEOLOCATION_BACKEND'] = '{backend_path}' "
            f"points to a valid module."
        ) from exc

    try:
        func = getattr(module, func_name)
    except AttributeError:
        raise InvalidGeolocationBackend(
            f"Module '{module_path}' does not have a '{func_name}' attribute. "
            f"Check that TRUSTED_DEVICE['GEOLOCATION_BACKEND'] = '{backend_path}' "
            f"points to a valid function."
        )

    if not callable(func):
        raise InvalidGeolocationBackend(
            f"TRUSTED_DEVICE['GEOLOCATION_BACKEND'] = '{backend_path}' "
            f"resolved to {type(func).__name__}, which is not callable. "
            f"It must be a function that accepts an IP string and returns a "
            f"LocationData dict with keys: {_VALID_LOCATION_KEYS}."
        )

    def validated_backend(ip: str) -> LocationData:
        raw = func(ip)

        if not isinstance(raw, dict):
            logger.warning(
                "Geolocation backend '%s' returned %s instead of dict. "
                "Ignoring result.",
                backend_path,
                type(raw).__name__,
            )
            return {}

        unexpected_keys = set(raw.keys()) - _VALID_LOCATION_KEYS
        if unexpected_keys:
            logger.warning(
                "Geolocation backend '%s' returned unexpected keys: %s. "
                "Only %s are used.",
                backend_path,
                unexpected_keys,
                _VALID_LOCATION_KEYS,
            )

        return {
            "country": raw.get("country"),
            "region": raw.get("region"),
            "city": raw.get("city"),
        }

    return validated_backend


def format_duration(minutes: int) -> str:
    """
    Converts a duration in minutes into a human-readable string format such as:
    "1 week, 2 days, 3 hours, 15 minutes".
    """
    parts = []

    weeks, minutes = divmod(minutes, 60 * 24 * 7)
    if weeks:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")

    days, minutes = divmod(minutes, 60 * 24)
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")

    hours, minutes = divmod(minutes, 60)
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return ", ".join(parts) if parts else "0 minutes"
