import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import TrustedDeviceFactory, UserFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    user = UserFactory()
    user.set_password("correcthorsebatterystaple")
    user.save()
    return user


@pytest.fixture
def device(db, user):
    return TrustedDeviceFactory(user=user)


@pytest.fixture
def auth_client(api_client, user, device):
    refresh = RefreshToken.for_user(user)
    refresh["device_uid"] = str(device.device_uid)
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}",
        REMOTE_ADDR=device.last_ip,
    )
    api_client.user = user
    api_client.device = device
    api_client.refresh = refresh
    return api_client
