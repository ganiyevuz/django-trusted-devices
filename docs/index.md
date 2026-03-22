# 🔐 Django Trusted Devices

Welcome to the official documentation for the Django Trusted Devices library.

This package provides JWT-based trusted device tracking with per-device session control and security.

## 🚀 Features

* 🔑 **JWT tokens** include a unique `device_uid`
* 🌍 **Auto-detect IP, region, and city** via configurable geolocation backend
* 🛡️ **Per-device session tracking** with update/delete restrictions
* 🔄 **Custom** `TokenObtainPair`, `TokenRefresh`, and `TokenVerify` views
* 🚪 **Logout & revoke** — logout current session or revoke all other devices
* 🧼 **Automatic cleanup** of stale devices on login + management command
* 🏷️ **Device naming** — let users label their devices
* 📍 **`is_current` flag** — identify which device is making the request
* 🚨 **Suspicious login detection** — signals when a login comes from a new country
* 🔒 **Rate limiting** on login to prevent brute-force attacks
* 📊 **Max device limit** — configurable cap with oldest-device eviction
* ⚠️ **Custom exception classes** — catchable, typed errors with stable codes
* 📖 **Full OpenAPI/Swagger schema** via drf-spectacular
* 🧩 **API-ready** — supports DRF out of the box
* ⚙️ **Fully customizable** via `TRUSTED_DEVICE` Django settings

## 📚 Documentation

- [Usage Guide](usage.md) — installation, configuration, and integration
- [API Reference](api.md) — endpoints, fields, and response schemas
- [Signals](signals.md) — device lifecycle events and suspicious login detection
- [Exceptions](exceptions.md) — custom error classes and error codes
- [Geolocation](geolocation.md) — custom geolocation backends
- [Contributing](contributing.md) — how to contribute
