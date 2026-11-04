"""Modern service for MTN Cloud service plans."""

from typing import Any

from mtn_cloud.models.plan import ServicePlan
from mtn_cloud.modern_exceptions import NotFoundError
from mtn_cloud.services.base import Page, Service


class PlansService(Service[ServicePlan]):
    """Discover compute plans available to the tenant."""

    path = "/service-plans"
    item_key = "servicePlan"
    list_key = "servicePlans"
    model = ServicePlan

    def list_page(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        name: str | None = None,
    ) -> Page[ServicePlan]:
        params: dict[str, Any] = {"max": limit, "offset": offset, "name": name}
        return self._list_page(params={key: value for key, value in params.items() if value is not None})

    def list(self, **kwargs: Any) -> list[ServicePlan]:
        return self.list_page(**kwargs).items

    def get(self, plan_id: int) -> ServicePlan:
        return self._get(plan_id)

    def get_by_name(self, name: str) -> ServicePlan:
        matches = [item for item in self.list(name=name, limit=100) if item.name == name]
        if not matches:
            raise NotFoundError(f"Service plan with name '{name}' not found")
        if len(matches) > 1:
            raise ValueError(f"Service plan name '{name}' is ambiguous")
        return matches[0]
