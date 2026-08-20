# AI agent memory starter kits

Add persistent, action-aware memory to OpenAI Agents, LangGraph, Vercel AI SDK,
LiveKit Agents, or PyAI voice agents. Each starter uses the public ContextDB
Cloud client and keeps every project key in server-side environment variables.

These are thin Apache-2.0 reference integrations. They contain no ContextDB
Cloud server, billing, tenant control plane, managed-source worker, or
enterprise implementation.

## Pick your framework

| Framework | Language | What the starter demonstrates |
|---|---|---|
| [OpenAI Agents SDK](openai-agents-python/) | Python | Recall before `Runner.run` plus a typed `remember_user_fact` tool |
| [LangGraph](langgraph-python/) | Python | Recall inside a graph node before model invocation |
| [Vercel AI SDK](vercel-ai-sdk/) | TypeScript | Recall in `generateText` plus a server-side memory tool |
| [LiveKit Agents](livekit-agents-python/) | Python | Per-turn recall with `on_user_turn_completed` and PyAI speech plugins |
| [PyAI Omni](pyai-omni/) | TypeScript | ContextDB grounding inside the official `OmniAgent.bridge` knowledge callback |

Copy one starter without cloning the full repository:

```bash
npx degit atomsai/contextdb-clients/starters contextdb-agent-starters
cd contextdb-agent-starters/openai-agents-python
```

Open another directory from the table to use a different framework. The copied
bundle includes the Apache-2.0 license and notice.

## The memory lifecycle used by every kit

1. Resolve a stable `user_id` on your server.
2. Recall relevant memory before the model answers.
3. Inject the returned, guarded `context` into that turn.
4. Write only explicit or deliberately selected durable facts.
5. Use `evaluate_action` or `evaluateAction` before a memory influences an
   external side effect.
6. Confirm uncertain evidence, then report the execution receipt.

ContextDB memory is separate from framework thread state. A LangGraph
`thread_id`, LiveKit room, OpenAI session, or PyAI call can end while the same
user partition remains available on the next interaction.

## Required environment

Every starter expects:

```bash
CONTEXTDB_API_KEY=cdb_...
CONTEXTDB_USER_ID=customer-or-caller-id
```

Get a project key from [ContextDB Cloud](https://app.contextdb.ai). Validate
your memory and action behavior in the
[Memory Testbench](https://app.contextdb.ai/testbench) before connecting a
production action.

Project keys are server credentials. Never place a `cdb_` key in a browser,
mobile application, public LiveKit participant attribute, or client-visible
PyAI configuration.

## Frequently asked questions

### Does ContextDB replace framework chat history?

No. Keep OpenAI sessions, LangGraph checkpoints, AI SDK messages, LiveKit chat
context, or PyAI call state for the active interaction. Use ContextDB for
selected user memory that should survive the end of that interaction.

### Should an agent save every message?

No. Store explicit or deliberately selected durable facts. The starters either
use a narrowly described memory tool, ask the host to select a fact, or require
an explicit `remember that` phrase.

### Can recalled memory authorize an action?

Not by ordinary recall alone. Call ContextDB action evaluation before an
external side effect. Execute only on `act`; handle `ask` with confirmation and
treat `abstain` as a stop.

### Are these framework implementations part of ContextDB Cloud?

No. They are public reference applications over the published client
contract. Hosted tenancy, operations, billing, and managed services remain
private.

### Are the starters production-ready?

They are tested alpha references, not a deployment or availability guarantee.
Review identity mapping, retention, error handling, and action policy for your
application before production use.

## Compatibility status

The source and dependency imports are checked in CI. External framework APIs
were verified against their official documentation on 2026-08-21. The hosted
ContextDB service and clients remain alpha, with no public availability SLA.

Official references:

- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
- [Vercel AI SDK](https://ai-sdk.dev/docs/introduction)
- [LiveKit Agents](https://docs.livekit.io/agents/)
- [PyAI developer guide](https://pyai.com/AGENTS.md)
