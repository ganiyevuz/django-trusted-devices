# 🚨 Signals

Django Trusted Devices provides custom signals for device lifecycle events. Connect to these in your app to trigger notifications, audit logs, or security responses.

## Available Signals

### `device_created`

Fired when a new device is registered (on login).

| Argument | Type | Description |
|----------|------|-------------|
| `sender` | `TrustedDevice` | The model class |
| `user` | `User` | The user who logged in |
| `device` | `TrustedDevice` | The newly created device instance |

```python
from django.dispatch import receiver
from trusted_devices.signals import device_created

@receiver(device_created)
def on_new_device(sender, user, device, **kwargs):
    send_push_notification(
        user,
        f"New login from {device.city}, {device.country}"
    )
```

---

### `device_revoked`

Fired when a device is deleted (via API, cleanup, eviction, or logout).

| Argument | Type | Description |
|----------|------|-------------|
| `sender` | `TrustedDevice` | The model class |
| `user` | `User` | The device owner |
| `device_uid` | `UUID` | The UID of the deleted device |

```python
from django.dispatch import receiver
from trusted_devices.signals import device_revoked

@receiver(device_revoked)
def on_device_removed(sender, user, device_uid, **kwargs):
    audit_log.info(f"Device {device_uid} revoked for user {user.pk}")
```

---

### `suspicious_login`

Fired when a new device logs in from a country not seen in the user's existing devices.

| Argument | Type | Description |
|----------|------|-------------|
| `sender` | `TrustedDevice` | The model class |
| `user` | `User` | The user who logged in |
| `device` | `TrustedDevice` | The new device from an unknown country |
| `previous_countries` | `set[str]` | Countries from the user's existing devices |

```python
from django.dispatch import receiver
from trusted_devices.signals import suspicious_login

@receiver(suspicious_login)
def on_suspicious_login(sender, user, device, previous_countries, **kwargs):
    send_email(
        user.email,
        subject="Security Alert: New login from a new location",
        body=(
            f"We detected a login from {device.city}, {device.country}. "
            f"Your previous logins were from: {', '.join(previous_countries)}.\n\n"
            f"If this wasn't you, revoke this device immediately."
        ),
    )
```

---

## When Signals Fire

| Event | Signal(s) |
|-------|-----------|
| User logs in | `device_created`, possibly `suspicious_login` |
| User calls `DELETE /trusted-devices/{uid}` | `device_revoked` |
| User calls `POST /trusted-devices/logout` | `device_revoked` |
| User calls `POST /trusted-devices/revoke-all` | `device_revoked` (once per device) |
| Stale device cleanup (login or management command) | `device_revoked` (once per device) |
| Max device limit eviction | `device_revoked` (once per evicted device) |

## Registering Signal Handlers

Register your handlers in your app's `apps.py`:

```python
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = "myapp"

    def ready(self):
        from . import signal_handlers  # noqa
```
