from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import TrustedDeviceFactory, UserFactory
from trusted_devices.authentication import TrustedDeviceAuthentication
from trusted_devices.exceptions import (
    DeviceCompromised,
    DeviceNotRecognized,
    DeviceUIDMissing,
)
from trusted_devices.models import TrustedDevice


def _request_with_token(token: str, ip: str = "203.0.113.10"):
    factory = APIRequestFactory()
    request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}", REMOTE_ADDR=ip)
    return request


@pytest.mark.django_db
class TestTrustedDeviceAuthentication:
    def test_no_header_returns_none(self):
        factory = APIRequestFactory()
        request = factory.get("/")
        assert TrustedDeviceAuthentication().authenticate(request) is None

    def test_authenticates_with_valid_device(self, user):
        device = TrustedDeviceFactory(user=user, last_ip="203.0.113.10")
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)

        request = _request_with_token(str(refresh.access_token), ip="203.0.113.10")
        authed_user, token = TrustedDeviceAuthentication().authenticate(request)

        assert authed_user.pk == user.pk
        assert authed_user.current_trusted_device.device_uid == device.device_uid

    def test_missing_device_uid_in_token_raises(self, user):
        refresh = RefreshToken.for_user(user)
        request = _request_with_token(str(refresh.access_token))
        with pytest.raises(DeviceUIDMissing):
            TrustedDeviceAuthentication().authenticate(request)

    def test_unknown_device_uid_raises(self, user):
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = "00000000-0000-0000-0000-000000000000"
        request = _request_with_token(str(refresh.access_token))
        with pytest.raises(DeviceNotRecognized):
            TrustedDeviceAuthentication().authenticate(request)

    def test_device_belonging_to_other_user_is_rejected(self, user):
        other_user = UserFactory()
        their_device = TrustedDeviceFactory(user=other_user)
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(their_device.device_uid)
        request = _request_with_token(str(refresh.access_token))
        with pytest.raises(DeviceNotRecognized):
            TrustedDeviceAuthentication().authenticate(request)

    def test_concurrent_ip_within_window_invalidates_device(self, user):
        device = TrustedDeviceFactory(
            user=user,
            ip_address="203.0.113.10",
            last_ip="203.0.113.10",
        )
        TrustedDevice.objects.filter(pk=device.pk).update(last_seen=timezone.now())

        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)
        request = _request_with_token(str(refresh.access_token), ip="198.51.100.99")

        with pytest.raises(DeviceCompromised):
            TrustedDeviceAuthentication().authenticate(request)
        assert not TrustedDevice.objects.filter(pk=device.pk).exists()

    def test_concurrent_ip_outside_window_only_updates_last_ip(self, user):
        device = TrustedDeviceFactory(user=user, last_ip="203.0.113.10")
        old = timezone.now() - timedelta(minutes=10)
        TrustedDevice.objects.filter(pk=device.pk).update(last_seen=old)

        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)
        request = _request_with_token(str(refresh.access_token), ip="198.51.100.99")

        TrustedDeviceAuthentication().authenticate(request)
        device.refresh_from_db()
        assert device.last_ip == "198.51.100.99"

    @override_settings(TRUSTED_DEVICE={"DETECT_CONCURRENT_SESSIONS": False})
    def test_detection_can_be_disabled(self, user):
        device = TrustedDeviceFactory(user=user, last_ip="203.0.113.10")
        TrustedDevice.objects.filter(pk=device.pk).update(last_seen=timezone.now())
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)
        request = _request_with_token(str(refresh.access_token), ip="198.51.100.99")

        TrustedDeviceAuthentication().authenticate(request)
        device.refresh_from_db()
        assert device.last_ip == "198.51.100.99"

    def test_invalid_jwt_raises_auth_failed(self):
        request = _request_with_token("not.a.real.token")
        with pytest.raises(AuthenticationFailed):
            TrustedDeviceAuthentication().authenticate(request)
