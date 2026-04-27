from unittest.mock import MagicMock

import pytest

from tests.factories import TrustedDeviceFactory
from trusted_devices.models import TrustedDevice
from trusted_devices.signals import (
    device_created,
    device_revoked,
    suspicious_login,
)


@pytest.fixture
def created_handler():
    handler = MagicMock()
    device_created.connect(handler, sender=TrustedDevice)
    yield handler
    device_created.disconnect(handler, sender=TrustedDevice)


@pytest.fixture
def revoked_handler():
    handler = MagicMock()
    device_revoked.connect(handler, sender=TrustedDevice)
    yield handler
    device_revoked.disconnect(handler, sender=TrustedDevice)


@pytest.fixture
def suspicious_handler():
    handler = MagicMock()
    suspicious_login.connect(handler, sender=TrustedDevice)
    yield handler
    suspicious_login.disconnect(handler, sender=TrustedDevice)


@pytest.mark.django_db
def test_device_created_signal_fires_once(user, created_handler):
    TrustedDeviceFactory(user=user)
    assert created_handler.call_count == 1


@pytest.mark.django_db
def test_device_revoked_signal_fires_on_delete(user, revoked_handler):
    device = TrustedDeviceFactory(user=user)
    device.delete()
    assert revoked_handler.call_count == 1


@pytest.mark.django_db
def test_suspicious_login_fires_for_new_country(user, suspicious_handler):
    TrustedDeviceFactory(user=user, country="Testland")
    TrustedDeviceFactory(user=user, country="Otherland")
    assert suspicious_handler.call_count == 1
    args = suspicious_handler.call_args.kwargs
    assert args["device"].country == "Otherland"
    assert "Testland" in args["previous_countries"]


@pytest.mark.django_db
def test_suspicious_login_skipped_for_first_device(user, suspicious_handler):
    TrustedDeviceFactory(user=user, country="Testland")
    assert suspicious_handler.call_count == 0


@pytest.mark.django_db
def test_suspicious_login_skipped_for_known_country(user, suspicious_handler):
    TrustedDeviceFactory(user=user, country="Testland")
    TrustedDeviceFactory(user=user, country="Testland")
    assert suspicious_handler.call_count == 0
