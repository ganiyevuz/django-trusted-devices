from django.apps import AppConfig


class TrustedDevicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trusted_devices"

    def ready(self):
        from . import signals  # noqa
        import trusted_devices.schema  # noqa
