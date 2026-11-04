"""Typed service clients exposed by the modern MTN Cloud client."""

from mtn_cloud.services.groups import GroupsService
from mtn_cloud.services.instance_types import InstanceTypesService
from mtn_cloud.services.plans import PlansService
from mtn_cloud.services.resource_pools import ResourcePoolsService
from mtn_cloud.services.zones import ZonesService

__all__ = [
    "GroupsService",
    "InstanceTypesService",
    "PlansService",
    "ResourcePoolsService",
    "ZonesService",
]
