from rest_framework_simplejwt.tokens import RefreshToken


class TrustedDeviceRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user) -> RefreshToken:
        token = super().for_user(user)
        cls.add_trusted_device_info(token, user)
        return token

    @staticmethod
    def add_trusted_device_info(token: RefreshToken, user) -> None:
        if not hasattr(user, "current_trusted_device"):
            raise ValueError(
                "Expected 'user.current_trusted_device' to be set before generating the token."
            )
        token["device_uid"] = user.current_trusted_device.device_uid
