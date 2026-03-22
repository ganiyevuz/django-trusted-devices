from typing import cast

from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from trusted_devices.exceptions import DeviceNotRecognized, DeviceUIDMissing
from trusted_devices.models import TrustedDevice


class TrustedDeviceAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class that validates not only the user token
    but also checks the associated device via a device_uid included in the JWT payload.

    - If the token is valid and the device is recognized, the last_seen timestamp is updated.
    - Adds the TrustedDevice instance to the user as `current_trusted_device` for further use.
    """

    def authenticate(self, request):
        """
        Authenticates the request by validating the JWT and verifying the device.
        Returns a (user, token) tuple or raises AuthenticationFailed/InvalidToken exceptions.
        """
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        user = self.get_user(validated_token)
        device_uid = validated_token.get("device_uid")

        if not device_uid:
            raise DeviceUIDMissing()

        device = TrustedDevice.objects.filter(
            user=user, device_uid=device_uid
        ).first()

        if not device:
            raise DeviceNotRecognized()

        device.last_seen = timezone.now()
        device.save(update_fields=["last_seen"])

        user.current_trusted_device = cast(TrustedDevice, device)

        return user, validated_token
