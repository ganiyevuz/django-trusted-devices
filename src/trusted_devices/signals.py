import logging

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import Signal, receiver

from trusted_devices.models import TrustedDevice
from trusted_devices.utils import get_geolocation_backend

logger = logging.getLogger(__name__)

# Custom signals for consumers to hook into
device_created = Signal()  # args: user, device
device_revoked = Signal()  # args: user, device_uid
suspicious_login = Signal()  # args: user, device, previous_countries
device_compromised = Signal()  # args: user, device_uid, previous_ip, current_ip


@receiver(pre_save, sender=TrustedDevice)
def set_device_location(sender, instance, **kwargs):
    """
    Fetches geolocation data on initial device creation only.
    Skips if location is already populated or if this is a partial update
    (e.g. last_seen-only saves via update_fields).
    """
    if instance.pk and kwargs.get("update_fields"):
        return

    if instance.ip_address and not instance.country:
        geolocation_fn = get_geolocation_backend()
        location = geolocation_fn(instance.ip_address)
        instance.country = location.get("country")
        instance.region = location.get("region")
        instance.city = location.get("city")


@receiver(post_save, sender=TrustedDevice)
def on_device_created(sender, instance, created, **kwargs):
    """Fires device_created signal when a new device is registered."""
    if created:
        device_created.send(
            sender=TrustedDevice,
            user=instance.user,
            device=instance,
        )


@receiver(post_save, sender=TrustedDevice)
def detect_suspicious_login(sender, instance, created, **kwargs):
    """
    Fires suspicious_login signal when a new device logs in from
    a country not seen in the user's existing devices.
    """
    if not created or not instance.country:
        return

    previous_countries = set(
        TrustedDevice.objects.filter(user=instance.user)
        .exclude(device_uid=instance.device_uid)
        .exclude(country__isnull=True)
        .exclude(country="")
        .values_list("country", flat=True)
        .distinct()
    )

    if previous_countries and instance.country not in previous_countries:
        logger.warning(
            "Suspicious login for user %s: new country '%s', "
            "known countries: %s",
            instance.user_id,
            instance.country,
            previous_countries,
        )
        suspicious_login.send(
            sender=TrustedDevice,
            user=instance.user,
            device=instance,
            previous_countries=previous_countries,
        )


@receiver(post_delete, sender=TrustedDevice)
def on_device_revoked(sender, instance, **kwargs):
    """Fires device_revoked signal when a device is removed."""
    device_revoked.send(
        sender=TrustedDevice,
        user=instance.user,
        device_uid=instance.device_uid,
    )
