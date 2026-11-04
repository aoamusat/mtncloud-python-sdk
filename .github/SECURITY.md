# Security policy

## Supported versions

| Version | Security support |
| --- | --- |
| `0.1.x` | Supported |
| Older versions | Upgrade recommended |

Security fixes are prioritized for the latest release line. Because the SDK
is pre-`1.0`, users should upgrade promptly when a patched version is made
available.

## Reporting a vulnerability in this SDK

Please do not open a public GitHub issue for a suspected vulnerability.

Preferred channel:

1. Use GitHub's private vulnerability reporting feature for this repository,
   if enabled.
2. Otherwise email the maintainer at `hello@a4m.dev` with the subject
   `[SECURITY] mtncloud-python-sdk`.

Include:

- A concise description of the vulnerability and its impact
- Affected versions and supported Python versions
- Reproduction steps or a minimal proof of concept
- Any required configuration or permissions
- A suggested mitigation, if known

Do not include real API keys, refresh tokens, authorization headers, or
unredacted tenant data. Use placeholders in all examples.

You can expect an acknowledgement within 48 hours. We will coordinate a fix,
release, and disclosure timeline with the reporter where appropriate.

## MTN Cloud service vulnerabilities

Report vulnerabilities in the MTN Cloud service itself directly to MTN through
its official security or support channels. This repository cannot remediate
service-side vulnerabilities.

## Dependency and credential safety

- Credentials must be supplied through environment variables or a secret
  manager, never committed to source control.
- Live mutation tests are opt-in and require a separate explicit guard.
- CI workflows use read-only repository permissions by default.
- Pull requests must not include secrets in logs, fixtures, screenshots, or
  issue comments.
