"""Requests-based synchronous transport."""

from collections.abc import Mapping
from typing import Any

import requests

from mtn_cloud.settings import ClientSettings
from mtn_cloud.transport.base import HttpResponse


class RequestsTransport:
    """Default transport with connection reuse and explicit request boundaries."""

    def __init__(self, settings: ClientSettings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": settings.user_agent,
            }
        )
        self._session.verify = settings.verify_ssl

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        response = self._session.request(
            method=method,
            url=f"{self._settings.api_url}/{path.lstrip('/')}",
            params=params,
            json=json,
            headers=dict(headers or {}),
            timeout=timeout or self._settings.timeout,
        )
        try:
            body: Any = response.json() if response.content else None
        except ValueError:
            body = response.text
        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            request_id=response.headers.get("X-Request-Id"),
        )

    def close(self) -> None:
        self._session.close()
