from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import TrustedDevice
from .utils import get_location_data


@receiver(pre_save, sender=TrustedDevice)
def set_device_location(sender, instance, **kwargs):

    # Only fetches location if fields are empty
    if instance.ip_address and not instance.country:
        location = get_location_data(instance.ip_address)
        instance.country = location.get("country")
        instance.region = location.get("region")
        instance.city = location.get("city")
