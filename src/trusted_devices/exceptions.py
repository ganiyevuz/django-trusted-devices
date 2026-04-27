from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError


class InvalidGeolocationBackend(ImproperlyConfigured):
    pass


class DeviceUIDMissing(AuthenticationFailed):
    default_detail = "Device UID not found in token."
    default_code = "device_uid_missing"


class DeviceNotRecognized(AuthenticationFailed):
    default_detail = "This session device is no longer valid."
    default_code = "device_not_recognized"


class DeviceCompromised(AuthenticationFailed):
    default_detail = (
        "Concurrent session use detected from a different IP. "
        "This session has been invalidated. Please log in again."
    )
    default_code = "device_compromised"


class InactiveAccount(AuthenticationFailed):
    default_detail = "User account is inactive."
    default_code = "inactive_account"


class TokenBlacklisted(ValidationError):
    default_detail = "Token has been blacklisted."
    default_code = "token_blacklisted"


class DeviceDeletionDisabled(PermissionDenied):
    default_detail = "Device deletion is globally disabled by the system administrator."
    default_code = "device_deletion_disabled"


class DeviceEditingDisabled(PermissionDenied):
    default_detail = "Device editing is globally disabled by the system administrator."
    default_code = "device_editing_disabled"


class DeviceLacksDeletePermission(PermissionDenied):
    default_detail = (
        "Your current device does not have permission to delete other sessions. "
        "Please use a device with elevated privileges."
    )
    default_code = "device_lacks_delete_permission"


class DeviceLacksEditPermission(PermissionDenied):
    default_detail = (
        "Your current device does not have permission to modify other sessions. "
        "Use a device with the required privileges."
    )
    default_code = "device_lacks_edit_permission"


class DeviceSessionTooRecent(PermissionDenied):
    default_code = "device_session_too_recent"

    def __init__(self, action, duration_text):
        detail = (
            f"This session is too recent to be {action}. "
            f"Try again after {duration_text} from creation."
        )
        super().__init__(detail=detail)


class DeviceNotVerified(PermissionDenied):
    default_detail = "Your current session could not be verified as a trusted device."
    default_code = "device_not_verified"


class DeviceSelfModification(PermissionDenied):
    default_detail = (
        "You cannot modify or delete your current device this way. "
        "Use the logout endpoint to revoke your own session."
    )
    default_code = "device_self_modification"


class DevicePermissionEscalation(PermissionDenied):
    default_detail = (
        "You cannot grant permissions that your current device does not have."
    )
    default_code = "device_permission_escalation"
