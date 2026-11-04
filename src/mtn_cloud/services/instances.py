"""Modern service for MTN Cloud compute instances."""

from typing import Any

from mtn_cloud.core import CoreClient
from mtn_cloud.models.instance import Instance, InstanceCreate, InstanceUpdate
from mtn_cloud.modern_exceptions import MtnCloudError
from mtn_cloud.services.base import Page, Service


class InstancesService(Service[Instance]):
    """List, create, update, and delete compute instances."""

    path = "/instances"
    item_key = "instance"
    list_key = "instances"
    model = Instance

    def list_page(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        name: str | None = None,
        status: str | None = None,
        zone_id: int | None = None,
        group_id: int | None = None,
    ) -> Page[Instance]:
        params: dict[str, Any] = {
            "max": limit,
            "offset": offset,
            "name": name,
            "status": status,
            "zoneId": zone_id,
            "siteId": group_id,
        }
        return self._list_page(params={key: value for key, value in params.items() if value is not None})

    def list(self, **kwargs: Any) -> list[Instance]:
        return self.list_page(**kwargs).items

    def get(self, instance_id: int) -> Instance:
        return self._get(instance_id)

    def create(self, request: InstanceCreate) -> Instance:
        body = self._core.request("POST", self.path, json=request.to_api_payload())
        return self._parse_item(body)

    def update(self, instance_id: int, request: InstanceUpdate) -> Instance:
        body = self._core.request("PUT", f"{self.path}/{instance_id}", json=request.to_api_payload())
        return self._parse_item(body)

    def delete(
        self,
        instance_id: int,
        *,
        force: bool = False,
        preserve_volumes: bool = False,
    ) -> bool:
        params: dict[str, str] = {}
        if force:
            params["force"] = "on"
        if preserve_volumes:
            params["preserveVolumes"] = "on"
        self._core.request(
            "DELETE",
            f"{self.path}/{instance_id}",
            params=params or None,
        )
        return True

    def _parse_item(self, body: Any) -> Instance:
        if not isinstance(body, dict):
            raise MtnCloudError("Invalid instance response: expected an object")
        payload = body.get(self.item_key, body)
        if not isinstance(payload, dict):
            raise MtnCloudError("Invalid instance response: expected an instance object")
        return self.model.model_validate(payload)
