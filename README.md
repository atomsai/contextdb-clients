# ContextDB Cloud clients

Public, thin clients and API contracts for the hosted ContextDB data plane.
The clients contain request/response types and transport helpers only; the
multi-tenant server, control plane, managed sources, operations, and enterprise
implementation remain private.

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

## License

Apache-2.0. ContextDB trademarks are not licensed by Apache-2.0.
