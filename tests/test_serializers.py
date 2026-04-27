from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import TrustedDeviceFactory, UserFactory
from trusted_devices.exceptions import (
    DeviceCompromised,
    DeviceNotRecognized,
    DevicePermissionEscalation,
    InactiveAccount,
)
from trusted_devices.models import TrustedDevice
from trusted_devices.serializers import (
    TrustedDeviceListSerializer,
    TrustedDeviceTokenObtainPairSerializer,
    TrustedDeviceTokenRefreshSerializer,
    TrustedDeviceTokenVerifySerializer,
    TrustedDeviceUpdateSerializer,
)


def _make_request(ip="203.0.113.10", ua="pytest"):
    factory = APIRequestFactory()
    request = factory.post("/", HTTP_USER_AGENT=ua, REMOTE_ADDR=ip)
    return request


@pytest.mark.django_db
class TestTokenObtainPairSerializer:
    def test_login_creates_device_with_uid_in_token(self, user):
        request = _make_request()
        serializer = TrustedDeviceTokenObtainPairSerializer(
            data={"username": user.username, "password": "correcthorsebatterystaple"},
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        data = serializer.validated_data

        assert "device_uid" in data
        assert TrustedDevice.objects.filter(device_uid=data["device_uid"]).exists()
        device = TrustedDevice.objects.get(device_uid=data["device_uid"])
        assert device.user == user
        assert device.ip_address == "203.0.113.10"
        assert device.last_ip == "203.0.113.10"

    def test_login_includes_geolocation_from_backend(self, user):
        request = _make_request()
        serializer = TrustedDeviceTokenObtainPairSerializer(
            data={"username": user.username, "password": "correcthorsebatterystaple"},
            context={"request": request},
        )
        assert serializer.is_valid()
        device = TrustedDevice.objects.get(device_uid=serializer.validated_data["device_uid"])
        assert device.country == "Testland"

    @override_settings(TRUSTED_DEVICE={"MAX_DEVICES_PER_USER": 2, "GEOLOCATION_BACKEND": "tests.fakes.fake_geolocation"})
    def test_max_devices_evicts_oldest(self, user):
        TrustedDeviceFactory(user=user)
        TrustedDeviceFactory(user=user)
        assert TrustedDevice.objects.filter(user=user).count() == 2

        request = _make_request()
        serializer = TrustedDeviceTokenObtainPairSerializer(
            data={"username": user.username, "password": "correcthorsebatterystaple"},
            context={"request": request},
        )
        assert serializer.is_valid()
        # Total is still capped at max_devices (2)
        assert TrustedDevice.objects.filter(user=user).count() == 2

    def test_login_cleans_up_stale_devices(self, user):
        old_device = TrustedDeviceFactory(user=user)
        TrustedDevice.objects.filter(pk=old_device.pk).update(
            last_seen=timezone.now() - timedelta(days=365)
        )

        request = _make_request()
        serializer = TrustedDeviceTokenObtainPairSerializer(
            data={"username": user.username, "password": "correcthorsebatterystaple"},
            context={"request": request},
        )
        assert serializer.is_valid()
        # Old stale device removed, new device created → 1 remains
        assert TrustedDevice.objects.filter(user=user).count() == 1

    def test_missing_request_raises(self, user):
        serializer = TrustedDeviceTokenObtainPairSerializer(
            data={"username": user.username, "password": "correcthorsebatterystaple"},
            context={},
        )
        with pytest.raises(ValueError):
            serializer.is_valid(raise_exception=False)
            serializer.validated_data


@pytest.mark.django_db
class TestTokenRefreshSerializer:
    def test_refresh_succeeds_for_known_device(self, user):
        device = TrustedDeviceFactory(user=user)
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)

        request = _make_request(ip=device.last_ip)
        serializer = TrustedDeviceTokenRefreshSerializer(
            data={"refresh": str(refresh)},
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        assert "access" in serializer.validated_data

    def test_refresh_unknown_device_raises(self, user):
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = "00000000-0000-0000-0000-000000000000"
        serializer = TrustedDeviceTokenRefreshSerializer(
            data={"refresh": str(refresh)},
            context={"request": _make_request()},
        )
        with pytest.raises(DeviceNotRecognized):
            serializer.is_valid(raise_exception=True)

    def test_refresh_device_belonging_to_other_user_raises(self, user):
        other = UserFactory()
        their_device = TrustedDeviceFactory(user=other)
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(their_device.device_uid)
        serializer = TrustedDeviceTokenRefreshSerializer(
            data={"refresh": str(refresh)},
            context={"request": _make_request()},
        )
        with pytest.raises(DeviceNotRecognized):
            serializer.is_valid(raise_exception=True)

    def test_refresh_concurrent_ip_invalidates(self, user):
        device = TrustedDeviceFactory(user=user, last_ip="203.0.113.10")
        TrustedDevice.objects.filter(pk=device.pk).update(last_seen=timezone.now())
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)

        request = _make_request(ip="198.51.100.99")
        serializer = TrustedDeviceTokenRefreshSerializer(
            data={"refresh": str(refresh)},
            context={"request": request},
        )
        with pytest.raises(DeviceCompromised):
            serializer.is_valid(raise_exception=True)
        assert not TrustedDevice.objects.filter(pk=device.pk).exists()

    def test_refresh_inactive_user_raises(self, user):
        device = TrustedDeviceFactory(user=user)
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)
        user.is_active = False
        user.save()

        request = _make_request(ip=device.last_ip)
        serializer = TrustedDeviceTokenRefreshSerializer(
            data={"refresh": str(refresh)},
            context={"request": request},
        )
        with pytest.raises(InactiveAccount):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestTokenVerifySerializer:
    def test_verify_valid_token(self, user):
        device = TrustedDeviceFactory(user=user)
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(device.device_uid)

        serializer = TrustedDeviceTokenVerifySerializer(
            data={"token": str(refresh.access_token)},
        )
        assert serializer.is_valid(), serializer.errors

    def test_verify_unknown_device_raises(self, user):
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = "00000000-0000-0000-0000-000000000000"
        serializer = TrustedDeviceTokenVerifySerializer(
            data={"token": str(refresh.access_token)},
        )
        with pytest.raises(DeviceNotRecognized):
            serializer.is_valid(raise_exception=True)

    def test_verify_device_belonging_to_other_user_raises(self, user):
        other = UserFactory()
        their_device = TrustedDeviceFactory(user=other)
        refresh = RefreshToken.for_user(user)
        refresh["device_uid"] = str(their_device.device_uid)
        serializer = TrustedDeviceTokenVerifySerializer(
            data={"token": str(refresh.access_token)},
        )
        with pytest.raises(DeviceNotRecognized):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestUpdateSerializer:
    def test_cannot_grant_delete_perm_when_lacking(self, user):
        current = TrustedDeviceFactory(user=user, can_delete_other_devices=False)
        target = TrustedDeviceFactory(user=user)
        request = MagicMock()
        request.user = user
        request.user.current_trusted_device = current

        serializer = TrustedDeviceUpdateSerializer(
            instance=target,
            data={"can_delete_other_devices": True},
            partial=True,
            context={"request": request},
        )
        with pytest.raises(DevicePermissionEscalation):
            serializer.is_valid(raise_exception=True)

    def test_cannot_grant_update_perm_when_lacking(self, user):
        current = TrustedDeviceFactory(user=user, can_update_other_devices=False)
        target = TrustedDeviceFactory(user=user)
        request = MagicMock()
        request.user = user
        request.user.current_trusted_device = current

        serializer = TrustedDeviceUpdateSerializer(
            instance=target,
            data={"can_update_other_devices": True},
            partial=True,
            context={"request": request},
        )
        with pytest.raises(DevicePermissionEscalation):
            serializer.is_valid(raise_exception=True)

    def test_can_revoke_perm_without_having_it(self, user):
        current = TrustedDeviceFactory(user=user, can_delete_other_devices=False)
        target = TrustedDeviceFactory(user=user)
        request = MagicMock()
        request.user = user
        request.user.current_trusted_device = current

        serializer = TrustedDeviceUpdateSerializer(
            instance=target,
            data={"can_delete_other_devices": False},
            partial=True,
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestListSerializer:
    def test_is_current_flag_for_current_device(self, user, device):
        user.current_trusted_device = device
        request = MagicMock()
        request.user = user

        serializer = TrustedDeviceListSerializer(instance=device, context={"request": request})
        assert serializer.data["is_current"] is True

    def test_is_current_false_for_other_device(self, user, device):
        other = TrustedDeviceFactory(user=user)
        user.current_trusted_device = device
        request = MagicMock()
        request.user = user

        serializer = TrustedDeviceListSerializer(instance=other, context={"request": request})
        assert serializer.data["is_current"] is False
