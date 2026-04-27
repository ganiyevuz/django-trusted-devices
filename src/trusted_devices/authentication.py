import logging
from datetime import timedelta
from typing import cast

from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from trusted_devices.exceptions import (
    DeviceCompromised,
    DeviceNotRecognized,
    DeviceUIDMissing,
)
from trusted_devices.models import TrustedDevice
from trusted_devices.settings import trusted_device_settings
from trusted_devices.utils import get_client_ip

logger = logging.getLogger(__name__)


class TrustedDeviceAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that validates the user token and verifies
    the embedded device_uid against a TrustedDevice record.

    On every authenticated request:
    - Loads the device, ensures it belongs to the token's user.
    - If DETECT_CONCURRENT_SESSIONS is enabled, compares the request IP to
      the device's last_ip within CONCURRENT_SESSION_WINDOW_SECONDS. A
      mismatch within the window deletes the device (kicking both sessions)
      and emits the device_compromised signal.
    - Updates last_seen and last_ip.
    - Attaches the device to the user as `current_trusted_device`.
    """

    def authenticate(self, request):
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

        current_ip = get_client_ip(request)

        if self._is_concurrent_session_hijack(device, current_ip):
            previous_ip = device.last_ip or device.ip_address
            logger.warning(
                "Concurrent session hijack detected for user %s device %s: "
                "previous_ip=%s current_ip=%s",
                user.pk,
                device.device_uid,
                previous_ip,
                current_ip,
            )
            device_uid_value = device.device_uid
            device.delete()
            from trusted_devices.signals import device_compromised

            device_compromised.send(
                sender=TrustedDevice,
                user=user,
                device_uid=device_uid_value,
                previous_ip=previous_ip,
                current_ip=current_ip,
            )
            raise DeviceCompromised()

        device.last_seen = timezone.now()
        if current_ip:
            device.last_ip = current_ip
        device.save(update_fields=["last_seen", "last_ip"])

        user.current_trusted_device = cast(TrustedDevice, device)

        return user, validated_token

    @staticmethod
    def _is_concurrent_session_hijack(device: TrustedDevice, current_ip: str) -> bool:
        if not trusted_device_settings.DETECT_CONCURRENT_SESSIONS:
            return False
        if not current_ip or not device.last_ip:
            return False
        if current_ip == device.last_ip:
            return False

        window = timedelta(
            seconds=trusted_device_settings.CONCURRENT_SESSION_WINDOW_SECONDS
        )
        return device.last_seen >= timezone.now() - window
