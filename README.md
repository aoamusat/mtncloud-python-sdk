# MTN Cloud Python SDK

Production-oriented Python client for the MTN Cloud Console API.

## Status

The modern client is under active development and starts at version `0.1.0`.
The legacy client remains available for compatibility while the typed service
surface is expanded and validated against the MTN Cloud API.

## Installation

```bash
uv add mtn-cloud
```

For local development:

```bash
uv sync --extra dev
```

## Quick start

```python
from mtn_cloud import ClientSettings, MtnCloudClient

settings = ClientSettings()

with MtnCloudClient(settings=settings) as client:
    print(client.whoami())
    groups = client.groups.list()
    print(groups.items)
```

The client reads `MTN_CLOUD_TOKEN` (or the compatible
`MTN_CLOUD_API_KEY`) from the environment. The API base URL defaults to
`https://console.cloud.mtn.ng` and can be overridden with
`MTN_CLOUD_BASE_URL`.

## Live contract tests

Read-only live checks can be enabled explicitly:

```bash
MTN_CLOUD_RUN_LIVE_TESTS=1 uv run pytest tests/integration/test_live_contract.py -q -m "not mutation"
```

Mutation tests additionally require `MTN_CLOUD_ALLOW_MUTATIONS=1`. See
[`docs/live-contract-tests.md`](docs/live-contract-tests.md) for safeguards
and cleanup behavior.

## License

MIT
