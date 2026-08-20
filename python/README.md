# ContextDB Cloud Python SDK for AI agent memory

Remote client for the ContextDB Cloud data plane. The hosted API and this
package are alpha and do not carry a production availability commitment.

```python
from contextdb_cloud_client import CloudClient

async with CloudClient("https://api.contextdb.ai", api_key="cdb_…") as cdb:
    saved = await cdb.remember(
        "caller-1", "Thursday works", source="user_stated",
        confidence=0.9, idempotency_key="call-456-preference-v1",
    )
    context = await cdb.recall(
        "caller-1",
        "when can they come in?",
        min_memory_version=saved.memory_version,
        min_primary_wal_lsn=saved.primary_wal_lsn,
    )
    decision = await cdb.evaluate_action("caller-1", "book the visit")
    if decision.outcome == "act":
        # Execute in your host, then close the Action Ledger.
        await cdb.report_execution(
            "caller-1", decision.decision_id, "appointment.book", "succeeded",
            idempotency_key=f"receipt-{decision.decision_id}",
            external_ref="appt-8842",
        )
    pending = await cdb.pending_confirmations("caller-1")
```

`LocalClient` wraps the in-process memory calls for offline development.
Cloud-only control-plane features such as durable action decisions and
execution receipts require `CloudClient`.

The API key is a project-wide server credential (`cdb_…`). Keep it in your
server's secret store; never in a browser or client-side code.

Pass a stable `idempotency_key` when retrying `remember`, `remember_many`,
`confirm`, or `extract_memories(..., mode="commit")`. Reuse the key only for
the exact same logical request.

Delete one bad memory with `forget(user_id, memory_id=...)`. Whole-partition
erasure is deliberately harder: pass `erase_partition=True`,
`confirmation=user_id`, and an `idempotency_key`; Cloud deletes the partition
and verifies that no memory rows or vector-index IDs remain.

## Use cases

- **AI voice agents:** remember caller preferences and confirmed constraints
  across calls.
- **Customer support agents:** retrieve prior context while requiring trusted
  evidence before consequential actions.
- **Workflow agents:** record act/ask/abstain decisions and report execution
  outcomes.
- **Privacy operations:** delete one memory, a stable slot, or a complete user
  partition with verification.

## Links

- [API documentation](https://contextdb.ai/docs)
- [Source and examples](https://github.com/atomsai/contextdb-clients)
- [Open-source ContextDB engine](https://pypi.org/project/pycontextdb/)
- [Release notes](https://github.com/atomsai/contextdb-clients/releases)

## Is this package production-ready?

No. `contextdb-cloud-client` and the hosted service are alpha. The package does
not claim a public availability SLA.
