from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TrustedDeviceAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "trusted_devices.authentication.TrustedDeviceAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
