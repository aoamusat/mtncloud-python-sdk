from unittest.mock import Mock

import pytest

from mtn_cloud import ClientSettings, MtnCloudClient
from mtn_cloud.modern_exceptions import AuthenticationError
from mtn_cloud.transport import HttpResponse


def test_settings_default_to_mtn_cloud_control_plane() -> None:
    settings = ClientSettings()

    assert settings.base_url == "https://console.cloud.mtn.ng"
    assert settings.api_url == "https://console.cloud.mtn.ng/api"


def test_settings_normalize_urls() -> None:
    settings = ClientSettings(base_url="https://example.test/", api_prefix="v2/")

    assert settings.api_url == "https://example.test/v2"


def test_whoami_uses_bearer_auth_and_parses_user() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        status_code=200,
        headers={},
        body={"user": {"id": 1, "username": "hakeem"}},
    )
    client = MtnCloudClient(token="secret", transport=transport)

    user = client.whoami()

    assert user.username == "hakeem"
    transport.request.assert_called_once_with(
        "GET",
        "/whoami",
        params=None,
        json=None,
        headers={"Authorization": "Bearer secret"},
        timeout=None,
    )


def test_http_errors_preserve_request_id() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        status_code=401,
        headers={},
        body={"message": "invalid token"},
        request_id="req-123",
    )
    client = MtnCloudClient(token="secret", transport=transport)

    with pytest.raises(AuthenticationError) as raised:
        client.whoami()

    assert raised.value.request_id == "req-123"
    assert raised.value.status_code == 401


def test_get_retries_transient_responses_with_exponential_delay() -> None:
    transport = Mock()
    transport.request.side_effect = [
        HttpResponse(503, {}, {"message": "busy"}),
        HttpResponse(200, {}, {"user": {"id": 1, "username": "hakeem"}}),
    ]
    sleeper = Mock()
    client = MtnCloudClient(
        settings=ClientSettings(
            token="secret",
            max_retries=2,
            retry_delay=0.25,
        ),
        transport=transport,
        sleeper=sleeper,
    )

    assert client.whoami().username == "hakeem"
    sleeper.assert_called_once_with(0.25)
    assert transport.request.call_count == 2


def test_mutating_requests_are_not_automatically_retried() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(503, {}, {"message": "busy"})
    client = MtnCloudClient(token="secret", transport=transport)

    with pytest.raises(Exception):
        client._core.request("POST", "/instances", json={"name": "demo"})

    transport.request.assert_called_once()
