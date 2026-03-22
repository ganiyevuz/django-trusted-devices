# ⚠️ Exceptions

All exceptions are importable from `trusted_devices.exceptions`. They extend DRF's built-in exception classes, so they are automatically handled by DRF's exception handler and return proper JSON error responses.

## Exception Reference

### Authentication Errors (HTTP 401)

| Exception | Code | Default Message |
|-----------|------|-----------------|
| `DeviceUIDMissing` | `device_uid_missing` | Device UID not found in token. |
| `DeviceNotRecognized` | `device_not_recognized` | This session device is no longer valid. |
| `InactiveAccount` | `inactive_account` | User account is inactive. |

These extend `rest_framework.exceptions.AuthenticationFailed`.

### Validation Errors (HTTP 400)

| Exception | Code | Default Message |
|-----------|------|-----------------|
| `TokenBlacklisted` | `token_blacklisted` | Token has been blacklisted. |

Extends `rest_framework.exceptions.ValidationError`.

### Permission Errors (HTTP 403)

| Exception | Code | Default Message |
|-----------|------|-----------------|
| `DeviceNotVerified` | `device_not_verified` | Your current session could not be verified as a trusted device. |
| `DeviceDeletionDisabled` | `device_deletion_disabled` | Device deletion is globally disabled by the system administrator. |
| `DeviceEditingDisabled` | `device_editing_disabled` | Device editing is globally disabled by the system administrator. |
| `DeviceLacksDeletePermission` | `device_lacks_delete_permission` | Your current device does not have permission to delete other sessions. |
| `DeviceLacksEditPermission` | `device_lacks_edit_permission` | Your current device does not have permission to modify other sessions. |
| `DeviceSessionTooRecent` | `device_session_too_recent` | This session is too recent to be {action}. Try again after {duration} from creation. |

These extend `rest_framework.exceptions.PermissionDenied`.

### Configuration Errors

| Exception | Base Class | When |
|-----------|-----------|------|
| `InvalidGeolocationBackend` | `django.core.exceptions.ImproperlyConfigured` | `GEOLOCATION_BACKEND` setting is misconfigured |

This is raised at startup/first use, not during API requests.

---

## Error Response Format

All API errors follow DRF's standard format:

```json
{
  "detail": "This session device is no longer valid.",
  "code": "device_not_recognized"
}
```

The `code` field is stable across versions — use it for programmatic error handling instead of matching on the message string.

---

## Catching Specific Exceptions

```python
from trusted_devices.exceptions import DeviceNotRecognized, InactiveAccount

try:
    # ... authenticate or make API call
    pass
except DeviceNotRecognized:
    # Device was revoked — redirect to login
    pass
except InactiveAccount:
    # User account was disabled — show specific message
    pass
```

---

## Custom Exception Handler

You can extend DRF's exception handler to add custom behavior for trusted device errors:

```python
from rest_framework.views import exception_handler
from trusted_devices.exceptions import DeviceNotRecognized

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, DeviceNotRecognized):
        # Add a custom header to signal the client to re-authenticate
        response['X-Device-Revoked'] = 'true'

    return response
```
