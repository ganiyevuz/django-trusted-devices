# 📘 API Reference

## 🔐 Token Views

- `POST /api/token/` — Login
- `POST /api/token/refresh/` — Refresh with same device
- `POST /api/token/verify/` — Verify device-bound token

## 📡 TrustedDeviceViewSet

### Fields:
- `device_uid` – Unique UUID
- `user_agent`, `ip_address`
- `country`, `region`, `city`
- `last_seen`, `created_at`
- `can_update_other_devices`
- `can_delete_other_devices`

## 🔐 Permissions

- Only authenticated users can access their own devices
- Global update/delete controlled by settings or user permissions

