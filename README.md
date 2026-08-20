# ContextDB Cloud SDKs for AI agent memory

Add persistent, action-aware memory to Python and TypeScript AI agents through
the hosted ContextDB API. These public clients cover memory writes, recall,
read-your-writes consistency, action decisions, confirmations, execution
receipts, and verifiable deletion.

The repository contains transport code and the strict OpenAPI contract only.
The multi-tenant server, managed sources, operations, billing, and enterprise
control plane remain private.

## Python

```bash
pip install contextdb-cloud-client
```

```python
from contextdb_cloud_client import CloudClient

async with CloudClient(
    "https://api.contextdb.ai",
    api_key="cdb_...",
) as db:
    saved = await db.remember(
        "caller-1",
        "Thursday works",
        source="user_stated",
    )
    recalled = await db.recall(
        "caller-1",
        "When can they come in?",
        min_memory_version=saved.memory_version,
    )
```

## TypeScript

```bash
npm install @contextdb/cloud
```

```ts
import { CloudClient } from "@contextdb/cloud";

const db = new CloudClient({
  baseUrl: "https://api.contextdb.ai",
  apiKey: process.env.CONTEXTDB_API_KEY!,
});
```

Project API keys are server credentials. Never place them in browser code.

## Contract

`openapi/v1alpha.yaml` is the strict API contract consumed by both clients.
Server implementation code is intentionally absent.

## What can you build with ContextDB Cloud?

### Voice agents that remember caller preferences

Store appointment windows, language preferences, accessibility needs, and
confirmed constraints so callers do not repeat themselves on every call.

### Support agents that distinguish facts from wishes

Recall conversational context normally, then use action evaluation before
refunds, bookings, cancellations, or account changes.

### Workflow agents with an execution audit trail

Link the memory considered, act/ask/abstain decision, confirmation, and final
execution receipt under one durable decision ID.

### Read-after-write memory flows

Pass the returned `memory_version` and WAL position into recall when the next
turn must observe a newly written or deleted memory.

## Links

- [ContextDB Cloud documentation](https://contextdb.ai/docs)
- [Python package on PyPI](https://pypi.org/project/contextdb-cloud-client/)
- [TypeScript package on npm](https://www.npmjs.com/package/@contextdb/cloud)
- [ContextDB open-source engine](https://github.com/atomsai/contextdb)
- [Release notes](https://github.com/atomsai/contextdb-clients/releases)

## Frequently asked questions

### Is this the ContextDB server?

No. This repository contains public client libraries and API schemas. It does
not contain hosted service implementation code.

### Can I use ContextDB without Cloud?

Yes. Install the [Apache-2.0 `pycontextdb` engine](https://pypi.org/project/pycontextdb/)
for local or self-hosted memory.

### Can I put a ContextDB project key in browser code?

No. A `cdb_` key is a server credential. Keep it in a backend secret store.

### Is ContextDB Cloud production-ready?

The clients and hosted service are alpha. No public availability SLA is
claimed.

## License

Apache-2.0. ContextDB trademarks are not licensed by Apache-2.0.
