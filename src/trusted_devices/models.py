from uuid import uuid4

from django.conf import settings
from django.db.models import (
    Model,
    CharField,
    DateTimeField,
    ForeignKey,
    CASCADE,
    GenericIPAddressField,
    BooleanField,
    TextField,
    UUIDField,
)
from django.db.models.indexes import Index


class TrustedDevice(Model):
    """
    Represents a device that a user has authenticated from.

    This model tracks a device via a unique UUID, stores metadata such as IP address,
    user agent, and geographical information (country, region, city), and provides
    control over whether this device can manage (update/delete) other sessions.
    """

    device_uid = UUIDField(
        default=uuid4,
        editable=False,
        primary_key=True,
        help_text="Unique identifier for the device.",
    )
    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=CASCADE,
        related_name="trusted_devices",
        help_text="The user to whom this device belongs.",
    )
    user_agent = TextField(
        help_text="User agent string of the browser or app used for login."
    )

    country = CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Country derived from the device's IP address.",
    )
    region = CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Region/state derived from the device's IP address.",
    )
    city = CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="City derived from the device's IP address.",
    )

    ip_address = GenericIPAddressField(
        help_text="IP address of the device used for authentication."
    )
    last_seen = DateTimeField(
        auto_now=True,
        help_text="The last time this device was active.",
    )
    created_at = DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this device was first registered.",
    )

    can_update_other_devices = BooleanField(
        default=True,
        help_text="Whether this device can update settings for other devices.",
    )
    can_delete_other_devices = BooleanField(
        default=True,
        help_text="Whether this device can delete other devices.",
    )

    def __str__(self):
        return f"{self.user} — {self.device_uid}"

    class Meta:
        verbose_name = "Trusted Device"
        verbose_name_plural = "Trusted Devices"
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["user"]),
        ]


# class TrustedDeviceToken(Model):
#     device = ForeignKey(TrustedDevice, on_delete=CASCADE)
#     token = CharField(max_length=255, unique=True)
#     is_active = BooleanField(default=True)
#     created_at = DateTimeField(auto_now_add=True)
#     expires_at = DateTimeField()
