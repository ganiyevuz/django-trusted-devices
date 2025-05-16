# 🧩 Usage Guide

## 🔐 SimpleJWT configuration

Replace default SimpleJWT serializers with TrustedDevice serializers.:

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
````

### 📡 Device Management API

Use provided `TrustedDeviceViewSet`:

```python
from trusted_devices.views import TrustedDeviceViewSet

router.register(r'trusted-devices', TrustedDeviceViewSet)
```

Endpoints:

* `GET /trusted-devices` — List devices
* `DELETE /trusted-devices/{uid}` — Remove session
* `PATCH /trusted-devices/{uid}` — Change permissions

## ⚙️ Settings

```python
TRUSTED_DEVICE = {
    "DELETE_DELAY_MINUTES": 60 * 24 * 7,
    "UPDATE_DELAY_MINUTES": 60,
    "ALLOW_GLOBAL_DELETE": True,
    "ALLOW_GLOBAL_UPDATE": True,
}
```