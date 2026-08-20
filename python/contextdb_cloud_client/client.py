"""CloudClient — the remote client for the ContextDB Cloud data plane.

Speaks the versioned contract in clients/openapi/v1alpha.yaml. The API key
is a project-wide server credential (`cdb_…`): keep it in your server's
secret store, never in a browser or client-side code.

Hosted alpha. Not production-ready.
"""

from __future__ import annotations

from typing import Any

import httpx

from contextdb_cloud_client.types import (
    ActionDecision,
    ApiError,
    EpistemicSource,
    ExecutionReceiptResponse,
    ForgetResponse,
    FormationMode,
    FormationResponse,
    Health,
    Memory,
    ReadConsistency,
    Ready,
    RecallResult,
    ReceiptStatus,
)


class CloudClient:
    """Async client for the alpha data plane. One instance per project key."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.startswith("cdb_"):
            raise ValueError("api_key must be a project key (cdb_…)")
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> CloudClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    async def _call(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"X-Request-ID": request_id} if request_id else {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        resp = await self._http.request(
            method, path, json=json, params=params, headers=headers
        )
        try:
            data = resp.json()
        except ValueError:
            raise ApiError(resp.status_code, "non_json", "non-JSON response") from None
        if not resp.is_success:
            raise ApiError(
                resp.status_code,
                str(data.get("code", "error")),
                str(data.get("message", f"HTTP {resp.status_code}")),
                data.get("request_id"),
            )
        return data

    async def health(self) -> Health:
        data = await self._call("GET", "/health")
        return Health(
            ok=bool(data["ok"]),
            service=str(data["service"]),
            sdk_pin=data.get("sdk_pin"),
        )

    async def ready(self) -> Ready:
        resp = await self._http.get("/ready")
        data = resp.json()
        return Ready(ready=bool(data["ready"]), checks=dict(data["checks"]))

    async def remember(
        self,
        user_id: str,
        content: str,
        *,
        source: EpistemicSource,
        confidence: float | None = None,
        action_relevant: bool | None = None,
        entity: str | None = None,
        attribute: str | None = None,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Memory:
        """Store one memory. ``source`` is required provenance."""
        body: dict[str, Any] = {"user_id": user_id, "content": content, "source": source}
        if confidence is not None:
            body["confidence"] = confidence
        if action_relevant is not None:
            body["action_relevant"] = action_relevant
        if entity is not None:
            body["entity"] = entity
        if attribute is not None:
            body["attribute"] = attribute
        data = await self._call(
            "POST",
            "/v1/remember",
            json=body,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return Memory.from_dict(data["memory"], data)

    async def remember_many(
        self,
        user_id: str,
        items: list[dict[str, Any]],
        *,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> list[Memory]:
        """LLM-free batch store. Items without ``source`` take the fast path."""
        data = await self._call(
            "POST",
            "/v1/remember_many",
            json={"user_id": user_id, "items": items},
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return [
            Memory.from_dict(memory, data)
            for memory in data["memories"]
        ]

    async def extract_memories(
        self,
        user_id: str,
        turns: list[dict[str, str]],
        *,
        mode: FormationMode = "propose",
        source_id: str | None = None,
        max_memories: int = 10,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> FormationResponse:
        """Extract sourced memories from a bounded conversation.

        Named provider/timeout/storage failures are returned as
        ``FormationResponse`` even when the HTTP status is non-2xx, so callers
        can route on why formation stopped. Protocol/auth errors still raise
        ``ApiError``.
        """
        body: dict[str, Any] = {
            "user_id": user_id,
            "turns": turns,
            "mode": mode,
            "max_memories": max_memories,
        }
        if source_id is not None:
            body["source_id"] = source_id
        headers = {"X-Request-ID": request_id} if request_id else {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        response = await self._http.post(
            "/v1/extract_memories",
            json=body,
            headers=headers,
        )
        try:
            data = response.json()
        except ValueError:
            raise ApiError(
                response.status_code, "non_json", "non-JSON response"
            ) from None
        if "run_id" in data and "status" in data:
            return FormationResponse.from_dict(data)
        if not response.is_success:
            raise ApiError(
                response.status_code,
                str(data.get("code", "error")),
                str(data.get("message", f"HTTP {response.status_code}")),
                data.get("request_id"),
            )
        raise ApiError(
            response.status_code,
            "invalid_response",
            "formation response is missing terminal status",
            data.get("request_id"),
        )

    async def recall(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int = 5,
        entity: str | None = None,
        min_confidence: float | None = None,
        min_memory_version: int | None = None,
        min_primary_wal_lsn: str | None = None,
        read_consistency: ReadConsistency = "default",
        request_id: str | None = None,
    ) -> RecallResult:
        """Recall memories for grounding, with injection-guarded context."""
        body: dict[str, Any] = {"user_id": user_id, "query": query, "top_k": top_k}
        if entity is not None:
            body["entity"] = entity
        if min_confidence is not None:
            body["min_confidence"] = min_confidence
        if min_memory_version is not None:
            body["min_memory_version"] = min_memory_version
        if min_primary_wal_lsn is not None:
            body["min_primary_wal_lsn"] = min_primary_wal_lsn
        if read_consistency != "default":
            body["read_consistency"] = read_consistency
        data = await self._call("POST", "/v1/recall", json=body, request_id=request_id)
        return RecallResult(
            context=str(data["context"]),
            memories=[Memory.from_dict(m) for m in data["memories"]],
        )

    async def recall_for_action(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int = 5,
        request_id: str | None = None,
    ) -> list[Memory]:
        """Compatibility helper returning trusted memory only.

        Use :meth:`evaluate_action` when the host will report an execution
        receipt.
        """
        data = await self._call(
            "POST",
            "/v1/recall_for_action",
            json={"user_id": user_id, "query": query, "top_k": top_k},
            request_id=request_id,
        )
        return [Memory.from_dict(memory) for memory in data["memories"]]

    async def evaluate_action(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int = 5,
        request_id: str | None = None,
    ) -> ActionDecision:
        """Return the durable action decision and its receipt target."""
        data = await self._call(
            "POST",
            "/v1/recall_for_action",
            json={"user_id": user_id, "query": query, "top_k": top_k},
            request_id=request_id,
        )
        return ActionDecision.from_dict(data)

    async def pending_confirmations(self, user_id: str) -> list[Memory]:
        """Facts waiting on a human yes for this partition."""
        data = await self._call(
            "GET", "/v1/pending_confirmations", params={"user_id": user_id}
        )
        return [Memory.from_dict(m) for m in data["memories"]]

    async def confirm(
        self,
        user_id: str,
        memory_id: str,
        *,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Memory:
        """Record an explicit user confirmation for a pending memory.

        Closes the ask -> confirm -> act loop: the fact becomes confirmed
        and passes ``recall_for_action``. A memory outside this project's
        partition raises ``ApiError`` with status 404 — indistinguishable
        from a missing one.
        """
        data = await self._call(
            "POST",
            "/v1/confirm",
            json={"user_id": user_id, "memory_id": memory_id},
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return Memory.from_dict(data["memory"], data)

    async def forget(
        self,
        user_id: str,
        *,
        memory_id: str | None = None,
        entity: str | None = None,
        attribute: str | None = None,
        erase_partition: bool = False,
        confirmation: str | None = None,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> ForgetResponse:
        """Delete one memory, one slot, or a verified user partition."""
        if (entity is None) != (attribute is None):
            raise ValueError("entity and attribute must be set together")
        modes = int(memory_id is not None) + int(entity is not None)
        modes += int(erase_partition)
        if modes != 1:
            raise ValueError(
                "choose memory_id, entity+attribute, or erase_partition"
            )
        if erase_partition and (
            confirmation != user_id or idempotency_key is None
        ):
            raise ValueError(
                "partition erasure requires confirmation=user_id and "
                "idempotency_key"
            )
        body: dict[str, Any] = {
            "user_id": user_id,
            "erase_partition": erase_partition,
        }
        if memory_id is not None:
            body["memory_id"] = memory_id
        if entity is not None:
            body["entity"] = entity
            body["attribute"] = attribute
        if confirmation is not None:
            body["confirmation"] = confirmation
        data = await self._call(
            "POST",
            "/v1/forget",
            json=body,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return ForgetResponse.from_dict(data)

    async def report_execution(
        self,
        user_id: str,
        decision_id: str,
        action_name: str,
        status: ReceiptStatus,
        *,
        idempotency_key: str,
        external_ref: str | None = None,
        error_code: str | None = None,
        request_id: str | None = None,
    ) -> ExecutionReceiptResponse:
        """Attach one terminal, host-reported outcome to an action decision."""
        body: dict[str, Any] = {
            "user_id": user_id,
            "decision_id": decision_id,
            "action_name": action_name,
            "status": status,
        }
        if external_ref is not None:
            body["external_ref"] = external_ref
        if error_code is not None:
            body["error_code"] = error_code
        data = await self._call(
            "POST",
            "/v1/receipts",
            json=body,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return ExecutionReceiptResponse.from_dict(data)
