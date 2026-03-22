# 🌍 Geolocation Backends

By default, Django Trusted Devices uses [ipapi.co](https://ipapi.co) for IP geolocation. You can replace it with any provider by configuring the `GEOLOCATION_BACKEND` setting.

## Configuration

```python
TRUSTED_DEVICE = {
    "GEOLOCATION_BACKEND": "myapp.geo.maxmind_lookup",
}
```

## Backend Contract

A geolocation backend is a callable that:

1. **Accepts** a single `ip` string argument
2. **Returns** a `LocationData` dict with optional keys: `country`, `region`, `city`
3. **Returns** an empty dict `{}` on failure (never raises)

```python
from trusted_devices.utils import LocationData

def my_backend(ip: str) -> LocationData:
    # Your logic here
    return {
        "country": "United States",
        "region": "California",
        "city": "San Francisco",
    }
```

### Type Definitions

```python
class LocationData(TypedDict, total=False):
    country: str | None
    region: str | None
    city: str | None

class GeolocationBackend(Protocol):
    def __call__(self, ip: str) -> LocationData: ...
```

---

## Built-in Backend

The default backend (`trusted_devices.utils.get_location_data`) uses the free [ipapi.co](https://ipapi.co) API:

- **Rate limit**: 1,000 requests/day (free tier)
- **Timeout**: 5 seconds
- **Skips**: `127.0.0.1`, `::1`, empty IPs
- **Fails gracefully**: returns `{}` on error

---

## Custom Backend Examples

### MaxMind GeoIP2

```python
# myapp/geo.py
import geoip2.database
from trusted_devices.utils import LocationData

_reader = geoip2.database.Reader('/path/to/GeoLite2-City.mmdb')

def maxmind_lookup(ip: str) -> LocationData:
    try:
        response = _reader.city(ip)
        return {
            "country": response.country.name,
            "region": response.subdivisions.most_specific.name,
            "city": response.city.name,
        }
    except (geoip2.errors.AddressNotFoundError, ValueError):
        return {}
```

```python
# settings.py
TRUSTED_DEVICE = {
    "GEOLOCATION_BACKEND": "myapp.geo.maxmind_lookup",
}
```

### ip-api.com

```python
# myapp/geo.py
from httpx import Client, HTTPError
from trusted_devices.utils import LocationData

def ip_api_lookup(ip: str) -> LocationData:
    try:
        with Client(timeout=5.0) as client:
            response = client.get(f"http://ip-api.com/json/{ip}")
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                return {}
            return {
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
            }
    except (HTTPError, ValueError):
        return {}
```

### Disabled (no geolocation)

```python
# myapp/geo.py
from trusted_devices.utils import LocationData

def no_geolocation(ip: str) -> LocationData:
    return {}
```

```python
# settings.py
TRUSTED_DEVICE = {
    "GEOLOCATION_BACKEND": "myapp.geo.no_geolocation",
}
```

---

## Validation

The backend's return value is automatically validated by the library:

- **Non-dict returns** (e.g. `None`, `list`, `str`) are logged as warnings and treated as `{}`
- **Unexpected keys** are logged as warnings and ignored — only `country`, `region`, `city` are used
- **Missing keys** default to `None`

This means your backend can safely return extra data without breaking anything, though you'll see a warning in your logs.

---

## Error Handling

If the `GEOLOCATION_BACKEND` setting is misconfigured, an `InvalidGeolocationBackend` error is raised with a descriptive message:

| Misconfiguration | Error Message |
|-------------------|---------------|
| Empty or non-string value | Must be a non-empty dotted path string |
| No dot in path (e.g. `"lookup"`) | Not a valid dotted path. Expected `module.path.function_name` |
| Module doesn't exist | Could not import geolocation backend module |
| Function doesn't exist in module | Module does not have the specified attribute |
| Attribute is not callable | Resolved to a non-callable type |
