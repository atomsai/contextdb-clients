"""Typed contracts for the data-plane API, mirroring clients/openapi/v1alpha.yaml.

Keep these in sync with the contract in the same PR that changes either.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

EpistemicSource = Literal["user_stated", "agent_inferred", "third_party"]
FormationMode = Literal["propose", "commit"]
ActionOutcome = Literal["act", "ask", "abstain"]
ReceiptStatus = Literal["succeeded", "failed", "skipped"]
PolicyAlignment = Literal["aligned", "violated"]
ForgetMode = Literal["memory", "slot", "partition"]
ReadConsistency = Literal["default", "primary", "replica_fallback"]
FormationStatus = Literal[
    "completed",
    "no_memories",
    "provider_unavailable",
    "provider_error",
    "invalid_output",
    "timed_out",
    "budget_exhausted",
    "storage_error",
    "internal_error",
    "interrupted",
]


class ApiError(Exception):
    """A data-plane error response: machine code, human message, request id."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        request_id: str | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.request_id = request_id
        super().__init__(f"[{status}] {code}: {message}")


@dataclass(frozen=True)
class ConsistencyToken:
    memory_version: int
    primary_wal_lsn: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConsistencyToken:
        return cls(
            memory_version=int(data["memory_version"]),
            primary_wal_lsn=data.get("primary_wal_lsn"),
        )


@dataclass(frozen=True)
class Memory:
    id: str
    content: str
    user_id: str | None
    epistemic_source: str
    confidence: float
    corroboration_count: int
    action_relevant: bool
    requires_confirmation: bool
    confirmed: bool
    independent_corroboration: int
    injection_suspect: bool
    entity_key: str | None
    attribute_key: str | None
    valid_until: str | None
    superseded_by: str | None
    memory_version: int | None = None
    primary_wal_lsn: str | None = None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        consistency: dict[str, Any] | None = None,
    ) -> Memory:
        token = consistency or {}
        return cls(
            id=str(data["id"]),
            content=str(data["content"]),
            user_id=data.get("user_id"),
            epistemic_source=str(data["epistemic_source"]),
            confidence=float(data["confidence"]),
            corroboration_count=int(data["corroboration_count"]),
            action_relevant=bool(data["action_relevant"]),
            requires_confirmation=bool(data["requires_confirmation"]),
            confirmed=bool(data["confirmed"]),
            independent_corroboration=int(data["independent_corroboration"]),
            injection_suspect=bool(data["injection_suspect"]),
            entity_key=data.get("entity_key"),
            attribute_key=data.get("attribute_key"),
            valid_until=data.get("valid_until"),
            superseded_by=data.get("superseded_by"),
            memory_version=(
                int(token["memory_version"])
                if token.get("memory_version") is not None
                else None
            ),
            primary_wal_lsn=token.get("primary_wal_lsn"),
        )


@dataclass(frozen=True)
class RecallResult:
    context: str
    memories: list[Memory]


@dataclass(frozen=True)
class ActionDecision:
    decision_id: str
    outcome: ActionOutcome
    memories: list[Memory]
    pending_confirmation_ids: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionDecision:
        return cls(
            decision_id=str(data["decision_id"]),
            outcome=data["outcome"],
            memories=[Memory.from_dict(memory) for memory in data["memories"]],
            pending_confirmation_ids=[
                str(memory_id)
                for memory_id in data["pending_confirmation_ids"]
            ],
        )


@dataclass(frozen=True)
class ExecutionReceipt:
    id: str
    decision_id: str
    action_name: str
    status: ReceiptStatus
    policy_alignment: PolicyAlignment
    external_ref: str | None
    error_code: str | None
    request_id: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionReceipt:
        return cls(
            id=str(data["id"]),
            decision_id=str(data["decision_id"]),
            action_name=str(data["action_name"]),
            status=data["status"],
            policy_alignment=data["policy_alignment"],
            external_ref=data.get("external_ref"),
            error_code=data.get("error_code"),
            request_id=str(data["request_id"]),
            created_at=str(data["created_at"]),
        )


@dataclass(frozen=True)
class ExecutionReceiptResponse:
    decision_id: str
    outcome: ActionOutcome
    receipt: ExecutionReceipt

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ExecutionReceiptResponse:
        return cls(
            decision_id=str(data["decision_id"]),
            outcome=data["outcome"],
            receipt=ExecutionReceipt.from_dict(data["receipt"]),
        )


@dataclass(frozen=True)
class ForgetResponse:
    mode: ForgetMode
    deleted: int
    verified: bool | None
    request_id: str
    memory_version: int
    primary_wal_lsn: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForgetResponse:
        return cls(
            mode=data["mode"],
            deleted=int(data["deleted"]),
            verified=data.get("verified"),
            request_id=str(data["request_id"]),
            memory_version=int(data["memory_version"]),
            primary_wal_lsn=data.get("primary_wal_lsn"),
        )


@dataclass(frozen=True)
class Health:
    ok: bool
    service: str
    sdk_pin: str | None


@dataclass(frozen=True)
class Ready:
    ready: bool
    checks: dict[str, bool]


@dataclass(frozen=True)
class FormationCandidate:
    content: str
    quote: str
    turn_indexes: list[int]
    source: str
    confidence: float
    action_relevant: bool
    entity: str | None
    attribute: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormationCandidate:
        return cls(
            content=str(data["content"]),
            quote=str(data["quote"]),
            turn_indexes=[int(index) for index in data["turn_indexes"]],
            source=str(data["source"]),
            confidence=float(data["confidence"]),
            action_relevant=bool(data["action_relevant"]),
            entity=data.get("entity"),
            attribute=data.get("attribute"),
        )


@dataclass(frozen=True)
class FormationResponse:
    run_id: str
    status: FormationStatus
    mode: FormationMode
    attempts: int
    candidates: list[FormationCandidate]
    memories: list[Memory]
    error_code: str | None
    request_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormationResponse:
        return cls(
            run_id=str(data["run_id"]),
            status=data["status"],
            mode=data["mode"],
            attempts=int(data["attempts"]),
            candidates=[
                FormationCandidate.from_dict(candidate)
                for candidate in data["candidates"]
            ],
            memories=[Memory.from_dict(memory) for memory in data["memories"]],
            error_code=data.get("error_code"),
            request_id=str(data["request_id"]),
        )
