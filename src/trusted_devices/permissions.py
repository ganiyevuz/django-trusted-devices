from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import BasePermission

from trusted_devices.models import TrustedDevice
from trusted_devices.settings import trusted_device_settings
from trusted_devices.utils import format_duration


class TrustedDevicePermission(BasePermission):
    """
    Ensures the user is authenticated and has at least one trusted device registered.
    """

    def has_permission(self, request, view):
        """
        Returns True if the user is authenticated and has any trusted device.
        """
        user = request.user
        return (
            user.is_authenticated
            and hasattr(user, "trusted_devices")
            and user.trusted_devices.exists()
        )

    def has_object_permission(self, request, view, obj: TrustedDevice):
        """
        Returns True if the user is the owner of the TrustedDevice object.
        """
        return obj.user == request.user


class DeletableTrustedDevicePermission(BasePermission):
    """
    Allows deletion of trusted devices under these conditions:
    - Global delete setting is enabled.
    - Current device has permission to delete others.
    - Target device is older than the allowed delay period.
    """

    message = (
        "You are not allowed to delete this device. "
        "Either global deletion is disabled, your current device lacks permission, "
        "or the session is too new. Try again later from a trusted device."
    )

    def has_object_permission(self, request, view, obj: TrustedDevice):
        if not trusted_device_settings.ALLOW_GLOBAL_DELETE:
            self.message = (
                "Device deletion is globally disabled by the system administrator."
            )
            return False

        current_device: TrustedDevice = getattr(
            request.user, "current_trusted_device", None
        )
        if not current_device:
            self.message = (
                "Your current session could not be verified as a trusted device."
            )
            return False

        if not current_device.can_delete_other_devices:
            self.message = (
                "Your current device does not have permission to delete other sessions. "
                "Please use a device with elevated privileges."
            )
            return False

        delay = timedelta(minutes=trusted_device_settings.DELETE_DELAY_MINUTES)
        if obj.created_at > timezone.now() - delay:
            self.message = (
                f"This session is too recent to be deleted. "
                f"Try again after {format_duration(trusted_device_settings.DELETE_DELAY_MINUTES)} minutes from creation."
            )
            return False

        return True


class EditableTrustedDevicePermission(BasePermission):
    """
    Allows editing trusted devices under these conditions:
    - Global update setting is enabled.
    - Current device has permission to update others.
    - Target device is older than the allowed delay period.
    """

    message = (
        "You are not allowed to update this device. "
        "Either global editing is disabled, your current device lacks permission, "
        "or the session is too recent. Try again later from a trusted device."
    )

    def has_object_permission(self, request, view, obj: TrustedDevice):
        if not trusted_device_settings.ALLOW_GLOBAL_UPDATE:
            self.message = (
                "Device editing is globally disabled by the system administrator."
            )
            return False

        current_device: TrustedDevice = getattr(
            request.user, "current_trusted_device", None
        )
        if not current_device:
            self.message = (
                "Your current session could not be verified as a trusted device."
            )
            return False

        if not current_device.can_update_other_devices:
            self.message = (
                "Your current device does not have permission to modify other sessions. "
                "Use a device with the required privileges."
            )
            return False

        delay = timedelta(minutes=trusted_device_settings.UPDATE_DELAY_MINUTES)
        if obj.created_at > timezone.now() - delay:
            self.message = (
                f"This session is too recent to edit. "
                f"Please wait {format_duration(trusted_device_settings.UPDATE_DELAY_MINUTES)} after creation."
            )
            return False

        return True
