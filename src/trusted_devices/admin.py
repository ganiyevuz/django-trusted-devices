from django.contrib.admin import ModelAdmin, register

from trusted_devices.models import TrustedDevice


@register(TrustedDevice)
class TrustedDeviceAdmin(ModelAdmin):
    list_display = [
        "device_uid",
        "name",
        "user",
        "ip_address",
        "country",
        "city",
        "last_seen",
        "created_at",
    ]
    list_filter = ["country", "created_at", "last_seen"]
    search_fields = ["user__username", "user__email", "ip_address", "city", "name"]
    readonly_fields = [
        "device_uid",
        "user",
        "user_agent",
        "ip_address",
        "country",
        "region",
        "city",
        "last_seen",
        "created_at",
    ]
    list_select_related = ["user"]
    ordering = ["-last_seen"]
