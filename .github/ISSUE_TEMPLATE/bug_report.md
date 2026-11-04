---
name: Bug report
about: Report a reproducible defect in the SDK
title: "bug: "
labels: ["bug", "triage"]
assignees: []
---

## Summary

<!-- What went wrong? Please describe the observed behavior precisely. -->

## Reproduction

```python
from mtn_cloud import MtnCloudClient

with MtnCloudClient(token="REDACTED") as cloud:
    # Minimal reproduction here.
    pass
```

<!-- Remove credentials and tenant-specific identifiers before submitting. -->

## Expected behavior

## Actual behavior

## API context

- Endpoint or SDK operation:
- HTTP status code:
- Request ID, if available:
- Was this a read-only or mutating operation?
- Was the credential a `morph-api` client or another client type?

## Environment

- SDK version:
- Python version:
- Operating system:
- Installation method (`uv`, pip, source checkout):

## Logs and traceback

```text
Paste a redacted traceback or response here.
Do not include API keys, refresh tokens, authorization headers, or private IPs.
```

## Additional context

<!-- Include a sanitized response shape, relevant configuration, or links. -->
