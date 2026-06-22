import logging
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.transaction import atomic
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
    DevicePermissionEscalation,
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
            "last_ip",
            "country",
            "region",
            "city",
            "last_seen",
            "created_at",
            "can_update_other_devices",
            "can_delete_other_devices",
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

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not hasattr(request.user, "current_trusted_device"):
            return attrs

        current_device = request.user.current_trusted_device

        if attrs.get("can_delete_other_devices") and not current_device.can_delete_other_devices:
            raise DevicePermissionEscalation()

        if attrs.get("can_update_other_devices") and not current_device.can_update_other_devices:
            raise DevicePermissionEscalation()

        return attrs


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

        refresh = self.get_token(self.user)
        refresh["device_uid"] = device_uid

        with atomic():
            self._enforce_device_limit(self.user)
            TrustedDevice.objects.create(
                user=self.user,
                device_uid=device_uid,
                user_agent=user_agent,
                ip_address=ip_address,
                last_ip=ip_address,
                country=location_data.get("country"),
                region=location_data.get("region"),
                city=location_data.get("city"),
                can_update_other_devices=trusted_device_settings.DEFAULT_CAN_UPDATE_OTHER_DEVICES,
                can_delete_other_devices=trusted_device_settings.DEFAULT_CAN_DELETE_OTHER_DEVICES,
            )
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
        If MAX_DEVICES_PER_USER is set, evict the oldest devices to make
        room for a new one. Locks the user row so concurrent logins for the
        same user serialize through this section.
        """
        max_devices = trusted_device_settings.MAX_DEVICES_PER_USER
        if not max_devices:
            return

        get_user_model().objects.select_for_update().filter(pk=user.pk).first()

        device_count = TrustedDevice.objects.filter(user=user).count()
        if device_count >= max_devices:
            devices_to_keep = list(
                TrustedDevice.objects.filter(user=user)
                .order_by("-last_seen")
                .values_list("device_uid", flat=True)[: max_devices - 1]
            )
            evicted, _ = (
                TrustedDevice.objects.filter(user=user)
                .exclude(device_uid__in=devices_to_keep)
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
        from trusted_devices.exceptions import DeviceCompromised
        from trusted_devices.signals import device_compromised

        refresh = self.token_class(attrs["refresh"])
        device_uid = refresh.payload.get("device_uid")
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)

        device = (
            TrustedDevice.objects.filter(
                device_uid=device_uid, user_id=user_id
            )
            .only("device_uid", "user_id", "last_ip", "last_seen")
            .first()
        )
        if not device:
            raise DeviceNotRecognized()

        request = self.context.get("request")
        current_ip = get_client_ip(request) if request else ""

        if self._is_concurrent_session_hijack(device, current_ip):
            previous_ip = device.last_ip or ""
            logger.warning(
                "Concurrent session hijack detected on refresh for user %s "
                "device %s: previous_ip=%s current_ip=%s",
                user_id,
                device.device_uid,
                previous_ip,
                current_ip,
            )
            compromised_uid = device.device_uid
            device.delete()
            device_compromised.send(
                sender=TrustedDevice,
                user_id=user_id,
                device_uid=compromised_uid,
                previous_ip=previous_ip,
                current_ip=current_ip,
            )
            raise DeviceCompromised()

        TrustedDevice.objects.filter(device_uid=device_uid).update(
            last_seen=timezone.now(),
            last_ip=current_ip or device.last_ip,
        )

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

    @staticmethod
    def _is_concurrent_session_hijack(device: TrustedDevice, current_ip: str) -> bool:
        from datetime import timedelta

        if not trusted_device_settings.DETECT_CONCURRENT_SESSIONS:
            return False
        if not current_ip or not device.last_ip:
            return False
        if current_ip == device.last_ip:
            return False
        window = timedelta(
            seconds=trusted_device_settings.CONCURRENT_SESSION_WINDOW_SECONDS
        )
        return device.last_seen >= timezone.now() - window


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
        user_id = token.payload.get(api_settings.USER_ID_CLAIM)

        if (
            not device_uid
            or not user_id
            or not TrustedDevice.objects.filter(
                device_uid=device_uid, user_id=user_id
            ).exists()
        ):
            raise DeviceNotRecognized()

        return {}

    @staticmethod
    def _is_token_blacklisted(jti: str) -> bool:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        return BlacklistedToken.objects.filter(token__jti=jti).exists()
