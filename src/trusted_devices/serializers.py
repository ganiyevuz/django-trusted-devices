from typing import Any
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
    TokenVerifySerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import UntypedToken

from trusted_devices.models import TrustedDevice
from trusted_devices.utils import get_client_ip, get_location_data


class TrustedDeviceListSerializer(ModelSerializer):
    """Serializer for listing TrustedDevice instances."""

    class Meta:
        model = TrustedDevice
        fields = [
            "device_uid",
            "user_agent",
            "ip_address",
            "country",
            "region",
            "city",
            "last_seen",
            "created_at",
        ]
        read_only_fields = fields


class TrustedDeviceUpdateSerializer(ModelSerializer):
    """Serializer for updating TrustedDevice instances."""

    class Meta:
        model = TrustedDevice
        fields = ["can_delete_other_devices", "can_update_other_devices"]


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

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = get_client_ip(request)
        location_data = get_location_data(ip_address)

        # Add device_uid to token
        refresh = self.get_token(self.user)
        refresh["device_uid"] = str(uuid4())

        # Save TrustedDevice instance
        TrustedDevice.objects.create(
            user=self.user,
            device_uid=refresh["device_uid"],
            user_agent=user_agent,
            ip_address=ip_address,
            country=location_data.get("country"),
            region=location_data.get("region"),
            city=location_data.get("city"),
        )

        data.update(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "device_uid": refresh["device_uid"],
            }
        )

        return data


class TrustedDeviceTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Custom refresh serializer that updates last_seen on the TrustedDevice
    and validates device ownership.
    """

    default_error_messages = {
        "device_uid_mismatch_with_user": "This session device is no longer valid.",
        "no_active_account": "User account is inactive.",
    }

    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        refresh = self.token_class(attrs["refresh"])
        device_uid = refresh.payload.get("device_uid")

        device = TrustedDevice.objects.filter(device_uid=device_uid).first()
        if device:
            device.last_seen = timezone.now()
            device.save()
        else:
            raise AuthenticationFailed(
                self.error_messages["device_uid_mismatch_with_user"],
                code="device_uid_mismatch_with_user",
            )

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = (
            get_user_model()
            .objects.filter(**{api_settings.USER_ID_FIELD: user_id})
            .first()
        )

        if not user or not api_settings.USER_AUTHENTICATION_RULE(user):
            raise AuthenticationFailed(
                self.error_messages["no_active_account"],
                code="no_active_account",
            )

        data = {"access": str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass  # Token blacklisting not enabled

            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            refresh.outstand()

            data["refresh"] = str(refresh)

        return data


class TrustedDeviceTokenVerifySerializer(TokenVerifySerializer):
    """
    Custom verify serializer that checks whether the device_uid in the token
    belongs to a known trusted device.
    """

    default_error_messages = {
        "device_uid_mismatch_with_user": "This session device is no longer valid.",
        "token_blacklisted": "Token has been blacklisted.",
    }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        token = UntypedToken(attrs["token"])

        if (
            api_settings.BLACKLIST_AFTER_ROTATION
            and "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS
        ):
            jti = token.get(api_settings.JTI_CLAIM)
            if BlacklistedToken.objects.filter(token__jti=jti).exists():
                raise ValidationError(
                    self.error_messages["token_blacklisted"],
                    code="token_blacklisted",
                )

        device_uid = token.payload.get("device_uid")
        if (
            not device_uid
            or not TrustedDevice.objects.filter(device_uid=device_uid).exists()
        ):
            raise AuthenticationFailed(
                self.error_messages["device_uid_mismatch_with_user"],
                code="device_uid_mismatch_with_user",
            )

        return {}
