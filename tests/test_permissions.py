from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from django.utils import timezone

from tests.factories import TrustedDeviceFactory
from trusted_devices.exceptions import (
    DeviceDeletionDisabled,
    DeviceEditingDisabled,
    DeviceLacksDeletePermission,
    DeviceLacksEditPermission,
    DeviceNotVerified,
    DeviceSelfModification,
    DeviceSessionTooRecent,
)
from trusted_devices.permissions import (
    DeletableTrustedDevicePermission,
    EditableTrustedDevicePermission,
    TrustedDevicePermission,
)


def _request_with_user(user, current_device=None):
    request = MagicMock()
    request.user = user
    if current_device is not None:
        user.current_trusted_device = current_device
    elif hasattr(user, "current_trusted_device"):
        delattr(user, "current_trusted_device")
    return request


@pytest.mark.django_db
class TestTrustedDevicePermission:
    def test_authenticated_user_with_current_device(self, user, device):
        user.current_trusted_device = device
        request = _request_with_user(user, device)
        assert TrustedDevicePermission().has_permission(request, view=None) is True

    def test_object_permission_only_owner(self, user, device):
        request = _request_with_user(user, device)
        assert TrustedDevicePermission().has_object_permission(request, None, device) is True
        other_device = TrustedDeviceFactory()
        assert TrustedDevicePermission().has_object_permission(request, None, other_device) is False


@pytest.mark.django_db
class TestDeletableTrustedDevicePermission:
    def _aged_device(self, user, minutes_old=2000):
        device = TrustedDeviceFactory(user=user)
        from trusted_devices.models import TrustedDevice
        TrustedDevice.objects.filter(pk=device.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_old)
        )
        device.refresh_from_db()
        return device

    def test_no_current_device_raises(self, user):
        target = TrustedDeviceFactory(user=user)
        request = MagicMock()
        request.user = MagicMock(spec=[])
        with pytest.raises(DeviceNotVerified):
            DeletableTrustedDevicePermission().has_object_permission(request, None, target)

    def test_self_modification_raises(self, user, device):
        request = _request_with_user(user, device)
        with pytest.raises(DeviceSelfModification):
            DeletableTrustedDevicePermission().has_object_permission(request, None, device)

    @override_settings(TRUSTED_DEVICE={"ALLOW_GLOBAL_DELETE": False})
    def test_global_disabled_raises(self, user):
        current = TrustedDeviceFactory(user=user)
        target = self._aged_device(user)
        request = _request_with_user(user, current)
        with pytest.raises(DeviceDeletionDisabled):
            DeletableTrustedDevicePermission().has_object_permission(request, None, target)

    def test_no_delete_permission_raises(self, user):
        current = TrustedDeviceFactory(user=user, can_delete_other_devices=False)
        target = self._aged_device(user)
        request = _request_with_user(user, current)
        with pytest.raises(DeviceLacksDeletePermission):
            DeletableTrustedDevicePermission().has_object_permission(request, None, target)

    def test_too_recent_raises(self, user):
        current = TrustedDeviceFactory(user=user)
        target = TrustedDeviceFactory(user=user)  # just created
        request = _request_with_user(user, current)
        with pytest.raises(DeviceSessionTooRecent):
            DeletableTrustedDevicePermission().has_object_permission(request, None, target)

    def test_eligible_returns_true(self, user):
        current = TrustedDeviceFactory(user=user)
        target = self._aged_device(user)
        request = _request_with_user(user, current)
        assert DeletableTrustedDevicePermission().has_object_permission(request, None, target) is True


@pytest.mark.django_db
class TestEditableTrustedDevicePermission:
    def _aged_device(self, user, minutes_old=120):
        from trusted_devices.models import TrustedDevice

        device = TrustedDeviceFactory(user=user)
        TrustedDevice.objects.filter(pk=device.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_old)
        )
        device.refresh_from_db()
        return device

    def test_self_modification_raises(self, user, device):
        request = _request_with_user(user, device)
        with pytest.raises(DeviceSelfModification):
            EditableTrustedDevicePermission().has_object_permission(request, None, device)

    @override_settings(TRUSTED_DEVICE={"ALLOW_GLOBAL_UPDATE": False})
    def test_global_disabled_raises(self, user):
        current = TrustedDeviceFactory(user=user)
        target = self._aged_device(user)
        request = _request_with_user(user, current)
        with pytest.raises(DeviceEditingDisabled):
            EditableTrustedDevicePermission().has_object_permission(request, None, target)

    def test_no_edit_permission_raises(self, user):
        current = TrustedDeviceFactory(user=user, can_update_other_devices=False)
        target = self._aged_device(user)
        request = _request_with_user(user, current)
        with pytest.raises(DeviceLacksEditPermission):
            EditableTrustedDevicePermission().has_object_permission(request, None, target)

    def test_too_recent_raises(self, user):
        current = TrustedDeviceFactory(user=user)
        target = TrustedDeviceFactory(user=user)  # just created
        request = _request_with_user(user, current)
        with pytest.raises(DeviceSessionTooRecent):
            EditableTrustedDevicePermission().has_object_permission(request, None, target)

    def test_eligible_returns_true(self, user):
        current = TrustedDeviceFactory(user=user)
        target = self._aged_device(user)
        request = _request_with_user(user, current)
        assert EditableTrustedDevicePermission().has_object_permission(request, None, target) is True
