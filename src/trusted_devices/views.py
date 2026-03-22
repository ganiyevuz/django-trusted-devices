from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    inline_serializer,
    OpenApiResponse,
)
from rest_framework.decorators import action
from rest_framework.fields import CharField, IntegerField
from rest_framework.mixins import UpdateModelMixin, ListModelMixin, DestroyModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.throttling import AnonRateThrottle
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

_ERROR_401 = OpenApiResponse(
    description="Authentication failed — invalid credentials, "
    "unrecognized device, or inactive account.",
    response=inline_serializer(
        name="AuthErrorResponse",
        fields={
            "detail": CharField(),
            "code": CharField(),
        },
    ),
)

_ERROR_403 = OpenApiResponse(
    description="Permission denied — device lacks required privileges "
    "or the session is too recent.",
    response=inline_serializer(
        name="PermissionErrorResponse",
        fields={
            "detail": CharField(),
            "code": CharField(),
        },
    ),
)

_ERROR_429 = OpenApiResponse(description="Rate limit exceeded. Try again later.")


class LoginRateThrottle(AnonRateThrottle):
    """Limits login attempts to prevent brute-force and device-creation spam."""

    rate = "5/min"


@extend_schema(
    tags=["Authentication"],
    summary="Obtain token pair",
    description=(
        "Authenticate with credentials and receive access/refresh tokens "
        "along with a device_uid. A new TrustedDevice record is created."
    ),
    responses={
        200: inline_serializer(
            name="TokenObtainResponse",
            fields={
                "refresh": CharField(),
                "access": CharField(),
                "device_uid": CharField(),
            },
        ),
        401: _ERROR_401,
        429: _ERROR_429,
    },
)
class TrustedDeviceTokenObtainPairView(TokenObtainPairView):
    """View to obtain access and refresh tokens with device tracking."""

    serializer_class = TrustedDeviceTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


@extend_schema(
    tags=["Authentication"],
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token. "
        "The associated device's last_seen timestamp is updated."
    ),
    responses={
        200: inline_serializer(
            name="TokenRefreshResponse",
            fields={
                "access": CharField(),
                "refresh": CharField(help_text="Only returned when ROTATE_REFRESH_TOKENS is enabled."),
            },
        ),
        401: _ERROR_401,
    },
)
class TrustedDeviceTokenRefreshView(TokenRefreshView):
    """View to refresh access tokens while validating trusted devices."""

    serializer_class = TrustedDeviceTokenRefreshSerializer


@extend_schema(
    tags=["Authentication"],
    summary="Verify token",
    description=(
        "Verify that a token is valid and its device_uid still exists. "
        "Also checks token blacklist status if enabled."
    ),
    responses={
        200: OpenApiResponse(description="Token is valid."),
        400: OpenApiResponse(
            description="Token is blacklisted or invalid.",
            response=inline_serializer(
                name="TokenVerifyErrorResponse",
                fields={
                    "detail": CharField(),
                    "code": CharField(),
                },
            ),
        ),
        401: _ERROR_401,
    },
)
class TrustedDeviceTokenVerifyView(TokenVerifyView):
    """View to verify access token and ensure a device is still trusted."""

    serializer_class = TrustedDeviceTokenVerifySerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Trusted Devices"],
        summary="List devices",
        description=(
            "Returns all trusted devices for the authenticated user. "
            "Each device includes an `is_current` flag indicating "
            "which device is making the request."
        ),
        responses={
            200: TrustedDeviceListSerializer(many=True),
            401: _ERROR_401,
        },
    ),
    update=extend_schema(
        tags=["Trusted Devices"],
        summary="Update device",
        description="Update a device's name and permission flags.",
        responses={
            200: TrustedDeviceUpdateSerializer,
            401: _ERROR_401,
            403: _ERROR_403,
        },
    ),
    partial_update=extend_schema(
        tags=["Trusted Devices"],
        summary="Partial update device",
        description="Partially update a device's name and permission flags.",
        responses={
            200: TrustedDeviceUpdateSerializer,
            401: _ERROR_401,
            403: _ERROR_403,
        },
    ),
    destroy=extend_schema(
        tags=["Trusted Devices"],
        summary="Delete device",
        description=(
            "Revoke a specific device session. Requires the current device "
            "to have `can_delete_other_devices` permission and the target "
            "device to be older than DELETE_DELAY_MINUTES."
        ),
        responses={
            204: OpenApiResponse(description="Device deleted successfully."),
            401: _ERROR_401,
            403: _ERROR_403,
        },
    ),
    logout=extend_schema(
        tags=["Trusted Devices"],
        summary="Logout current device",
        description=(
            "Revoke the current device session. The JWT remains "
            "cryptographically valid but subsequent requests will "
            "fail device validation."
        ),
        request=None,
        responses={
            204: OpenApiResponse(description="Current device session revoked."),
            401: _ERROR_401,
        },
    ),
    revoke_all=extend_schema(
        tags=["Trusted Devices"],
        summary="Revoke all other devices",
        description=(
            "Revoke all device sessions except the current one. "
            "Returns the number of revoked sessions."
        ),
        request=None,
        responses={
            204: inline_serializer(
                name="RevokeAllResponse",
                fields={"revoked_count": IntegerField()},
            ),
            401: _ERROR_401,
        },
    ),
)
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

    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        """Revoke the current device session (logout)."""
        current_device = getattr(request.user, "current_trusted_device", None)
        if current_device:
            current_device.delete()
        return Response(status=HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="revoke-all")
    def revoke_all(self, request):
        """Revoke all other device sessions except the current one."""
        current_device = getattr(request.user, "current_trusted_device", None)
        queryset = TrustedDevice.objects.filter(user=request.user)
        if current_device:
            queryset = queryset.exclude(device_uid=current_device.device_uid)
        count, _ = queryset.delete()
        return Response({"revoked_count": count}, status=HTTP_204_NO_CONTENT)
