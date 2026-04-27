from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from tests.factories import TrustedDeviceFactory
from trusted_devices.models import TrustedDevice


@pytest.mark.django_db
class TestLoginView:
    def test_login_returns_access_refresh_and_device_uid(self, api_client, user):
        url = reverse("trusted_devices:token_obtain_pair")
        response = api_client.post(
            url,
            {"username": user.username, "password": "correcthorsebatterystaple"},
            REMOTE_ADDR="203.0.113.10",
        )
        assert response.status_code == 200
        body = response.json()
        assert "access" in body
        assert "refresh" in body
        assert "device_uid" in body

    def test_login_with_bad_password_returns_401(self, api_client, user):
        url = reverse("trusted_devices:token_obtain_pair")
        response = api_client.post(
            url,
            {"username": user.username, "password": "wrong"},
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestListView:
    def test_list_returns_only_users_devices(self, auth_client, user):
        from tests.factories import UserFactory

        TrustedDeviceFactory(user=UserFactory())  # noise
        TrustedDeviceFactory(user=user, name="Phone")

        url = reverse("trusted_devices:trusted_device-list")
        response = auth_client.get(url)
        assert response.status_code == 200
        device_uids = {d["device_uid"] for d in response.json()}
        assert all(
            TrustedDevice.objects.get(device_uid=uid).user == user
            for uid in device_uids
        )

    def test_list_marks_current_device(self, auth_client):
        url = reverse("trusted_devices:trusted_device-list")
        response = auth_client.get(url)
        assert response.status_code == 200
        rows = response.json()
        current_rows = [r for r in rows if r["is_current"]]
        assert len(current_rows) == 1
        assert current_rows[0]["device_uid"] == str(auth_client.device.device_uid)

    def test_list_unauthenticated_returns_401(self, api_client):
        url = reverse("trusted_devices:trusted_device-list")
        assert api_client.get(url).status_code == 401


@pytest.mark.django_db
class TestDestroyView:
    def _aged_device(self, user, minutes_old=2000):
        device = TrustedDeviceFactory(user=user)
        TrustedDevice.objects.filter(pk=device.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_old)
        )
        return device

    def test_cannot_delete_self_via_destroy(self, auth_client):
        url = reverse(
            "trusted_devices:trusted_device-detail",
            kwargs={"device_uid": auth_client.device.device_uid},
        )
        response = auth_client.delete(url)
        assert response.status_code == 403
        assert response.json()["code"] == "device_self_modification"

    def test_can_delete_old_other_device(self, auth_client, user):
        target = self._aged_device(user)
        url = reverse(
            "trusted_devices:trusted_device-detail",
            kwargs={"device_uid": target.device_uid},
        )
        response = auth_client.delete(url)
        assert response.status_code == 204
        assert not TrustedDevice.objects.filter(pk=target.pk).exists()

    def test_cannot_delete_recent_other_device(self, auth_client, user):
        target = TrustedDeviceFactory(user=user)
        url = reverse(
            "trusted_devices:trusted_device-detail",
            kwargs={"device_uid": target.device_uid},
        )
        response = auth_client.delete(url)
        assert response.status_code == 403
        assert response.json()["code"] == "device_session_too_recent"


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_deletes_current_device(self, auth_client):
        url = reverse("trusted_devices:trusted_device-logout")
        response = auth_client.post(url)
        assert response.status_code == 204
        assert not TrustedDevice.objects.filter(pk=auth_client.device.pk).exists()


@pytest.mark.django_db
class TestRevokeAll:
    def test_revoke_all_keeps_current_device(self, auth_client, user):
        TrustedDeviceFactory(user=user)
        TrustedDeviceFactory(user=user)

        url = reverse("trusted_devices:trusted_device-revoke-all")
        response = auth_client.post(url)
        assert response.status_code == 204
        remaining = TrustedDevice.objects.filter(user=user)
        assert remaining.count() == 1
        assert remaining.first() == auth_client.device
