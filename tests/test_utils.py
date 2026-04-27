from unittest.mock import MagicMock

import pytest
from django.test import override_settings

from trusted_devices.exceptions import InvalidGeolocationBackend
from trusted_devices.utils import (
    format_duration,
    get_client_ip,
    get_geolocation_backend,
)


def _request_with_meta(**meta):
    request = MagicMock()
    request.META = meta
    return request


class TestGetClientIp:
    def test_default_returns_remote_addr(self):
        request = _request_with_meta(REMOTE_ADDR="198.51.100.1")
        assert get_client_ip(request) == "198.51.100.1"

    def test_default_ignores_x_forwarded_for(self):
        request = _request_with_meta(
            REMOTE_ADDR="198.51.100.1",
            HTTP_X_FORWARDED_FOR="1.2.3.4, 198.51.100.1",
        )
        assert get_client_ip(request) == "198.51.100.1"

    @override_settings(TRUSTED_DEVICE={"USE_X_FORWARDED_FOR": True, "TRUSTED_PROXY_DEPTH": 1})
    def test_with_proxy_depth_one_takes_second_from_right(self):
        request = _request_with_meta(
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="203.0.113.5, 10.0.0.1",
        )
        assert get_client_ip(request) == "203.0.113.5"

    @override_settings(TRUSTED_DEVICE={"USE_X_FORWARDED_FOR": True, "TRUSTED_PROXY_DEPTH": 2})
    def test_with_proxy_depth_two_takes_third_from_right(self):
        request = _request_with_meta(
            HTTP_X_FORWARDED_FOR="203.0.113.5, 10.0.0.1, 10.0.0.2",
        )
        assert get_client_ip(request) == "203.0.113.5"

    @override_settings(TRUSTED_DEVICE={"USE_X_FORWARDED_FOR": True, "TRUSTED_PROXY_DEPTH": 5})
    def test_short_xff_falls_back_to_first(self):
        request = _request_with_meta(HTTP_X_FORWARDED_FOR="203.0.113.5")
        assert get_client_ip(request) == "203.0.113.5"

    def test_missing_remote_addr_returns_empty(self):
        request = _request_with_meta()
        assert get_client_ip(request) == ""


class TestGetGeolocationBackend:
    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": "tests.fakes.fake_geolocation"})
    def test_returns_callable_for_valid_path(self):
        backend = get_geolocation_backend()
        result = backend("203.0.113.10")
        assert result["country"] == "Testland"

    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": ""})
    def test_empty_path_raises(self):
        with pytest.raises(InvalidGeolocationBackend):
            get_geolocation_backend()

    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": "noseparator"})
    def test_no_dot_raises(self):
        with pytest.raises(InvalidGeolocationBackend):
            get_geolocation_backend()

    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": "nonexistent_module.func"})
    def test_unimportable_module_raises(self):
        with pytest.raises(InvalidGeolocationBackend):
            get_geolocation_backend()

    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": "tests.fakes.does_not_exist"})
    def test_missing_attribute_raises(self):
        with pytest.raises(InvalidGeolocationBackend):
            get_geolocation_backend()

    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": "tests.fakes.FAKE_LOCATION"})
    def test_non_callable_raises(self):
        with pytest.raises(InvalidGeolocationBackend):
            get_geolocation_backend()

    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": "tests.fakes.extra_keys_backend"})
    def test_extra_keys_are_dropped(self):
        backend = get_geolocation_backend()
        result = backend("1.2.3.4")
        assert result == {"country": "X", "region": None, "city": None}

    @override_settings(TRUSTED_DEVICE={"GEOLOCATION_BACKEND": "tests.fakes.non_dict_backend"})
    def test_non_dict_return_is_safe(self):
        backend = get_geolocation_backend()
        assert backend("1.2.3.4") == {}

    @override_settings(
        TRUSTED_DEVICE={
            "GEOLOCATION_BACKEND": "tests.fakes.counted_backend",
            "GEOLOCATION_CACHE_SECONDS": 60,
        }
    )
    def test_cache_avoids_second_call(self):
        from django.core.cache import cache

        from tests import fakes

        cache.clear()
        fakes.counted_backend.calls = 0
        backend = get_geolocation_backend()
        backend("203.0.113.10")
        backend("203.0.113.10")
        assert fakes.counted_backend.calls == 1


class TestFormatDuration:
    @pytest.mark.parametrize(
        "minutes,expected",
        [
            (0, "0 minutes"),
            (1, "1 minute"),
            (2, "2 minutes"),
            (60, "1 hour"),
            (61, "1 hour, 1 minute"),
            (60 * 24, "1 day"),
            (60 * 24 * 7, "1 week"),
            (60 * 24 * 8 + 65, "1 week, 1 day, 1 hour, 5 minutes"),
        ],
    )
    def test_format(self, minutes, expected):
        assert format_duration(minutes) == expected
