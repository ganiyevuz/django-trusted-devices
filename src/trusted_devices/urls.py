from django.urls import path, include
from trusted_devices.views import (
    TrustedDeviceTokenObtainPairView,
    TrustedDeviceTokenVerifyView,
    TrustedDeviceTokenRefreshView,
    TrustedDeviceViewSet,
)

from rest_framework.routers import SimpleRouter

app_name = "trusted_devices"

router = SimpleRouter(trailing_slash=False)
router.register("trusted-devices", TrustedDeviceViewSet, basename="trusted_device")
urlpatterns = [
    path("", include(router.urls)),
    path(
        "api/token",
        TrustedDeviceTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/token/refresh",
        TrustedDeviceTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "api/token/verify", TrustedDeviceTokenVerifyView.as_view(), name="token_verify"
    ),
]
