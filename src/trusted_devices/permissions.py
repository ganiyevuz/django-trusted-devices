from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import BasePermission

from trusted_devices.exceptions import (
    DeviceDeletionDisabled,
    DeviceEditingDisabled,
    DeviceLacksDeletePermission,
    DeviceLacksEditPermission,
    DeviceNotVerified,
    DeviceSessionTooRecent,
)
from trusted_devices.models import TrustedDevice
from trusted_devices.settings import trusted_device_settings
from trusted_devices.utils import format_duration


class TrustedDevicePermission(BasePermission):
    """
    Ensures the user is authenticated and has a current trusted device
    (set by TrustedDeviceAuthentication).
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "current_trusted_device")
        )

    def has_object_permission(self, request, view, obj: TrustedDevice):
        return obj.user_id == request.user.pk


class DeletableTrustedDevicePermission(BasePermission):
    """
    Allows deletion of trusted devices under these conditions:
    - Global delete setting is enabled.
    - Current device has permission to delete others.
    - Target device is older than the allowed delay period.
    """

    def has_object_permission(self, request, view, obj: TrustedDevice):
        if not trusted_device_settings.ALLOW_GLOBAL_DELETE:
            raise DeviceDeletionDisabled()

        current_device: TrustedDevice = getattr(
            request.user, "current_trusted_device", None
        )
        if not current_device:
            raise DeviceNotVerified()

        if not current_device.can_delete_other_devices:
            raise DeviceLacksDeletePermission()

        delay = timedelta(minutes=trusted_device_settings.DELETE_DELAY_MINUTES)
        if obj.created_at > timezone.now() - delay:
            raise DeviceSessionTooRecent(
                action="deleted",
                duration_text=format_duration(
                    trusted_device_settings.DELETE_DELAY_MINUTES
                ),
            )

        return True


class EditableTrustedDevicePermission(BasePermission):
    """
    Allows editing trusted devices under these conditions:
    - Global update setting is enabled.
    - Current device has permission to update others.
    - Target device is older than the allowed delay period.
    """

    def has_object_permission(self, request, view, obj: TrustedDevice):
        if not trusted_device_settings.ALLOW_GLOBAL_UPDATE:
            raise DeviceEditingDisabled()

        current_device: TrustedDevice = getattr(
            request.user, "current_trusted_device", None
        )
        if not current_device:
            raise DeviceNotVerified()

        if not current_device.can_update_other_devices:
            raise DeviceLacksEditPermission()

        delay = timedelta(minutes=trusted_device_settings.UPDATE_DELAY_MINUTES)
        if obj.created_at > timezone.now() - delay:
            raise DeviceSessionTooRecent(
                action="edited",
                duration_text=format_duration(
                    trusted_device_settings.UPDATE_DELAY_MINUTES
                ),
            )

        return True
