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
* 🔒 **Rate limiting** on login to prevent brute-force and device-creation spam
* 📊 **Max device limit** — configurable cap with automatic oldest-device eviction
* ⚠️ **Custom exception classes** — catchable, typed errors with stable error codes
* 📖 **Full OpenAPI/Swagger schema** via drf-spectacular
* 🧩 **API-ready** — supports DRF out of the box
* ⚙️ **Fully customizable** via `TRUSTED_DEVICE` Django settings
* 🚫 **Rejects refresh/verify** from unknown devices

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
    "DEFAULT_CAN_UPDATE_OTHER_DEVICES": True,   # Default perm for new devices
    "DEFAULT_CAN_DELETE_OTHER_DEVICES": True,   # Default perm for new devices
}
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `DELETE_DELAY_MINUTES` | `1440` (24h) | Minimum device age before it can be deleted |
| `UPDATE_DELAY_MINUTES` | `60` (1h) | Minimum device age before it can be edited |
| `ALLOW_GLOBAL_DELETE` | `True` | Master switch for device deletion |
| `ALLOW_GLOBAL_UPDATE` | `True` | Master switch for device editing |
| `MAX_DEVICES_PER_USER` | `None` | Max active devices per user. Oldest evicted on new login |
| `GEOLOCATION_BACKEND` | `"trusted_devices.utils.get_location_data"` | Dotted path to geolocation function |
| `DEFAULT_CAN_UPDATE_OTHER_DEVICES` | `True` | Default update permission for newly created devices |
| `DEFAULT_CAN_DELETE_OTHER_DEVICES` | `True` | Default delete permission for newly created devices |

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
    "country": "United States",
    "region": "California",
    "city": "San Francisco",
    "last_seen": "2026-03-22T10:30:00Z",
    "created_at": "2026-03-15T08:00:00Z",
    "is_current": true
  },
  {
    "device_uid": "e5f6g7h8-...",
    "name": "",
    "user_agent": "okhttp/4.12.0",
    "ip_address": "198.51.100.7",
    "country": "Germany",
    "region": "Berlin",
    "city": "Berlin",
    "last_seen": "2026-03-20T14:22:00Z",
    "created_at": "2026-03-10T09:15:00Z",
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
from trusted_devices.signals import device_created, device_revoked, suspicious_login

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
```

| Signal | Args | When |
|--------|------|------|
| `device_created` | `user`, `device` | New device registered on login |
| `device_revoked` | `user`, `device_uid` | Device deleted (via API, cleanup, or eviction) |
| `suspicious_login` | `user`, `device`, `previous_countries` | Login from a new country |

---

## ⚠️ Exception Classes

All exceptions are importable from `trusted_devices.exceptions`:

| Exception | HTTP | Code | When |
|-----------|------|------|------|
| `DeviceUIDMissing` | 401 | `device_uid_missing` | Token has no `device_uid` claim |
| `DeviceNotRecognized` | 401 | `device_not_recognized` | Device deleted or never existed |
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
| `ip_address` | Client IP address |
| `country` / `region` / `city` | Geolocation data |
| `last_seen` / `created_at` | Activity timestamps |
| `can_update_other_devices` | Permission flag |
| `can_delete_other_devices` | Permission flag |

---

## 🧠 How It Works

1. **Login** → a `device_uid` is generated and embedded in the JWT token. A `TrustedDevice` record is created with IP, user agent, and geolocation.
2. **Every API request** → `TrustedDeviceAuthentication` validates the `device_uid` from the token against the database and updates `last_seen`.
3. **Token refresh** → validates the device still exists, updates `last_seen`, and optionally rotates the token.
4. **Device management** → users can list, rename, update permissions, or revoke their devices via the API.
5. **Session revocation** → deleting a device record immediately blocks all requests using tokens linked to that device, even if the JWT hasn't expired.

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

* Django >= 4.2
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
