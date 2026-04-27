from uuid import uuid4

from django.contrib.auth import get_user_model
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory

from trusted_devices.models import TrustedDevice


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = Faker("user_name")
    email = Faker("email")


class TrustedDeviceFactory(DjangoModelFactory):
    class Meta:
        model = TrustedDevice

    device_uid = LazyFunction(uuid4)
    user = SubFactory(UserFactory)
    user_agent = "pytest-agent/1.0"
    ip_address = "203.0.113.10"
    last_ip = "203.0.113.10"
    country = "Testland"
    region = "Test Region"
    city = "Testville"
    can_update_other_devices = True
    can_delete_other_devices = True
