"""Modern service for MTN Cloud network discovery."""

from typing import Any

from mtn_cloud.core import CoreClient
from mtn_cloud.models.network import Network, Subnet
from mtn_cloud.modern_exceptions import MtnCloudError
from mtn_cloud.services.base import Page, Service


class NetworksService(Service[Network]):
    """Discover tenant networks and their subnets."""

    path = "/networks"
    item_key = "network"
    list_key = "networks"
    model = Network

    def list_page(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        name: str | None = None,
        zone_id: int | None = None,
        group_id: int | None = None,
    ) -> Page[Network]:
        params: dict[str, Any] = {
            "max": limit,
            "offset": offset,
            "name": name,
            "zoneId": zone_id,
            "siteId": group_id,
        }
        return self._list_page(params={key: value for key, value in params.items() if value is not None})

    def list(self, **kwargs: Any) -> list[Network]:
        return self.list_page(**kwargs).items

    def get(self, network_id: int) -> Network:
        return self._get(network_id)

    def list_subnets(self, network_id: int) -> list[Subnet]:
        body = self._core.request("GET", f"{self.path}/{network_id}/subnets")
        if not isinstance(body, dict) or not isinstance(body.get("subnets"), list):
            raise MtnCloudError("Invalid subnet response: expected a 'subnets' list")
        return [Subnet.model_validate(item) for item in body["subnets"]]
