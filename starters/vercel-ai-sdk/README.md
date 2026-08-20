# Persistent memory for Vercel AI SDK agents

This TypeScript starter recalls ContextDB memory before `generateText` and
adds a typed tool for storing a selected durable fact. AI SDK manages model and
tool execution. ContextDB keeps user memory available after a request, process,
deployment, or chat thread ends.

Use it for Next.js support assistants, workflow agents, account copilots, and
server-side AI routes that should recognize a returning user.

## Run it

```bash
npm install
cp .env.example .env
set -a; source .env; set +a
npm start -- "Which appointment day do I prefer?"
```

The starter follows the current
[Vercel AI SDK](https://ai-sdk.dev/docs/introduction) `generateText`, `tool`,
`inputSchema`, and `isStepCount` APIs.

## Recall and inject context

```ts
const recalled = await memory.recall(userId, prompt, { topK: 5 });

const result = await generateText({
  model: openai("gpt-5-mini"),
  system: `Use recalled memory only when relevant.\n${recalled.context}`,
  prompt,
  tools: { rememberUserFact },
  stopWhen: isStepCount(5),
});
```

The `rememberUserFact` tool stores `agent_inferred` provenance because the
model chooses and phrases the fact. If your server stores exact user words
without model interpretation, use `user_stated`.

## Use it in a Next.js route

Move the body of `index.ts` into a server route, server action, queue worker, or
backend service. Resolve `userId` from authenticated server state. Do not accept
an arbitrary user partition from an untrusted browser.

Before an external side effect:

```ts
const decision = await memory.evaluateAction(
  userId,
  "Cancel the order using the recalled request",
);

if (decision.outcome === "act") {
  // Execute, then report the receipt.
}
```

Handle `ask` with explicit confirmation and treat `abstain` as a hard stop.
Validate the query in the
[ContextDB Memory Testbench](https://app.contextdb.ai/testbench).

## Security

`@contextdb/cloud` is server-only and fails closed in browser code. Keep
`CONTEXTDB_API_KEY` in Vercel environment variables or another server secret
store. Never prefix it with `NEXT_PUBLIC_`.

Status: reference starter compiled with `ai@7.0.70` and
`@ai-sdk/openai@4.0.44` on 2026-08-21. ContextDB Cloud remains alpha.
