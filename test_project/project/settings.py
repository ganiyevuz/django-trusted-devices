from datetime import timedelta
from pathlib import Path
import sys
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(BASE_DIR / "../src"))

SECRET_KEY = "django-insecure-gmfhh4#l5e$_d3^e^-c_^%j)qzd^342_@ab*p0%v*wos6=m)dp"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "trusted_devices",
    "drf_spectacular",
]
USE_X_FORWARDED_HOST = True

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "trusted_devices.authentication.TrustedDeviceAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "trusted_devices.serializers.TrustedDeviceTokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "trusted_devices.serializers.TrustedDeviceTokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "trusted_devices.serializers.TrustedDeviceTokenVerifySerializer",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Django Trusted Devices API",
    "DESCRIPTION": "Secure and manage trusted login devices for Django users",
    "VERSION": "1.2",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATION_PARAMETERS": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]/[a-zA-Z0-9\-\_]+",
    # 'SCHEMA_PATH_PREFIX_TRIM': True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "SECURITY": [{"Bearer": []}],
    "AUTHENTICATION": [
        {
            "name": "Session",
            "description": "Session-based authentication (for Django admin and browser-based sessions)",
            "schema": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Bearer token is required for JWT authentication. Admin panel uses session-based authentication.",
            },
        },
        {
            "name": "JWT",
            "description": "JWT-based authentication",
            "schema": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Use Bearer token for JWT authentication.",
            },
        },
    ],
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
