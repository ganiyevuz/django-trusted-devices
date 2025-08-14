from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('project.swagger')),
    path("admin/", admin.site.urls),
    path(
        "api/trusted_devices/",
        include("trusted_devices.urls", namespace="trusted_devices"),
    ),
]
