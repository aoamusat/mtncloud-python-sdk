"""Transport contracts used by the modern client."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Small transport-neutral representation of an HTTP response."""

    status_code: int
    headers: Mapping[str, str]
    body: Any
    request_id: str | None = None


class Transport(Protocol):
    """Protocol implemented by synchronous HTTP transports."""

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse: ...

    def close(self) -> None: ...
