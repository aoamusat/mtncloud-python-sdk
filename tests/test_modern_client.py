from unittest.mock import Mock

import pytest

from mtn_cloud import ClientSettings, MtnCloudClient
from mtn_cloud.models.instance import InstanceCreate, InstanceUpdate
from mtn_cloud.modern_exceptions import TimeoutError as ModernTimeoutError
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


def test_zones_service_parses_typed_pages() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {
            "zones": [{"id": 1, "name": "MTNNG_CLOUD_AZ_1", "cloudType": "openstack"}],
            "meta": {"offset": 0, "max": 25, "total": 1},
        },
    )
    client = MtnCloudClient(token="secret", transport=transport)

    page = client.zones.list_page(limit=25, type_code="openstack")

    assert page.items[0].name == "MTNNG_CLOUD_AZ_1"
    assert page.total == 1
    assert page.has_more is False
    assert transport.request.call_args.kwargs["params"] == {"max": 25, "offset": 0, "type": "openstack"}


def test_groups_service_gets_wrapped_resource() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {"group": {"id": 7, "name": "project-a", "active": True}},
    )
    client = MtnCloudClient(token="secret", transport=transport)

    group = client.groups.get(7)

    assert group.id == 7
    assert group.name == "project-a"


def test_instance_types_service_parses_layouts() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {
            "instanceTypes": [
                {
                    "id": 10,
                    "name": "Ubuntu 22.04",
                    "code": "ubuntu-2204",
                    "instanceTypeLayouts": [{"id": 20, "name": "Ubuntu layout"}],
                }
            ],
            "meta": {"total": 1},
        },
    )
    client = MtnCloudClient(token="secret", transport=transport)

    instance_type = client.instance_types.get_by_code("ubuntu-2204")

    assert instance_type.default_layout_id == 20
    assert instance_type.layouts[0].name == "Ubuntu layout"


def test_plans_service_parses_resource_sizes() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {
            "servicePlans": [
                {"id": 30, "name": "small", "maxCores": 2, "maxMemory": 4294967296}
            ]
        },
    )
    client = MtnCloudClient(token="secret", transport=transport)

    plan = client.plans.get_by_name("small")

    assert plan.cores == 2
    assert plan.memory_gb == 4


def test_resource_pools_filter_non_selectable_group_rows() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {
            "data": [
                {"isGroup": True, "name": "OpenStack"},
                {"id": 214, "value": "pool-214", "name": "project-a", "isDefault": True},
            ]
        },
    )
    client = MtnCloudClient(token="secret", transport=transport)

    pools = client.resource_pools.list(zone_id=4, group_id=621)

    assert len(pools) == 1
    assert pools[0].code == "pool-214"
    assert pools[0].is_default is True
    assert transport.request.call_args.kwargs["params"] == {
        "cloudId": 4,
        "groupId": 621,
        "provisionTypeCode": "openstack",
    }


def test_instances_service_lists_typed_instances() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {"instances": [{"id": 99, "name": "web-01", "status": "running"}]},
    )
    client = MtnCloudClient(token="secret", transport=transport)

    instances = client.instances.list(status="running")

    assert instances[0].id == 99
    assert instances[0].is_running is True
    assert transport.request.call_args.kwargs["params"] == {
        "offset": 0,
        "status": "running",
    }


def test_instances_service_create_serializes_request_model() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        201,
        {},
        {"instance": {"id": 100, "name": "web-01", "status": "provisioning"}},
    )
    client = MtnCloudClient(token="secret", transport=transport)
    request = InstanceCreate(
        name="web-01",
        cloud="MTNNG_CLOUD_AZ_1",
        type="ubuntu-2204",
        group_id=621,
        layout=20,
        plan=30,
        resource_pool_id="pool-214",
    )

    instance = client.instances.create(request)

    assert instance.id == 100
    assert transport.request.call_args.kwargs["json"]["instance"]["site"] == {"id": 621}


def test_instances_service_update_uses_put() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {"instance": {"id": 100, "name": "web-renamed", "status": "stopped"}},
    )
    client = MtnCloudClient(token="secret", transport=transport)

    instance = client.instances.update(100, InstanceUpdate(name="web-renamed"))

    assert instance.name == "web-renamed"
    assert transport.request.call_args.args[:2] == ("PUT", "/instances/100")


def test_instances_service_action_refreshes_instance() -> None:
    transport = Mock()
    transport.request.side_effect = [
        HttpResponse(202, {}, {}),
        HttpResponse(200, {}, {"instance": {"id": 100, "status": "running"}}),
    ]
    client = MtnCloudClient(token="secret", transport=transport)

    instance = client.instances.start(100)

    assert instance.is_running is True
    assert transport.request.call_args_list[0].args[:2] == ("PUT", "/instances/100/start")
    assert transport.request.call_args_list[1].args[:2] == ("GET", "/instances/100")


def test_instances_service_waiter_uses_monotonic_deadline() -> None:
    transport = Mock()
    transport.request.side_effect = [
        HttpResponse(200, {}, {"instance": {"id": 100, "status": "provisioning"}}),
        HttpResponse(200, {}, {"instance": {"id": 100, "status": "running"}}),
    ]
    clock_values = iter([0.0, 1.0, 2.0])
    sleeper = Mock()
    client = MtnCloudClient(
        token="secret",
        transport=transport,
        sleeper=sleeper,
        clock=lambda: next(clock_values),
    )

    instance = client.instances.wait_until_running(100, timeout=10, poll_interval=5)

    assert instance.status == "running"
    sleeper.assert_called_once_with(5)


def test_instances_service_waiter_raises_typed_timeout() -> None:
    transport = Mock()
    transport.request.return_value = HttpResponse(
        200,
        {},
        {"instance": {"id": 100, "status": "provisioning"}},
    )
    clock_values = iter([0.0, 2.0])
    client = MtnCloudClient(
        token="secret",
        transport=transport,
        sleeper=Mock(),
        clock=lambda: next(clock_values),
    )

    with pytest.raises(ModernTimeoutError) as raised:
        client.instances.wait_until_running(100, timeout=1, poll_interval=5)

    assert raised.value.timeout == 1


def test_instance_provision_dry_run_resolves_dependencies() -> None:
    transport = Mock()
    transport.request.side_effect = [
        HttpResponse(200, {}, {"groups": [{"id": 621, "name": "project-a", "zones": [{"id": 4}]}]}),
        HttpResponse(200, {}, {"zone": {"id": 4, "name": "MTNNG_CLOUD_AZ_1"}}),
        HttpResponse(200, {}, {"instanceTypes": [{"id": 10, "name": "Ubuntu", "code": "ubuntu", "instanceTypeLayouts": [{"id": 20, "name": "default"}]}]}),
        HttpResponse(200, {}, {"servicePlans": [{"id": 30, "name": "small"}]}),
        HttpResponse(200, {}, {"data": [{"id": 214, "value": "pool-214", "name": "project-a"}]}),
    ]
    client = MtnCloudClient(token="secret", transport=transport)

    resolved = client.instances.provision(
        "web-01",
        type_code="ubuntu",
        group="project-a",
        plan="small",
        dry_run=True,
    )

    assert resolved == {
        "name": "web-01",
        "cloud": "MTNNG_CLOUD_AZ_1",
        "group_id": 621,
        "zone_id": 4,
        "type": "ubuntu",
        "layout": 20,
        "plan": 30,
        "resource_pool_id": "pool-214",
    }
