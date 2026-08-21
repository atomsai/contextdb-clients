# ContextDB Cloud TypeScript SDK for AI agent memory

Give Node.js voice, support, and workflow agents persistent memory through the
hosted ContextDB data plane.

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
The package is marked server-only and throws if constructed in a browser
runtime. Use it from Node.js servers, API routes, workers, or server actions.

## Use cases

- Remember caller preferences across Retell, LiveKit, Pipecat, or custom voice
  agent sessions.
- Ground support responses in previous conversations.
- Require an act/ask/abstain decision before consequential tools run.
- Pass consistency tokens when a follow-up recall must observe a recent write.
- Report execution receipts for an auditable memory-to-action timeline.

## Asynchronous Formation

```ts
const submitted = await db.submitFormationJob(
  "caller-1",
  [{ speaker: "user", content: "I prefer Saturday mornings." }],
  {
    mode: "propose",
    idempotencyKey: "call-456-formation-v1",
  },
);

const job = await db.getFormationJob(submitted.job_id);
```

Jobs accept structured text turns and return closed, inspectable statuses.
Formation remains Hosted Alpha with no audio or cancellation contract.

## TypeScript starter kits

- [Vercel AI SDK](https://github.com/atomsai/contextdb-clients/tree/main/starters/vercel-ai-sdk)
- [PyAI Omni voice agents](https://github.com/atomsai/contextdb-clients/tree/main/starters/pyai-omni)

Both starters install this package from npm and compile against their current
framework dependencies in CI.

## Links

- [ContextDB API documentation](https://contextdb.ai/docs)
- [Source and OpenAPI contract](https://github.com/atomsai/contextdb-clients)
- [Python SDK](https://pypi.org/project/contextdb-cloud-client/)
- [Open-source ContextDB engine](https://github.com/atomsai/contextdb)
- [Release notes](https://github.com/atomsai/contextdb-clients/releases)

## Is this package production-ready?

The package is alpha. It contains no ContextDB Cloud server implementation.
No public availability SLA is claimed.
