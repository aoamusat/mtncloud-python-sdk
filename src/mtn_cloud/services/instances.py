"""Modern service for MTN Cloud compute instances."""

import time
from collections.abc import Callable
from typing import Any

from mtn_cloud.core import CoreClient
from mtn_cloud.models.instance import Instance, InstanceCreate, InstanceUpdate
from mtn_cloud.models.group import Group
from mtn_cloud.modern_exceptions import MtnCloudError, TimeoutError
from mtn_cloud.services.base import Page, Service
from mtn_cloud.services.groups import GroupsService
from mtn_cloud.services.instance_types import InstanceTypesService
from mtn_cloud.services.plans import PlansService
from mtn_cloud.services.resource_pools import ResourcePoolsService
from mtn_cloud.services.zones import ZonesService


class InstancesService(Service[Instance]):
    """List, create, update, and delete compute instances."""

    path = "/instances"
    item_key = "instance"
    list_key = "instances"
    model = Instance

    def __init__(
        self,
        core: CoreClient,
        *,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        groups: GroupsService | None = None,
        zones: ZonesService | None = None,
        instance_types: InstanceTypesService | None = None,
        plans: PlansService | None = None,
        resource_pools: ResourcePoolsService | None = None,
    ) -> None:
        super().__init__(core)
        self._sleeper = sleeper
        self._clock = clock
        self._groups = groups
        self._zones = zones
        self._instance_types = instance_types
        self._plans = plans
        self._resource_pools = resource_pools

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

    def start(self, instance_id: int) -> Instance:
        return self._action(instance_id, "start")

    def stop(self, instance_id: int) -> Instance:
        return self._action(instance_id, "stop")

    def restart(self, instance_id: int) -> Instance:
        return self._action(instance_id, "restart")

    def suspend(self, instance_id: int) -> Instance:
        return self._action(instance_id, "suspend")

    def _action(self, instance_id: int, action: str) -> Instance:
        self._core.request("PUT", f"{self.path}/{instance_id}/{action}")
        return self.get(instance_id)

    def wait_for_status(
        self,
        instance_id: int,
        target_status: str,
        *,
        timeout: float = 300,
        poll_interval: float = 5,
    ) -> Instance:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if poll_interval < 0:
            raise ValueError("poll_interval cannot be negative")

        target = target_status.strip().lower()
        deadline = self._clock() + timeout
        while True:
            instance = self.get(instance_id)
            current = instance.status.lower()
            if current == target:
                return instance
            if current == "failed":
                raise MtnCloudError(
                    f"Instance {instance_id} entered failed state: {instance.status_message}"
                )
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out waiting for instance {instance_id} to reach '{target}'",
                    timeout=timeout,
                )
            self._sleeper(min(poll_interval, remaining))

    def wait_until_running(
        self,
        instance_id: int,
        *,
        timeout: float = 300,
        poll_interval: float = 5,
    ) -> Instance:
        return self.wait_for_status(
            instance_id,
            "running",
            timeout=timeout,
            poll_interval=poll_interval,
        )

    def wait_until_stopped(
        self,
        instance_id: int,
        *,
        timeout: float = 300,
        poll_interval: float = 5,
    ) -> Instance:
        return self.wait_for_status(
            instance_id,
            "stopped",
            timeout=timeout,
            poll_interval=poll_interval,
        )

    def provision(
        self,
        name: str,
        *,
        type_code: str,
        group: str | int,
        plan: str | int,
        zone: str | int | None = None,
        resource_pool: str | int | None = None,
        layout: int | str | None = None,
        wait: bool = True,
        timeout: float = 600,
        dry_run: bool = False,
        description: str | None = None,
        labels: list[str] | None = None,
        tags: dict[str, str] | None = None,
        security_group: str = "default",
        create_user: bool = True,
    ) -> Instance | dict[str, Any]:
        """Resolve provisioning inputs and create an instance."""

        services = (
            self._groups,
            self._zones,
            self._instance_types,
            self._plans,
            self._resource_pools,
        )
        if any(service is None for service in services):
            raise RuntimeError("InstancesService provisioning dependencies are not configured")
        groups, zones, instance_types, plans, resource_pools = services

        group_model = groups.get(group) if isinstance(group, int) else groups.get_by_name(group)
        zone_model = self._resolve_zone(group_model, zone, zones)
        instance_type = instance_types.get_by_code(type_code)
        layout_id = self._resolve_layout(instance_type, layout)
        plan_id = self._resolve_plan(plans, plan)
        pool_code = self._resolve_pool(
            resource_pools,
            resource_pool,
            zone_id=zone_model.id,
            group_id=group_model.id,
        )
        cloud_name = zone_model.name or str(zone_model.id)

        request = InstanceCreate(
            name=name,
            cloud=cloud_name,
            type=type_code,
            group_id=group_model.id,
            layout=layout_id,
            plan=plan_id,
            resource_pool_id=pool_code,
            description=description,
            labels=labels or [],
            tags=tags or {},
            security_group=security_group,
            create_user=create_user,
        )
        resolved = {
            "name": name,
            "cloud": cloud_name,
            "group_id": group_model.id,
            "zone_id": zone_model.id,
            "type": type_code,
            "layout": layout_id,
            "plan": plan_id,
            "resource_pool_id": pool_code,
        }
        if dry_run:
            return resolved

        instance = self.create(request)
        return self.wait_until_running(instance.id, timeout=timeout) if wait else instance

    @staticmethod
    def _resolve_layout(instance_type: Any, layout: int | str | None) -> int:
        if isinstance(layout, int):
            return layout
        if isinstance(layout, str):
            if layout.isdigit():
                return int(layout)
            match = instance_type.get_layout_by_name(layout)
            if match is not None:
                return match.id
            raise ValueError(f"Layout '{layout}' not found for instance type '{instance_type.code}'")
        if instance_type.default_layout_id is None:
            raise ValueError(f"Instance type '{instance_type.code}' has no available layout")
        return instance_type.default_layout_id

    @staticmethod
    def _resolve_plan(plans: PlansService, plan: str | int) -> int:
        if isinstance(plan, int):
            return plan
        if plan.isdigit():
            return int(plan)
        return plans.get_by_name(plan).id

    @staticmethod
    def _resolve_pool(
        pools: ResourcePoolsService,
        resource_pool: str | int | None,
        *,
        zone_id: int,
        group_id: int,
    ) -> str:
        if isinstance(resource_pool, int) or (
            isinstance(resource_pool, str) and resource_pool.strip().isdigit()
        ):
            return f"pool-{resource_pool}"
        available = pools.list(zone_id=zone_id, group_id=group_id)
        if resource_pool is not None:
            return pools.get_by_name(
                resource_pool,
                zone_id=zone_id,
                group_id=group_id,
            ).code
        if len(available) != 1:
            if not available:
                raise ValueError("No resource pools are available for this group and zone")
            names = ", ".join(pool.name or pool.code for pool in available)
            raise ValueError(f"Multiple resource pools are available; choose one: {names}")
        return available[0].code

    @staticmethod
    def _resolve_zone(group: Group, zone: str | int | None, zones: ZonesService) -> Any:
        if isinstance(zone, int) or (isinstance(zone, str) and zone.isdigit()):
            return zones.get(int(zone))
        if isinstance(zone, str):
            return zones.get_by_name(zone)
        if not group.cloud_ids:
            raise ValueError(f"Group '{group.name or group.id}' has no associated zones")
        return zones.get(group.cloud_ids[0])

    def _parse_item(self, body: Any) -> Instance:
        if not isinstance(body, dict):
            raise MtnCloudError("Invalid instance response: expected an object")
        payload = body.get(self.item_key, body)
        if not isinstance(payload, dict):
            raise MtnCloudError("Invalid instance response: expected an instance object")
        return self.model.model_validate(payload)
