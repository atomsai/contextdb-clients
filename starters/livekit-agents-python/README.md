# Persistent caller memory for LiveKit Agents

This starter gives a LiveKit voice agent memory across rooms and calls.
LiveKit manages the realtime session and tools. PyAI Hear and Speak provide the
speech plugins. ContextDB recalls the caller's selected facts before each model
reply.

Use it for appointment lines, support calls, account service, collections
workflows, or any voice agent where callers should not repeat stable
preferences on every call.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python agent.py dev
```

Create LiveKit, PyAI, OpenAI, and ContextDB keys before starting the worker.
The sample follows the current
[LiveKit Agents](https://docs.livekit.io/agents/) `AgentSession`,
`on_user_turn_completed`, `function_tool`, and shutdown callback APIs.

## Recall before the voice reply

LiveKit calls `on_user_turn_completed` after the caller's turn ends and before
the agent replies:

```python
recalled = await self._memory.recall(
    self._user_id,
    new_message.text_content,
    top_k=5,
)

if recalled.context:
    turn_ctx.add_message(
        role="assistant",
        content=f"Relevant ContextDB memory:\n{recalled.context}",
    )
```

This keeps recalled memory turn-local instead of permanently copying it into
LiveKit chat history.

## Pick the right caller ID

`CONTEXTDB_USER_ID` is fixed only to keep the starter small. In production,
resolve a stable application user or verified caller ID on your server. Do not
use a room name, call SID, or temporary participant identity if the same person
should be remembered on a later call.

The `remember_user_fact` tool writes as `agent_inferred` because the model
selects and phrases the fact. Store exact caller words as `user_stated` only
when your host preserves that provenance.

## Actions

Before booking, cancelling, taking payment, or changing an account, use
`memory.evaluate_action(...)`. Only execute when ContextDB returns `act`.
Handle `ask` by confirming the pending memory with the caller.

Validate the caller partition and action query in the
[ContextDB Memory Testbench](https://app.contextdb.ai/testbench).

## Security

Keep `CONTEXTDB_API_KEY` and every provider key in the worker environment or a
server secret manager. Never put the ContextDB key in LiveKit room metadata or
participant attributes.

Status: reference starter verified against `livekit-agents==1.7.0`,
`livekit-plugins-pyai==0.1.0`, and matching LiveKit plugins on 2026-08-21.
ContextDB Cloud remains alpha.
