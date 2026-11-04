"""Authentication providers used by the request pipeline."""

from typing import Protocol


class CredentialProvider(Protocol):
    """Provide and invalidate a control-plane bearer token."""

    def get_token(self) -> str | None: ...

    def invalidate(self) -> None: ...


class StaticTokenProvider:
    """Credential provider for a token supplied by the caller or environment."""

    def __init__(self, token: str | None) -> None:
        self._token = token.strip() if token else None

    def get_token(self) -> str | None:
        return self._token

    def invalidate(self) -> None:
        # Static credentials cannot be refreshed by the SDK.
        return None
