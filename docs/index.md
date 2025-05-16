# 🔐 Django Trusted Device

Welcome to the official documentation for the Django Trusted Device library.

This package provides JWT-based trusted device tracking with per-device session control and security.

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

Check the [Usage](usage.md) page for integration details.
