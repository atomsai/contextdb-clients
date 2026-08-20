# Public client and starter-kit boundary

This repository is Apache-2.0 reference and transport code. It may contain:

- generated or hand-maintained thin Cloud API clients,
- strict public request and response contracts,
- framework adapters that call those public clients,
- runnable starter applications,
- tests, documentation, and release automation for those artifacts.

It must not contain:

- ContextDB Cloud route implementations,
- organization, project, entitlement, or billing control-plane logic,
- managed-source workers, scheduling, leases, checkpoints, or DLQ operations,
- deployment, fleet, migration-orchestration, or Secret Manager server code,
- enterprise governance implementation,
- private embedding or memory-service implementation.

Starter kits may show how an application reads its own provider credentials
from server-side environment variables. They may not mint, resolve, store, or
operate ContextDB service credentials.

The test is simple: deleting ContextDB Cloud must leave this repository useful
as a public contract and reference client, but incapable of recreating the
hosted service.
