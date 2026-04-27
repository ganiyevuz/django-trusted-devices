from uuid import UUID

import pytest

from tests.factories import TrustedDeviceFactory
from trusted_devices.models import TrustedDevice


@pytest.mark.django_db
class TestTrustedDeviceModel:
    def test_device_uid_is_uuid_primary_key(self):
        device = TrustedDeviceFactory()
        assert isinstance(device.device_uid, UUID)
        assert TrustedDevice._meta.pk.name == "device_uid"

    def test_default_name_is_empty_string(self):
        device = TrustedDeviceFactory(name="")
        assert device.name == ""

    def test_str_uses_name_when_present(self, user):
        device = TrustedDeviceFactory(user=user, name="Work Laptop")
        assert "Work Laptop" in str(device)
        assert str(user) in str(device)

    def test_str_falls_back_to_uid(self, user):
        device = TrustedDeviceFactory(user=user, name="")
        assert str(device.device_uid) in str(device)

    def test_ordering_is_newest_first(self):
        first = TrustedDeviceFactory()
        second = TrustedDeviceFactory()
        ordered = list(TrustedDevice.objects.all())
        assert ordered[0] == second
        assert ordered[1] == first

    def test_user_cascade_deletes_devices(self, user):
        TrustedDeviceFactory(user=user)
        TrustedDeviceFactory(user=user)
        assert TrustedDevice.objects.filter(user=user).count() == 2
        user.delete()
        assert TrustedDevice.objects.filter(user_id=user.pk).count() == 0
