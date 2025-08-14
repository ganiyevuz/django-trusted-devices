from typing import cast
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from jwt import decode, PyJWTError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from trusted_devices.models import TrustedDevice


class TrustedDeviceAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class that validates not only the user token
    but also checks the associated device via a device_uid included in the JWT payload.

    - If the token is expired and contains a device_uid, the associated TrustedDevice is deleted.
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

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken as e:
            # Attempt to decode the token without verifying the signature to extract device_uid
            try:
                unverified_payload = decode(
                    raw_token, options={"verify_signature": False}
                )
                device_uid = unverified_payload.get("device_uid")
                exp = unverified_payload.get("exp")

                # If token expired, and device_uid exists — delete that device
                if exp and datetime.fromtimestamp(exp, dt_timezone.utc) < datetime.now(
                    dt_timezone.utc
                ):
                    if device_uid:
                        TrustedDevice.objects.filter(device_uid=device_uid).delete()

                raise e
            except PyJWTError:
                raise InvalidToken

        user = self.get_user(validated_token)
        device_uid = validated_token.get("device_uid")

        if not device_uid:
            raise AuthenticationFailed("Device UID not found in token")

        try:
            device = TrustedDevice.objects.get(user=user, device_uid=device_uid)
            device.last_seen = timezone.now()
            device.save(update_fields=["last_seen"])

            # Attach the device instance to the user (not standard but useful internally)
            user.current_trusted_device = cast(TrustedDevice, device)
        except TrustedDevice.DoesNotExist:
            raise AuthenticationFailed("Unrecognized device")

        return user, validated_token
