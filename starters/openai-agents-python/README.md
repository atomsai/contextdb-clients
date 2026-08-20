# Persistent memory for OpenAI Agents SDK

This starter recalls ContextDB memory before `Runner.run` and gives the agent a
typed tool for storing a deliberately selected durable fact. OpenAI session
history handles the current thread. ContextDB carries useful user context into
the next thread, process, or channel.

Use it for support agents, account assistants, scheduling agents, and other
agents that should recognize a returning user without treating every chat
message as permanent memory.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python agent.py
```

The starter follows the current
[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) `Agent`,
`Runner`, and `tool` APIs.

## What happens on each run

```python
recalled = await memory.recall(user_id, prompt, top_k=5)
agent = build_agent(memory, user_id, recalled.context)
result = await Runner.run(agent, prompt)
```

The model receives ContextDB's guarded context as additional instructions for
that run. The `remember_user_fact` tool writes with
`source="agent_inferred"` because the model selects and phrases the fact. If
your application stores the user's exact words directly, use
`source="user_stated"` instead.

## Before an external action

Normal recall is for grounding. Before booking, refunding, cancelling, paying,
or changing an account, call:

```python
decision = await memory.evaluate_action(
    user_id,
    "Book the appointment using the recalled preference",
)

if decision.outcome == "act":
    # Execute the action, then report its receipt.
    ...
elif decision.outcome == "ask":
    # Ask the user to confirm the pending memory.
    ...
else:
    # Do not act from memory.
    ...
```

Test this exact user partition and query in the
[ContextDB Memory Testbench](https://app.contextdb.ai/testbench).

## Security

Run this code on a server. `CONTEXTDB_API_KEY` and `OPENAI_API_KEY` must never
be bundled into browser code. Do not store passwords, payment data, access
tokens, or one-time codes as agent memory.

Status: reference starter verified against `openai-agents==0.22.0` on
2026-08-21. ContextDB Cloud remains alpha.
