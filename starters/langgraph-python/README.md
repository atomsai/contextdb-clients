# Persistent memory for LangGraph agents

This starter adds ContextDB recall inside a LangGraph model node. LangGraph
state and checkpointers retain one workflow thread. ContextDB retains selected
user facts across thread IDs, graph deployments, channels, and process
restarts.

Use it when a support, scheduling, research, or workflow graph should recognize
the same user in a later run.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python agent.py
```

The graph uses the current `StateGraph`, `MessagesState`, `START`, and `END`
APIs documented by [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview).

## The memory node pattern

```python
async def call_model(state: AgentState):
    latest = message_text(state["messages"][-1])
    recalled = await memory.recall(state["user_id"], latest, top_k=5)

    system = "Use recalled memory only when relevant."
    if recalled.context:
        system += f"\n\nRelevant ContextDB memory:\n{recalled.context}"

    response = await model.ainvoke(
        [SystemMessage(content=system), *state["messages"]]
    )
    return {"messages": [response]}
```

Do not use a LangGraph `thread_id` as the user partition unless one human can
never have more than one thread. Pass a stable application user or caller ID as
`user_id`; keep workflow checkpoint identity separate.

The sample asks the host to select an exact user-stated fact before writing it.
It does not persist every message automatically.

## Actions and confirmations

Use `memory.evaluate_action(...)` before a recalled fact changes an external
system. If the decision is `ask`, confirm the pending memory after the user
attests to it. If it is `abstain`, continue without acting from memory.

Validate your graph query and expected evidence in the
[ContextDB Memory Testbench](https://app.contextdb.ai/testbench).

## Security

Keep `CONTEXTDB_API_KEY` and model-provider keys in the graph server's secret
store. Never place them in graph state that may be serialized to a client.

Status: reference starter verified against `langgraph==1.2.11` and
`langchain-openai==1.6.0` on 2026-08-21. ContextDB Cloud remains alpha.
