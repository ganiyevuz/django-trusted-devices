import logging
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
    TokenVerifySerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import UntypedToken

from trusted_devices.exceptions import (
    DeviceNotRecognized,
    InactiveAccount,
    TokenBlacklisted,
)
from trusted_devices.models import TrustedDevice
from trusted_devices.settings import trusted_device_settings
from trusted_devices.utils import get_client_ip, get_geolocation_backend

logger = logging.getLogger(__name__)


class TrustedDeviceListSerializer(ModelSerializer):
    """Serializer for listing TrustedDevice instances."""

    is_current = SerializerMethodField()

    class Meta:
        model = TrustedDevice
        fields = [
            "device_uid",
            "name",
            "user_agent",
            "ip_address",
            "country",
            "region",
            "city",
            "last_seen",
            "created_at",
            "is_current",
        ]
        read_only_fields = fields

    def get_is_current(self, obj: TrustedDevice) -> bool:
        request = self.context.get("request")
        if not request or not hasattr(request.user, "current_trusted_device"):
            return False
        return obj.device_uid == request.user.current_trusted_device.device_uid


class TrustedDeviceUpdateSerializer(ModelSerializer):
    """Serializer for updating TrustedDevice instances."""

    class Meta:
        model = TrustedDevice
        fields = ["name", "can_delete_other_devices", "can_update_other_devices"]


class TrustedDeviceTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer that adds device_uid to token payload
    and registers the trusted device on login.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        request = self.context.get("request")
        if not request or not hasattr(request, "META"):
            raise ValueError("Request object is required in the context.")

        user_agent = request.META.get("HTTP_USER_AGENT", "")
        ip_address = get_client_ip(request)
        geolocation_fn = get_geolocation_backend()
        location_data = geolocation_fn(ip_address)

        device_uid = str(uuid4())

        # Add device_uid to token
        refresh = self.get_token(self.user)
        refresh["device_uid"] = device_uid

        # Enforce max device limit — evict oldest device if at capacity
        self._enforce_device_limit(self.user)

        # Save TrustedDevice instance with location data pre-filled
        # to avoid the pre_save signal making a duplicate geolocation call
        TrustedDevice.objects.create(
            user=self.user,
            device_uid=device_uid,
            user_agent=user_agent,
            ip_address=ip_address,
            country=location_data.get("country"),
            region=location_data.get("region"),
            city=location_data.get("city"),
        )

        # Clean up stale devices whose refresh tokens have expired
        self._cleanup_stale_devices(self.user)

        data.update(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "device_uid": device_uid,
            }
        )

        return data

    @staticmethod
    def _enforce_device_limit(user):
        """
        If MAX_DEVICES_PER_USER is set, removes the oldest devices
        (by last_seen) to make room for the new one.
        """
        max_devices = trusted_device_settings.MAX_DEVICES_PER_USER
        if not max_devices:
            return

        device_count = TrustedDevice.objects.filter(user=user).count()
        if device_count >= max_devices:
            # Keep the (max_devices - 1) most recently seen, delete the rest
            devices_to_keep = (
                TrustedDevice.objects.filter(user=user)
                .order_by("-last_seen")
                .values_list("device_uid", flat=True)[: max_devices - 1]
            )
            evicted, _ = (
                TrustedDevice.objects.filter(user=user)
                .exclude(device_uid__in=list(devices_to_keep))
                .delete()
            )
            if evicted:
                logger.info(
                    "Evicted %d device(s) for user %s (limit: %d)",
                    evicted,
                    user.pk,
                    max_devices,
                )

    @staticmethod
    def _cleanup_stale_devices(user):
        """
        Removes devices that haven't been seen since the refresh token
        lifetime expired. These are orphaned sessions where the user
        never refreshed and logged in again instead.
        """
        refresh_lifetime = api_settings.REFRESH_TOKEN_LIFETIME
        cutoff = timezone.now() - refresh_lifetime
        stale_count, _ = TrustedDevice.objects.filter(
            user=user, last_seen__lt=cutoff
        ).delete()
        if stale_count:
            logger.info(
                "Cleaned up %d stale device(s) for user %s", stale_count, user.pk
            )


class TrustedDeviceTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Custom refresh serializer that updates last_seen on the TrustedDevice
    and validates device ownership.
    """

    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        refresh = self.token_class(attrs["refresh"])
        device_uid = refresh.payload.get("device_uid")

        if not TrustedDevice.objects.filter(device_uid=device_uid).exists():
            raise DeviceNotRecognized()

        # Use update() to avoid triggering pre_save signal
        TrustedDevice.objects.filter(device_uid=device_uid).update(
            last_seen=timezone.now()
        )

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = (
            get_user_model()
            .objects.filter(**{api_settings.USER_ID_FIELD: user_id})
            .first()
        )

        if not user or not api_settings.USER_AUTHENTICATION_RULE(user):
            raise InactiveAccount()

        data = {"access": str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    logger.debug("Token blacklisting not enabled, skipping.")

            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()

            data["refresh"] = str(refresh)

        return data


class TrustedDeviceTokenVerifySerializer(TokenVerifySerializer):
    """
    Custom verify serializer that checks whether the device_uid in the token
    belongs to a known trusted device.
    """

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        token = UntypedToken(attrs["token"])

        if (
            api_settings.BLACKLIST_AFTER_ROTATION
            and "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS
        ):
            jti = token.get(api_settings.JTI_CLAIM)
            if self._is_token_blacklisted(jti):
                raise TokenBlacklisted()

        device_uid = token.payload.get("device_uid")
        if (
            not device_uid
            or not TrustedDevice.objects.filter(device_uid=device_uid).exists()
        ):
            raise DeviceNotRecognized()

        return {}

    @staticmethod
    def _is_token_blacklisted(jti: str) -> bool:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        return BlacklistedToken.objects.filter(token__jti=jti).exists()
