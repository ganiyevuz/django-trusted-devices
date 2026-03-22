# 🧩 Usage Guide

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

## 🔐 SimpleJWT Configuration

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

## 🔐 Token Views

Replace default SimpleJWT views with TrustedDevice views:

```python
from trusted_devices.views import (
    TrustedDeviceTokenObtainPairView,
    TrustedDeviceTokenRefreshView,
    TrustedDeviceTokenVerifyView,
)

urlpatterns = [
    path('api/token', TrustedDeviceTokenObtainPairView.as_view()),
    path('api/token/refresh', TrustedDeviceTokenRefreshView.as_view()),
    path('api/token/verify', TrustedDeviceTokenVerifyView.as_view()),
]
```

---

## 📡 Device Management API

Use the provided `TrustedDeviceViewSet`:

```python
from trusted_devices.views import TrustedDeviceViewSet

router.register(r'trusted-devices', TrustedDeviceViewSet, basename='trusted-device')
```

Endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/trusted-devices` | List all devices (includes `is_current` flag) |
| `PATCH` | `/trusted-devices/{device_uid}` | Update device name & permissions |
| `DELETE` | `/trusted-devices/{device_uid}` | Delete a specific device session |
| `POST` | `/trusted-devices/logout` | Revoke current device session |
| `POST` | `/trusted-devices/revoke-all` | Revoke all other device sessions |

---

## ⚙️ Settings

```python
TRUSTED_DEVICE = {
    "DELETE_DELAY_MINUTES": 60 * 24,       # 24 hours before a device can be deleted
    "UPDATE_DELAY_MINUTES": 60,            # 1 hour before a device can be edited
    "ALLOW_GLOBAL_DELETE": True,           # Enable/disable device deletion globally
    "ALLOW_GLOBAL_UPDATE": True,           # Enable/disable device editing globally
    "MAX_DEVICES_PER_USER": None,          # None = unlimited, or set e.g. 5
    "GEOLOCATION_BACKEND": "trusted_devices.utils.get_location_data",
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

## 🧠 How It Works

1. **Login** — a `device_uid` is generated and embedded in the JWT token. A `TrustedDevice` record is created with IP, user agent, and geolocation.
2. **Every API request** — `TrustedDeviceAuthentication` validates the `device_uid` from the token against the database and updates `last_seen`.
3. **Token refresh** — validates the device still exists, updates `last_seen`, and optionally rotates the token.
4. **Device management** — users can list, rename, update permissions, or revoke their devices via the API.
5. **Session revocation** — deleting a device record immediately blocks all requests using tokens linked to that device, even if the JWT hasn't expired.
