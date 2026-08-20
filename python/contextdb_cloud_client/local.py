"""LocalClient — the same call surface over the in-process Apache SDK.

Local/Cloud parity: code written against this surface runs identically
against a local SDK runtime (development, offline) and the Cloud data plane
(CloudClient). The trust behavior is the SDK's in both cases — Cloud hosts
the same engine.

Requires pycontextdb for local mode: `pip install pycontextdb` (or the
pinned revision used by the gateway).
"""

from __future__ import annotations

from typing import Any

from contextdb_cloud_client.types import (
    EpistemicSource,
    ForgetResponse,
    Health,
    Memory,
    ReadConsistency,
    Ready,
    RecallResult,
)


def _from_item(item: Any, token: Any | None = None) -> Memory:
    return Memory(
        id=item.id,
        content=item.content,
        user_id=item.user_id,
        epistemic_source=item.epistemic_source,
        confidence=float(item.confidence),
        corroboration_count=int(item.corroboration_count),
        action_relevant=bool(item.action_relevant),
        requires_confirmation=bool(item.requires_confirmation),
        confirmed=bool(item.confirmed),
        independent_corroboration=int(item.independent_corroboration),
        injection_suspect=bool(item.injection_suspect),
        entity_key=item.entity_key,
        attribute_key=item.attribute_key,
        valid_until=item.valid_until.isoformat() if item.valid_until else None,
        superseded_by=item.superseded_by,
        memory_version=(
            int(token.memory_version) if token is not None else None
        ),
        primary_wal_lsn=(
            token.primary_wal_lsn if token is not None else None
        ),
    )


class LocalClient:
    """Parity adapter over an unscoped ``contextdb`` client (user per call)."""

    def __init__(self, db: Any) -> None:
        # db: an unscoped contextdb.ContextDB (contextdb.init() with no
        # user_id); each call passes user_id, same as the Cloud contract.
        self._db = db

    async def health(self) -> Health:
        return Health(ok=True, service="contextdb-local", sdk_pin=None)

    async def ready(self) -> Ready:
        await self._db._ensure_init()
        return Ready(ready=True, checks={"memory_store": True})

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
        item = await self._db.factual.add(
            content,
            source=source,
            confidence=confidence if confidence is not None else 1.0,
            action_relevant=action_relevant,
            entity=entity,
            attribute=attribute,
            user_id=user_id,
        )
        return _from_item(item, await self._db.consistency_token())

    async def remember_many(
        self,
        user_id: str,
        items: list[dict[str, Any]],
        *,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> list[Memory]:
        stored = await self._db.factual.add_many(items, user_id=user_id)
        token = await self._db.consistency_token()
        return [_from_item(memory, token) for memory in stored]

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
        from contextdb.integrations.prompting import render_recalled_context

        if (
            min_memory_version is not None
            or min_primary_wal_lsn is not None
        ):
            await self._db.require_consistency(
                min_memory_version=min_memory_version,
                min_wal_lsn=min_primary_wal_lsn,
            )
        items = await self._db.factual.recall(
            query,
            top_k=top_k,
            user_id=user_id,
            entity=entity,
            min_confidence=min_confidence,
        )
        return RecallResult(
            context=render_recalled_context(items, max_tokens=512),
            memories=[_from_item(m) for m in items],
        )

    async def recall_for_action(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int = 5,
        request_id: str | None = None,
    ) -> list[Memory]:
        items = await self._db.factual.recall_for_action(
            query, top_k=top_k, user_id=user_id
        )
        return [_from_item(m) for m in items]

    async def pending_confirmations(self, user_id: str) -> list[Memory]:
        items = await self._db.factual.pending_confirmations(user_id=user_id)
        return [_from_item(m) for m in items]

    async def confirm(
        self,
        user_id: str,
        memory_id: str,
        *,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Memory:
        item = await self._db.factual.confirm(memory_id, user_id=user_id)
        return _from_item(item, await self._db.consistency_token())

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
        if memory_id is not None:
            mode = "memory"
            deleted = await self._db.forget(
                user_id=user_id,
                memory_id=memory_id,
            )
            verified = None
        elif entity is not None and attribute is not None:
            mode = "slot"
            deleted = await self._db.forget(
                user_id=user_id,
                entity=entity,
                attribute=attribute,
            )
            verified = None
        else:
            mode = "partition"
            deleted = await self._db.forget_user(user_id)
            verified = await self._db.verify_forgotten(user_id)
        token = await self._db.consistency_token()
        return ForgetResponse(
            mode=mode,
            deleted=deleted,
            verified=verified,
            request_id=request_id or "local",
            memory_version=token.memory_version,
            primary_wal_lsn=token.primary_wal_lsn,
        )

    async def close(self) -> None:
        await self._db.close()
