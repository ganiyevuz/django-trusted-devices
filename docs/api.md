# 📘 API Reference

## 🔐 Token Endpoints

### `POST /api/token` — Obtain Token Pair

Authenticate with credentials and receive access/refresh tokens with a `device_uid`.

**Request:**

```json
{
  "username": "john",
  "password": "secret123"
}
```

**Response `200`:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1...",
  "access": "eyJ0eXAiOiJKV1...",
  "device_uid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Errors:**

| Code | Description |
|------|-------------|
| `401` | Invalid credentials |
| `429` | Rate limit exceeded (5 requests/min) |

---

### `POST /api/token/refresh` — Refresh Access Token

Exchange a valid refresh token for a new access token.

**Request:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1..."
}
```

**Response `200`:**

```json
{
  "access": "eyJ0eXAiOiJKV1...",
  "refresh": "eyJ0eXAiOiJKV1..."
}
```

The `refresh` field is only returned when `ROTATE_REFRESH_TOKENS` is enabled.

**Errors:**

| Code | Error | Description |
|------|-------|-------------|
| `401` | `device_not_recognized` | Device was revoked or doesn't exist |
| `401` | `inactive_account` | User account is disabled |

---

### `POST /api/token/verify` — Verify Token

Verify that a token is valid and its device still exists.

**Request:**

```json
{
  "token": "eyJ0eXAiOiJKV1..."
}
```

**Response `200`:** Empty body (token is valid).

**Errors:**

| Code | Error | Description |
|------|-------|-------------|
| `400` | `token_blacklisted` | Token has been blacklisted after rotation |
| `401` | `device_not_recognized` | Device was revoked or doesn't exist |

---

## 📡 Device Management Endpoints

All endpoints require authentication via `TrustedDeviceAuthentication`.

### `GET /trusted-devices` — List Devices

Returns all trusted devices for the authenticated user.

**Response `200`:**

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

---

### `PATCH /trusted-devices/{device_uid}` — Update Device

Update a device's name and permission flags. You cannot modify your own device (use `/logout` to revoke your session). You also cannot grant permissions that your current device doesn't have (escalation prevention).

**Request:**

```json
{
  "name": "My iPhone",
  "can_delete_other_devices": false,
  "can_update_other_devices": true
}
```

**Response `200`:**

```json
{
  "name": "My iPhone",
  "can_delete_other_devices": false,
  "can_update_other_devices": true
}
```

**Errors:**

| Code | Error | Description |
|------|-------|-------------|
| `403` | `device_self_modification` | Cannot modify your own device |
| `403` | `device_editing_disabled` | Global editing is turned off |
| `403` | `device_not_verified` | Current device not verified |
| `403` | `device_lacks_edit_permission` | Current device can't edit others |
| `403` | `device_permission_escalation` | Granting permissions you don't have |
| `403` | `device_session_too_recent` | Target device is within delay window |

---

### `DELETE /trusted-devices/{device_uid}` — Delete Device

Revoke a specific device session. You cannot delete your own device (use `/logout` instead).

**Response `204`:** No content.

**Errors:**

| Code | Error | Description |
|------|-------|-------------|
| `403` | `device_self_modification` | Cannot delete your own device (use `/logout`) |
| `403` | `device_deletion_disabled` | Global deletion is turned off |
| `403` | `device_not_verified` | Current device not verified |
| `403` | `device_lacks_delete_permission` | Current device can't delete others |
| `403` | `device_session_too_recent` | Target device is within delay window |

---

### `POST /trusted-devices/logout` — Logout Current Device

Revoke the current device session. The JWT remains cryptographically valid but subsequent requests will fail device validation.

**Request:** No body required.

**Response `204`:** No content.

---

### `POST /trusted-devices/revoke-all` — Revoke All Other Devices

Revoke all device sessions except the current one.

**Request:** No body required.

**Response `204`:**

```json
{
  "revoked_count": 3
}
```

---

## 👤 Device Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `device_uid` | `UUID` | Primary key, auto-generated |
| `name` | `CharField` | User-defined label (e.g. "Work Laptop") |
| `user` | `ForeignKey` | The user this device belongs to |
| `user_agent` | `TextField` | Browser or app user agent string |
| `ip_address` | `GenericIPAddressField` | Client IP address |
| `country` | `CharField` | Country from geolocation |
| `region` | `CharField` | Region/state from geolocation |
| `city` | `CharField` | City from geolocation |
| `last_seen` | `DateTimeField` | Last activity timestamp (auto-updated) |
| `created_at` | `DateTimeField` | Creation timestamp |
| `can_update_other_devices` | `BooleanField` | Can this device edit other devices |
| `can_delete_other_devices` | `BooleanField` | Can this device delete other devices |

---

## 🔐 Permissions

| Permission Class | Scope | Description |
|-----------------|-------|-------------|
| `TrustedDevicePermission` | All actions | Requires authenticated user with a current trusted device |
| `DeletableTrustedDevicePermission` | `destroy` | Checks global delete setting, device permission, and delay |
| `EditableTrustedDevicePermission` | `update`, `partial_update` | Checks global update setting, device permission, and delay |
