# Persistent caller memory for PyAI Omni voice agents

This starter connects ContextDB to the official PyAI Twilio bridge. PyAI Omni
handles the realtime voice session. ContextDB supplies relevant memory through
the bridge's per-turn `knowledge` callback.

Use it for phone support, appointment scheduling, account service, and other
returning-caller flows where selected facts should survive the end of a call.

## Run it

```bash
npm install
cp .env.example .env
set -a; source .env; set +a
npm start
```

Expose port 8080 through your normal HTTPS tunnel or deployment. Point the
Twilio number's incoming voice webhook to:

```text
https://YOUR_HOST/voice
```

The starter follows the official
[PyAI Omni and Twilio example](https://github.com/atomsai/pyai-examples/tree/main/twilio-omni-voice-agent).

## Recall on every turn

```ts
knowledge: async (query) => {
  const recalled = await memory.recall(userId, query, { topK: 5 });
  return recalled.context || "No relevant saved user memory.";
},
```

The example stores a fact only when the caller explicitly says
`remember that ...`. It does not persist every transcript. Replace this small
policy with your own reviewed extraction or explicit account workflow.

## Resolve caller identity on the server

`CONTEXTDB_USER_ID` is fixed only for the starter. In production, derive a
stable user partition from your authenticated customer record or verified
caller mapping. Do not use a one-time call SID when memory should carry into
the next call.

Do not send a raw phone number as the ContextDB user ID unless that choice
matches your privacy model. A stable internal customer ID is usually safer.

## Gate actions separately

The `knowledge` callback is for conversational grounding. Before Omni triggers
a booking, cancellation, payment, transfer with account effects, or another
external mutation, call `memory.evaluateAction(...)`. Execute only on `act`.
Handle `ask` with caller confirmation and treat `abstain` as a stop.

Validate the caller partition and action query in the
[ContextDB Memory Testbench](https://app.contextdb.ai/testbench).

## Security

Keep `CONTEXTDB_API_KEY` and `PYAI_API_KEY` on the bridge server. Never send the
ContextDB key through Twilio media metadata, an Omni configure frame, or
browser code.

Status: reference starter compiled with `@pyai/twilio@0.4.1` on 2026-08-21.
PyAI and ContextDB service availability claims are not made by this starter.
