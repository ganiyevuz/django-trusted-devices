"""Test doubles used by the test suite."""

FAKE_LOCATION = {
    "country": "Testland",
    "region": "Test Region",
    "city": "Testville",
}


def fake_geolocation(ip: str) -> dict:
    if not ip or ip in ("127.0.0.1", "::1"):
        return {}
    return dict(FAKE_LOCATION)


def extra_keys_backend(ip: str) -> dict:
    return {"country": "X", "extra": "ignored"}


def non_dict_backend(ip: str):
    return "not a dict"


def counted_backend(ip: str) -> dict:
    counted_backend.calls = getattr(counted_backend, "calls", 0) + 1
    return dict(FAKE_LOCATION)


counted_backend.calls = 0
