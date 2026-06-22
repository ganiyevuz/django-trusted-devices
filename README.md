# 🔐 Django Trusted Devices

A plug-and-play Django app that adds **trusted device management** to your API authentication system using
`djangorestframework-simplejwt`. Automatically associates tokens with user devices, tracks login locations,
and enables per-device control over access and session management.

---
[![Docs](https://img.shields.io/badge/docs-view-green?style=for-the-badge&logo=readthedocs)](https://ganiyevuz.github.io/django-trusted-devices/)


## 🚀 Features

* 🔑 **JWT tokens** include a unique `device_uid`
* 🌍 **Auto-detect IP, region, and city** via configurable geolocation backend
* 🛡️ **Per-device session tracking** with update/delete restrictions
* 🔄 **Custom** `TokenObtainPair`, `TokenRefresh`, and `TokenVerify` views
* 🚪 **Logout & revoke** — logout current session or revoke all other devices
* 🧼 **Automatic cleanup** of stale devices on login + management command
* 🏷️ **Device naming** — let users label their devices ("Work Laptop", "iPhone")
* 📍 **`is_current` flag** — identify which device is making the request
* 🚨 **Suspicious login detection** — signals when a login comes from a new country
* 🕵️ **Concurrent-session hijack detection** — same `device_uid` from a new IP inside a short window invalidates both sessions
* 🔒 **Rate limiting** on login to prevent brute-force and device-creation spam
* 📊 **Max device limit** — configurable cap with automatic oldest-device eviction (race-safe under concurrent logins)
* ⚠️ **Custom exception classes** — catchable, typed errors with stable error codes (and optional handler that surfaces `code` in JSON)
* 📖 **Full OpenAPI/Swagger schema** via drf-spectacular
* 🧩 **API-ready** — supports DRF out of the box
* ⚙️ **Fully customizable** via `TRUSTED_DEVICE` Django settings
* 🛰️ **Trusted-proxy aware** `X-Forwarded-For` parsing (off by default — opt in once behind a known reverse proxy)
* 🌐 **Cached geolocation** — configurable per-IP TTL keeps login latency low
* 🚫 **Rejects refresh/verify** from unknown or cross-user devices

---

## 📦 Installation

```bash
pip install django-trusted-device
```

Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'trusted_devices',
    'rest_framework_simplejwt.token_blacklist',  # optional, for token rotation
]
```

Run migrations:

```bash
python manage.py migrate
```

---

## ⚙️ Configuration

Customize behavior in `settings.py`:

```python
TRUSTED_DEVICE = {
    "DELETE_DELAY_MINUTES": 60 * 24,       # 24 hours before a device can be deleted
    "UPDATE_DELAY_MINUTES": 60,            # 1 hour before a device can be edited
    "ALLOW_GLOBAL_DELETE": True,           # Enable/disable device deletion globally
    "ALLOW_GLOBAL_UPDATE": True,           # Enable/disable device editing globally
    "MAX_DEVICES_PER_USER": None,          # None = unlimited, or set e.g. 5
    "GEOLOCATION_BACKEND": "trusted_devices.utils.get_location_data",
    "GEOLOCATION_CACHE_SECONDS": 60 * 60 * 24,  # 24h cache; 0 disables
    "DEFAULT_CAN_UPDATE_OTHER_DEVICES": True,   # Default perm for new devices
    "DEFAULT_CAN_DELETE_OTHER_DEVICES": True,   # Default perm for new devices

    # Trusted-proxy parsing — enable only when behind a known reverse proxy.
    "USE_X_FORWARDED_FOR": False,
    "TRUSTED_PROXY_DEPTH": 1,

    # Concurrent-session hijack detection.
    "DETECT_CONCURRENT_SESSIONS": True,
    "CONCURRENT_SESSION_WINDOW_SECONDS": 60,
}
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `DELETE_DELAY_MINUTES` | `1440` (24h) | Minimum device age before it can be deleted |
| `UPDATE_DELAY_MINUTES` | `60` (1h) | Minimum device age before it can be edited |
| `ALLOW_GLOBAL_DELETE` | `True` | Master switch for device deletion |
| `ALLOW_GLOBAL_UPDATE` | `True` | Master switch for device editing |
| `MAX_DEVICES_PER_USER` | `None` | Max active devices per user. Oldest evicted on new login (race-safe) |
| `GEOLOCATION_BACKEND` | `"trusted_devices.utils.get_location_data"` | Dotted path to geolocation function |
| `GEOLOCATION_CACHE_SECONDS` | `86400` | Per-IP cache TTL for geolocation lookups. `0` disables caching |
| `DEFAULT_CAN_UPDATE_OTHER_DEVICES` | `True` | Default update permission for newly created devices |
| `DEFAULT_CAN_DELETE_OTHER_DEVICES` | `True` | Default delete permission for newly created devices |
| `USE_X_FORWARDED_FOR` | `False` | When `True`, parse `X-Forwarded-For` to determine client IP. Leave `False` if the app is exposed directly — clients can otherwise spoof their own IP |
| `TRUSTED_PROXY_DEPTH` | `1` | Number of trusted reverse proxies between the client and the app. The client IP is taken at position `-(depth+1)` from the right of `X-Forwarded-For`, so spoofed leftmost entries are ignored |
| `DETECT_CONCURRENT_SESSIONS` | `True` | If a token's `device_uid` is presented from a different IP within the window below, the device is deleted (kicking both sessions) and `device_compromised` is fired |
| `CONCURRENT_SESSION_WINDOW_SECONDS` | `60` | Time window inside which a same-token IP change is treated as a hijack rather than a legitimate roaming user |

---

## 🧩 Usage

### 🔐 SimpleJWT Configuration

Replace default SimpleJWT serializers with TrustedDevice serializers:

```python
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'trusted_devices.authentication.TrustedDeviceAuthentication',
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": 'trusted_devices.serializers.TrustedDeviceTokenObtainPairSerializer',
    "TOKEN_REFRESH_SERIALIZER": 'trusted_devices.serializers.TrustedDeviceTokenRefreshSerializer',
    "TOKEN_VERIFY_SERIALIZER": 'trusted_devices.serializers.TrustedDeviceTokenVerifySerializer',
}
```

### 🔐 Custom Token Views

Replace the default SimpleJWT views:

```python
from trusted_devices.views import (
    TrustedDeviceTokenObtainPairView,
    TrustedDeviceTokenRefreshView,
    TrustedDeviceTokenVerifyView,
)

urlpatterns = [
    path('api/token/', TrustedDeviceTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TrustedDeviceTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TrustedDeviceTokenVerifyView.as_view(), name='token_verify'),
]
```

---

### 📡 Device Management API

Use the provided `TrustedDeviceViewSet`:

```python
from trusted_devices.views import TrustedDeviceViewSet

router.register(r'trusted-devices', TrustedDeviceViewSet, basename='trusted-device')
```

#### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/trusted-devices` | List all devices (includes `is_current` flag) |
| `PATCH` | `/trusted-devices/{device_uid}` | Update device name & permissions |
| `DELETE` | `/trusted-devices/{device_uid}` | Delete a specific device session |
| `POST` | `/trusted-devices/logout` | Revoke current device session |
| `POST` | `/trusted-devices/revoke-all` | Revoke all other device sessions |

#### Example: List Devices Response

```json
[
  {
    "device_uid": "a1b2c3d4-...",
    "name": "Work Laptop",
    "user_agent": "Mozilla/5.0 ...",
    "ip_address": "203.0.113.42",
    "last_ip": "203.0.113.42",
    "country": "United States",
    "region": "California",
    "city": "San Francisco",
    "last_seen": "2026-03-22T10:30:00Z",
    "created_at": "2026-03-15T08:00:00Z",
    "can_update_other_devices": true,
    "can_delete_other_devices": true,
    "is_current": true
  },
  {
    "device_uid": "e5f6g7h8-...",
    "name": "",
    "user_agent": "okhttp/4.12.0",
    "ip_address": "198.51.100.7",
    "last_ip": "198.51.100.23",
    "country": "Germany",
    "region": "Berlin",
    "city": "Berlin",
    "last_seen": "2026-03-20T14:22:00Z",
    "created_at": "2026-03-10T09:15:00Z",
    "can_update_other_devices": false,
    "can_delete_other_devices": false,
    "is_current": false
  }
]
```

#### Example: Revoke All Response

```json
{
  "revoked_count": 3
}
```

---

## 🚨 Signals

Connect to device lifecycle events:

```python
from django.dispatch import receiver
from trusted_devices.signals import (
    device_created,
    device_revoked,
    suspicious_login,
    device_compromised,
)

@receiver(device_created)
def on_new_device(sender, user, device, **kwargs):
    """Fired when a new device is registered (login)."""
    send_notification(user, f"New login from {device.city}, {device.country}")

@receiver(device_revoked)
def on_device_removed(sender, user, device_uid, **kwargs):
    """Fired when a device is deleted."""
    log_audit(user, f"Device {device_uid} revoked")

@receiver(suspicious_login)
def on_suspicious_login(sender, user, device, previous_countries, **kwargs):
    """Fired when a login comes from a country not seen before."""
    send_email(
        user,
        f"New login from {device.country} — was this you? "
        f"Your previous logins were from: {', '.join(previous_countries)}"
    )

@receiver(device_compromised)
def on_device_compromised(sender, device_uid, previous_ip, current_ip, **kwargs):
    """
    Fired when a token is presented from a new IP within
    CONCURRENT_SESSION_WINDOW_SECONDS — the device record has already been
    deleted by the time this signal fires. The `user` kwarg is provided
    when the request reached the auth layer; on refresh-time detection,
    `user_id` is provided instead.
    """
    user = kwargs.get("user")
    user_id = kwargs.get("user_id") or (user.pk if user else None)
    alert_security_team(
        user_id=user_id,
        message=f"Possible token theft for device {device_uid}: "
                f"{previous_ip} → {current_ip}",
    )
```

| Signal | Args | When |
|--------|------|------|
| `device_created` | `user`, `device` | New device registered on login |
| `device_revoked` | `user`, `device_uid` | Device deleted (via API, cleanup, or eviction) |
| `suspicious_login` | `user`, `device`, `previous_countries` | Login from a new country |
| `device_compromised` | `user` *or* `user_id`, `device_uid`, `previous_ip`, `current_ip` | Same `device_uid` used from a new IP inside `CONCURRENT_SESSION_WINDOW_SECONDS`. The device has already been deleted; both sessions are now invalid |

---

## ⚠️ Exception Classes

All exceptions are importable from `trusted_devices.exceptions`:

| Exception | HTTP | Code | When |
|-----------|------|------|------|
| `DeviceUIDMissing` | 401 | `device_uid_missing` | Token has no `device_uid` claim |
| `DeviceNotRecognized` | 401 | `device_not_recognized` | Device deleted, never existed, or belongs to a different user than the token claims |
| `DeviceCompromised` | 401 | `device_compromised` | Same `device_uid` used from a new IP inside `CONCURRENT_SESSION_WINDOW_SECONDS`; session has been invalidated |
| `InactiveAccount` | 401 | `inactive_account` | User disabled after token issued |
| `TokenBlacklisted` | 400 | `token_blacklisted` | Rotated token reuse attempt |
| `DeviceNotVerified` | 403 | `device_not_verified` | No current device on request |
| `DeviceDeletionDisabled` | 403 | `device_deletion_disabled` | Global deletion turned off |
| `DeviceEditingDisabled` | 403 | `device_editing_disabled` | Global editing turned off |
| `DeviceLacksDeletePermission` | 403 | `device_lacks_delete_permission` | Device can't delete others |
| `DeviceLacksEditPermission` | 403 | `device_lacks_edit_permission` | Device can't edit others |
| `DeviceSessionTooRecent` | 403 | `device_session_too_recent` | Target within delay window |
| `DeviceSelfModification` | 403 | `device_self_modification` | Attempt to modify/delete own device (use `/logout`) |
| `DevicePermissionEscalation` | 403 | `device_permission_escalation` | Granting permissions the current device doesn't have |
| `InvalidGeolocationBackend` | — | — | Misconfigured `GEOLOCATION_BACKEND` (startup error) |

```python
from trusted_devices.exceptions import DeviceNotRecognized

try:
    # ... authenticate
except DeviceNotRecognized:
    # handle specifically instead of catching generic AuthenticationFailed
    pass
```

### Surfacing `code` in JSON responses (optional)

DRF's default exception handler emits only `detail` in error bodies. To
include the stable `code` alongside it — recommended for clients that
branch on machine-readable error identifiers — wire up the bundled
handler:

```python
REST_FRAMEWORK = {
    # ...
    "EXCEPTION_HANDLER": "trusted_devices.handlers.trusted_device_exception_handler",
}
```

Responses then look like:

```json
{
  "detail": "This session device is no longer valid.",
  "code": "device_not_recognized"
}
```

---

## 🌍 Custom Geolocation Backend

By default, geolocation uses [ipapi.co](https://ipapi.co). You can replace it with any provider (MaxMind GeoIP2, ip-api.com, etc.):

```python
# settings.py
TRUSTED_DEVICE = {
    "GEOLOCATION_BACKEND": "myapp.geo.maxmind_lookup",
}
```

Your backend must accept an IP string and return a dict with optional keys `country`, `region`, `city`:

```python
# myapp/geo.py
from trusted_devices.utils import LocationData

def maxmind_lookup(ip: str) -> LocationData:
    import geoip2.database

    reader = geoip2.database.Reader('/path/to/GeoLite2-City.mmdb')
    try:
        response = reader.city(ip)
        return {
            "country": response.country.name,
            "region": response.subdivisions.most_specific.name,
            "city": response.city.name,
        }
    except geoip2.errors.AddressNotFoundError:
        return {}
```

The backend's return value is automatically validated — unexpected keys are logged as warnings, non-dict returns are safely ignored.

Geolocation results are cached per-IP for `GEOLOCATION_CACHE_SECONDS` (default 24h). Repeat lookups don't hit the backend, so login latency stays low and external API quota isn't spent re-resolving the same client. Set `GEOLOCATION_CACHE_SECONDS = 0` to disable.

---

## 🛰️ Trusted Proxies & Client IP

By default the library uses `REMOTE_ADDR` as the client IP. The `X-Forwarded-For` header is **ignored** unless you opt in — otherwise a client connecting directly to the app could spoof their IP and country by setting the header themselves.

When the app runs behind a known reverse proxy (Cloudflare, AWS ALB, nginx, etc.), enable parsing and tell the library how many trusted hops sit between the public client and Django:

```python
TRUSTED_DEVICE = {
    "USE_X_FORWARDED_FOR": True,
    "TRUSTED_PROXY_DEPTH": 1,  # 1 if you have one proxy, 2 if proxy → load balancer, etc.
}
```

The client IP is read at position `-(TRUSTED_PROXY_DEPTH + 1)` from the right of `X-Forwarded-For`, which is the last entry an attacker cannot inject.

---

## 🕵️ Concurrent-Session Hijack Detection

If a stolen access or refresh token is replayed from a different IP while the legitimate user is still active, the library treats it as a session hijack:

1. On every authenticated request, the incoming IP is compared against the device's stored `last_ip`.
2. If they differ **and** `last_seen` is within `CONCURRENT_SESSION_WINDOW_SECONDS` (default `60`), the device record is deleted.
3. Both sessions immediately fail authentication on their next request (`DeviceCompromised`, code `device_compromised`).
4. The `device_compromised` signal fires so you can alert the user, revoke related sessions, or escalate to a security team.

Detection is on by default and respects `USE_X_FORWARDED_FOR` for IP attribution. To disable (e.g. if you have a roaming-heavy mobile audience), set:

```python
TRUSTED_DEVICE = {
    "DETECT_CONCURRENT_SESSIONS": False,
}
```

> ℹ️ Tune `CONCURRENT_SESSION_WINDOW_SECONDS` carefully. A short window catches active token-replay; a long window will cause false positives for users on flaky mobile networks where IPs change between requests.

---

## 🧹 Device Cleanup

### Automatic (on login)

Stale devices (not seen within `REFRESH_TOKEN_LIFETIME`) are automatically cleaned up each time a user logs in.

### Management Command

```bash
# Delete devices not seen within the refresh token lifetime
python manage.py cleanup_devices

# Override with a custom cutoff (30 days)
python manage.py cleanup_devices --days 30

# Preview without deleting
python manage.py cleanup_devices --dry-run
```

Add to crontab for scheduled cleanup:

```bash
# Run daily at 3am
0 3 * * * python manage.py cleanup_devices
```

---

## 👤 Device Model

Each trusted device includes:

| Field | Purpose |
|-------|---------|
| `device_uid` | UUID primary key |
| `name` | User-defined label (e.g. "Work Laptop") |
| `user_agent` | Browser or app string |
| `ip_address` | Client IP captured when the device was first registered |
| `last_ip` | Most recently observed IP — compared against incoming requests for hijack detection |
| `country` / `region` / `city` | Geolocation data |
| `last_seen` / `created_at` | Activity timestamps |
| `can_update_other_devices` | Permission flag |
| `can_delete_other_devices` | Permission flag |

---

## 🧠 How It Works

1. **Login** → a `device_uid` is generated and embedded in the JWT token. A `TrustedDevice` record is created (transactionally, with row-level locking on the user when `MAX_DEVICES_PER_USER` is set) with IP, user agent, and geolocation.
2. **Every API request** → `TrustedDeviceAuthentication` validates the `device_uid` belongs to the token's user, runs hijack detection against `last_ip`, then updates `last_seen` + `last_ip`.
3. **Token refresh** → validates the device still exists *for this user*, runs hijack detection, updates timestamps, and optionally rotates the token.
4. **Device management** → users can list, rename, update permissions, or revoke their devices via the API.
5. **Session revocation** → deleting a device record immediately blocks all requests using tokens linked to that device, even if the JWT hasn't expired.
6. **Hijack invalidation** → if the same `device_uid` appears from a new IP within the configured window, the device record is deleted on the spot — both sessions fail their next call with `DeviceCompromised`.

---

## 🧪 Testing Locally

```bash
# Create and activate a virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the package in editable mode with dev extras
uv pip install -e ".[dev]"

# Run the test suite
pytest
```

---

## 🧱 Dependencies

* Django >= 5.2, < 6.1 (5.2 LTS and 6.0)
* Django REST Framework >= 3.14.0
* djangorestframework-simplejwt >= 5.5.0
* drf-spectacular >= 0.28.0
* httpx >= 0.28.1 (for default geolocation backend)

---

## 🤝 Collaboration & Contributing

We love community contributions! To collaborate:

1. **Fork** the repo and create a feature branch:

   ```bash
   git checkout -b feature/my-amazing-idea
   ```

2. **Follow code style** – run:

   ```bash
   make lint  # runs flake8, isort, black
   ```

3. **Write & run tests**:

   ```bash
   pytest
   ```

4. **Commit** with clear messages and open a **Pull Request**.
   GitHub Actions will lint + test your branch automatically.

---

### 🗣️ Discussions & Issues

* 💡 Questions / ideas → [GitHub Discussions](https://github.com/ganiyevuz/django-trusted-devices/discussions)
* 🐛 Bugs / feature requests → [GitHub Issues](https://github.com/ganiyevuz/django-trusted-devices/issues)

---

### 🛠 Maintainer Workflow

* PRs require at least one approval and passing CI
* We **squash‑merge** to keep history clean
* Follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`), tagged as `vX.Y.Z`

---

## 📄 License

[MIT](LICENSE)

---

Made with ❤️ by [Jahongir Ganiev](https://github.com/ganiyevuz)
Security questions or commercial support? Open an issue or email **[contact@jakhongir.dev](mailto:contact@jakhongir.dev)**
