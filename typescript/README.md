# @contextdb/cloud

Thin TypeScript client for the hosted ContextDB data plane.

```bash
npm install @contextdb/cloud
```

```ts
import { CloudClient } from "@contextdb/cloud";

const db = new CloudClient({
  baseUrl: "https://api.contextdb.ai",
  apiKey: process.env.CONTEXTDB_API_KEY!,
});

const saved = await db.remember(
  "caller-1",
  "Thursday works",
  { source: "user_stated" },
);
```

Project API keys are server credentials. Do not expose them to browser code.

The package is alpha. It contains no ContextDB Cloud server implementation.
