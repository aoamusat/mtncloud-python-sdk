"""Modern MTN Cloud client foundation."""

from typing import Any

from mtn_cloud.auth import CredentialProvider
from mtn_cloud.core import CoreClient
from mtn_cloud.models.user import User
from mtn_cloud.settings import ClientSettings
from mtn_cloud.transport import Transport


class MtnCloudClient:
    """Synchronous MTN Cloud control-plane client.

    The initial API intentionally exposes only the verified foundation and
    current-user operation. Resource services will be added incrementally as
    their live contracts are confirmed.
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        settings: ClientSettings | None = None,
        transport: Transport | None = None,
        credentials: CredentialProvider | None = None,
        sleeper: Any | None = None,
    ) -> None:
        if settings is not None and token is not None:
            raise ValueError("Pass either settings or token, not both")
        self._settings = settings or ClientSettings(token=token)
        self._core = CoreClient(
            self._settings,
            transport=transport,
            credentials=credentials,
            **({"sleeper": sleeper} if sleeper is not None else {}),
        )

    @property
    def settings(self) -> ClientSettings:
        return self._settings

    def whoami(self) -> User:
        """Return the authenticated control-plane user."""

        body: Any = self._core.request("GET", "/whoami")
        payload = body.get("user", body) if isinstance(body, dict) else body
        return User.model_validate(payload)

    def ping(self) -> bool:
        """Return whether authentication and API connectivity are working."""

        self.whoami()
        return True

    def close(self) -> None:
        self._core.close()

    def __enter__(self) -> "MtnCloudClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
