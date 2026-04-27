from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from tests.factories import TrustedDeviceFactory
from trusted_devices.models import TrustedDevice


@pytest.mark.django_db
class TestCleanupDevicesCommand:
    def _make_stale(self, user, days_old):
        device = TrustedDeviceFactory(user=user)
        TrustedDevice.objects.filter(pk=device.pk).update(
            last_seen=timezone.now() - timedelta(days=days_old)
        )
        return device

    def test_dry_run_does_not_delete(self, user):
        self._make_stale(user, 365)
        out = StringIO()
        call_command("cleanup_devices", "--dry-run", stdout=out)
        assert TrustedDevice.objects.filter(user=user).count() == 1
        assert "DRY RUN" in out.getvalue()

    def test_default_uses_refresh_token_lifetime(self, user):
        self._make_stale(user, 365)
        TrustedDeviceFactory(user=user)  # fresh
        call_command("cleanup_devices", stdout=StringIO())
        remaining = TrustedDevice.objects.filter(user=user)
        assert remaining.count() == 1

    def test_days_override(self, user):
        self._make_stale(user, 10)
        TrustedDeviceFactory(user=user)  # fresh
        call_command("cleanup_devices", "--days", "5", stdout=StringIO())
        remaining = TrustedDevice.objects.filter(user=user)
        assert remaining.count() == 1
