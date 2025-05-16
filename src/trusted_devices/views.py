from rest_framework.mixins import UpdateModelMixin, ListModelMixin, DestroyModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from trusted_devices.models import TrustedDevice
from trusted_devices.permissions import (
    TrustedDevicePermission,
    DeletableTrustedDevicePermission,
    EditableTrustedDevicePermission,
)
from trusted_devices.serializers import (
    TrustedDeviceTokenObtainPairSerializer,
    TrustedDeviceTokenRefreshSerializer,
    TrustedDeviceTokenVerifySerializer,
    TrustedDeviceListSerializer,
    TrustedDeviceUpdateSerializer,
)


class TrustedDeviceTokenObtainPairView(TokenObtainPairView):
    """View to obtain access and refresh tokens with device tracking."""

    serializer_class = TrustedDeviceTokenObtainPairSerializer


class TrustedDeviceTokenRefreshView(TokenRefreshView):
    """View to refresh access tokens while validating trusted devices."""

    serializer_class = TrustedDeviceTokenRefreshSerializer


class TrustedDeviceTokenVerifyView(TokenVerifyView):
    """View to verify access token and ensure a device is still trusted."""

    serializer_class = TrustedDeviceTokenVerifySerializer


class TrustedDeviceViewSet(
    UpdateModelMixin, DestroyModelMixin, ListModelMixin, GenericViewSet
):
    """
    ViewSet for listing, updating, and deleting TrustedDevice instances
    belonging to the authenticated user.
    """

    permission_classes = [TrustedDevicePermission]
    serializer_class = TrustedDeviceListSerializer
    lookup_url_kwarg = "device_uid"
    lookup_field = "device_uid"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TrustedDevice.objects.none()
        return TrustedDevice.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return TrustedDeviceUpdateSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        permission_classes = self.permission_classes.copy()

        if self.action == "destroy":
            permission_classes += [DeletableTrustedDevicePermission]
        elif self.action in ["update", "partial_update"]:
            permission_classes += [EditableTrustedDevicePermission]

        return [permission() for permission in permission_classes]
