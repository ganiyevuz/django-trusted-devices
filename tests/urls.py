from django.urls import include, path

urlpatterns = [
    path("api/", include("trusted_devices.urls", namespace="trusted_devices")),
]
