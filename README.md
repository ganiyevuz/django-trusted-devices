# 🔐 Django Trusted Device

A plug-and-play Django app that adds **trusted device management** to your API authentication system using
`djangorestframework-simplejwt`. Automatically associates tokens with user devices, tracks login locations,
and enables per-device control over access and session management.

---
[![Docs](https://img.shields.io/badge/docs-view-green?style=for-the-badge&logo=readthedocs)](https://ganiyevuz.github.io/django-trusted-devices/)


## 🚀 Features

* 🔑 **JWT tokens** include a unique `device_uid`
* 🌍 **Auto-detect IP, region, and city** via [ipapi.co](https://ipapi.co)
* 🛡️ **Per-device session tracking** with update/delete restrictions
* 🔄 **Custom** `TokenObtainPair`, `TokenRefresh`, and `TokenVerify` views
* 🚪 **Logout unwanted sessions** from the device list
* 🧼 **Automatic cleanup**, optional global control rules
* 🧩 **API-ready** – supports DRF out of the box
* ⚙️ **Fully customizable** via `TRUSTED_DEVICE` Django settings
* 🚫 **Rejects refresh/verify** from unknown or expired devices

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
    'rest_framework_simplejwt.token_blacklist',
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
    "DELETE_DELAY_MINUTES": 60 * 24 * 7,  # 7 days
    "UPDATE_DELAY_MINUTES": 60,           # 1 hour
    "ALLOW_GLOBAL_DELETE": True,
    "ALLOW_GLOBAL_UPDATE": True,
}
```

---

## 🧩 Usage


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

### 🔐 Custom Token Views

Replace the default SimpleJWT views with:

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

Endpoints:

* `GET /trusted-devices` — List all trusted devices
* `DELETE /trusted-devices/{device_uid}` — Delete a device
* `PATCH /trusted-devices/{device_uid}` — Update device permissions

---

## 👤 Device Model

Each trusted device includes:

* `device_uid`: Unique UUID
* `user_agent`: Browser or device string
* `ip_address`: IP address
* `country`, `region`, `city`: Geolocation (via `ipapi.co`)
* `last_seen`, `created_at`: Timestamps
* `can_delete_other_devices`, `can_update_other_devices`: Optional privileges

---

## 🧠 How It Works

1. During login, a `device_uid` is generated and embedded in the token.
2. Clients use that token (with `device_uid`) for refresh/verify.
3. Each request is linked to a known device.
4. Users can manage or restrict their devices via API or Admin.

---

## 🧪 Testing Locally

```bash
# 🧩 Create and activate a uv-managed virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 📦 Install the package in editable mode with dev extras
uv pip install -e ".[dev]"

# 🧪 Run the test suite
pytest
```

---

## 🧱 Dependencies

* Django
* Django REST Framework
* djangorestframework-simplejwt
* [ipapi.co](https://ipapi.co) (for IP geolocation)

---

## 🗃️ Model Snapshot

| Field                      | Purpose             |
| -------------------------- | ------------------- |
| `device_uid`               | UUID primary key    |
| `user_agent`, `ip_address` | Device fingerprint  |
| `country / region / city`  | Geo‑lookup          |
| `last_seen / created_at`   | Activity timestamps |
| `can_update_other_devices` | Granular permission |
| `can_delete_other_devices` | Granular permission |

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
