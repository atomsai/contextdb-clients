"""Python remote client — unit tests with a mock transport (no server)."""

from __future__ import annotations

import json

import httpx
import pytest
from contextdb_cloud_client import (
    ApiError,
    CloudClient,
    FormationJob,
    FormationJobSubmission,
    FormationResponse,
    Memory,
)

MEMORY = {
    "id": "m1",
    "content": "I'd like to come in Thursday afternoon.",
    "user_id": "caller-1",
    "epistemic_source": "user_stated",
    "confidence": 0.95,
    "corroboration_count": 1,
    "action_relevant": True,
    "requires_confirmation": False,
    "confirmed": False,
    "independent_corroboration": 1,
    "injection_suspect": False,
    "entity_key": "caller",
    "attribute_key": "preferred_visit_day",
    "valid_until": None,
}

FORMATION_JOB = {
    "job_id": "frm_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "status": "succeeded",
    "mode": "propose",
    "attempt_count": 1,
    "provider_attempts": 1,
    "max_attempts": 3,
    "max_provider_attempts": 2,
    "terminal_reason": "completed",
    "error_code": None,
    "accepted_count": 1,
    "rejected_count": 0,
    "provider": "mock",
    "model": "injected",
    "provider_latency_ms": 5,
    "provider_cost_usd": 0,
    "elapsed_ms": 8,
    "created_at": "2026-08-21T00:00:00+00:00",
    "started_at": "2026-08-21T00:00:00+00:00",
    "completed_at": "2026-08-21T00:00:00+00:00",
    "attempts": [
        {
            "attempt": 1,
            "status": "succeeded",
            "provider_called": True,
            "provider": "mock",
            "model": "injected",
            "latency_ms": 5,
            "accepted_count": 1,
            "rejected_count": 0,
            "provider_cost_usd": 0,
            "error_code": None,
            "failure_reason": None,
            "started_at": "2026-08-21T00:00:00+00:00",
            "finished_at": "2026-08-21T00:00:00+00:00",
        }
    ],
    "result": {
        "mode": "propose",
        "terminal_reason": "completed",
        "candidates": [
            {
                "content": "Customer prefers Saturday",
                "quote": "I prefer Saturday",
                "turn_indexes": [0],
                "source": "user_stated",
                "confidence": 0.9,
                "action_relevant": True,
                "entity": None,
                "attribute": None,
                "accepted": True,
                "rejection_reason": None,
            }
        ],
        "memory_ids": [],
        "memory_version": None,
        "primary_wal_lsn": None,
        "accepted_count": 1,
        "rejected_count": 0,
        "provider": "mock",
        "model": "injected",
        "turns": 1,
        "provider_attempts": 1,
        "provider_latency_ms": 5,
        "provider_cost_usd": 0,
        "error_code": None,
    },
    "request_id": "req-job",
}


def mock_client(status: int, body: dict) -> CloudClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )


def test_constructor_requires_project_key() -> None:
    with pytest.raises(ValueError, match="cdb_"):
        CloudClient("http://x", api_key="not-a-key")


async def test_remember_sends_provenance_and_auth() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers["authorization"]
        seen["idempotency"] = request.headers.get("idempotency-key", "")
        seen["body"] = request.content.decode()
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "memory": MEMORY,
                "memory_version": 3,
                "primary_wal_lsn": "1A/2B",
            },
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    memory = await client.remember(
        "caller-1",
        "Thursday works",
        source="user_stated",
        confidence=0.9,
        idempotency_key="remember-request-0001",
    )
    assert isinstance(memory, Memory)
    assert memory.id == "m1"
    assert memory.memory_version == 3
    assert memory.primary_wal_lsn == "1A/2B"
    assert seen["authorization"] == "Bearer cdb_test"
    assert seen["path"] == "/v1/remember"
    sent = json.loads(seen["body"])
    assert sent["source"] == "user_stated"
    assert sent["user_id"] == "caller-1"
    assert seen["idempotency"] == "remember-request-0001"
    await client.close()


async def test_recall_sends_consistency_floor() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content.decode()))
        return httpx.Response(
            200,
            json={"context": "", "memories": [MEMORY]},
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    result = await client.recall(
        "caller-1",
        "appointment preference",
        min_memory_version=3,
        min_primary_wal_lsn="1A/2B",
        read_consistency="replica_fallback",
    )

    assert seen["min_memory_version"] == 3
    assert seen["min_primary_wal_lsn"] == "1A/2B"
    assert seen["read_consistency"] == "replica_fallback"
    assert result.memories[0].id == "m1"
    await client.close()


async def test_error_mapping_carries_code_and_request_id() -> None:
    client = mock_client(
        401,
        {
            "code": "unauthenticated",
            "message": "unknown or revoked API key",
            "request_id": "req-9",
        },
    )
    with pytest.raises(ApiError) as excinfo:
        await client.recall("u", "q")
    err = excinfo.value
    assert err.status == 401
    assert err.code == "unauthenticated"
    assert err.request_id == "req-9"
    await client.close()


async def test_non_json_response_maps_to_non_json_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, content=b"boom")

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ApiError) as excinfo:
        await client.health()
    assert excinfo.value.code == "non_json"
    await client.close()


async def test_request_id_header_sent_when_provided() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["rid"] = request.headers.get("x-request-id", "")
        return httpx.Response(
            200,
            json={
                "decision_id": "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
                "outcome": "abstain",
                "memories": [],
                "pending_confirmation_ids": [],
            },
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    await client.recall_for_action("u", "q", request_id="req-77")
    assert seen["rid"] == "req-77"
    await client.close()


async def test_pending_confirmations_uses_query_param() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["query"] = request.url.query.decode()
        return httpx.Response(200, json={"memories": [MEMORY]})

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    pending = await client.pending_confirmations("caller-1")
    assert pending[0].entity_key == "caller"
    assert "user_id=caller-1" in seen["query"]
    await client.close()


async def test_extract_memories_returns_named_terminal_on_provider_failure() -> None:
    client = mock_client(
        502,
        {
            "run_id": "form_1",
            "status": "provider_error",
            "mode": "propose",
            "attempts": 2,
            "candidates": [],
            "memories": [],
            "error_code": "provider_error",
            "request_id": "req-formation",
        },
    )

    result = await client.extract_memories(
        "caller-1",
        [{"speaker": "user", "content": "I prefer Saturday."}],
    )

    assert isinstance(result, FormationResponse)
    assert result.status == "provider_error"
    assert result.attempts == 2
    await client.close()


async def test_extract_memories_sends_mode_source_and_request_id() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        seen["rid"] = request.headers["x-request-id"]
        seen["idempotency"] = request.headers["idempotency-key"]
        return httpx.Response(
            200,
            json={
                "run_id": "form_1",
                "status": "no_memories",
                "mode": "commit",
                "attempts": 1,
                "candidates": [],
                "memories": [],
                "error_code": None,
                "request_id": "req-formation",
            },
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    result = await client.extract_memories(
        "caller-1",
        [{"speaker": "user", "content": "Thanks."}],
        mode="commit",
        source_id="call-1",
        request_id="req-formation",
        idempotency_key="formation-request-0001",
    )

    sent = json.loads(seen["body"])
    assert sent["source_id"] == "call-1"
    assert sent["mode"] == "commit"
    assert seen["rid"] == "req-formation"
    assert seen["idempotency"] == "formation-request-0001"
    assert result.status == "no_memories"
    await client.close()


async def test_submit_formation_job_sends_idempotency_and_budgets() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        seen["idempotency"] = request.headers["idempotency-key"]
        seen["path"] = request.url.path
        return httpx.Response(
            202,
            json={
                "job_id": FORMATION_JOB["job_id"],
                "status": "queued",
                "request_id": "req-job",
            },
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    submitted = await client.submit_formation_job(
        "caller-1",
        [{"speaker": "user", "content": "I prefer Saturday."}],
        idempotency_key="formation-job-0001",
        mode="commit",
        max_memories=4,
        deadline_seconds=20,
    )

    assert isinstance(submitted, FormationJobSubmission)
    assert submitted.status == "queued"
    assert seen["path"] == "/v1/formation/jobs"
    assert seen["idempotency"] == "formation-job-0001"
    sent = json.loads(seen["body"])
    assert sent["mode"] == "commit"
    assert sent["max_memories"] == 4
    assert sent["deadline_seconds"] == 20
    await client.close()


async def test_get_formation_job_parses_attempts_and_candidates() -> None:
    client = mock_client(200, FORMATION_JOB)

    job = await client.get_formation_job(str(FORMATION_JOB["job_id"]))

    assert isinstance(job, FormationJob)
    assert job.status == "succeeded"
    assert job.attempts[0].provider_called is True
    assert job.result is not None
    assert job.result.candidates[0].source == "user_stated"
    await client.close()


async def test_evaluate_action_returns_receipt_target() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/recall_for_action"
        return httpx.Response(
            200,
            json={
                "decision_id": "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
                "outcome": "abstain",
                "memories": [],
                "pending_confirmation_ids": [],
            },
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    decision = await client.evaluate_action("caller-1", "book appointment")

    assert decision.outcome == "abstain"
    assert decision.decision_id == "54a81b8e-52bb-4e57-b4ac-ab78657e89d1"
    assert decision.memories == []
    await client.close()


async def test_report_execution_sends_required_idempotency_key() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["idempotency"] = request.headers["idempotency-key"]
        seen["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={
                "decision_id": "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
                "outcome": "act",
                "receipt": {
                    "id": "7ea64cc8-b53e-47e8-819a-84baf550888a",
                    "decision_id": "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
                    "action_name": "appointment.book",
                    "status": "succeeded",
                    "policy_alignment": "aligned",
                    "external_ref": "appt-42",
                    "error_code": None,
                    "request_id": "req-receipt",
                    "created_at": "2026-08-19T00:00:00+00:00",
                },
            },
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    response = await client.report_execution(
        "caller-1",
        "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
        "appointment.book",
        "succeeded",
        idempotency_key="receipt-request-0001",
        external_ref="appt-42",
        request_id="req-receipt",
    )

    assert seen["idempotency"] == "receipt-request-0001"
    assert json.loads(seen["body"])["external_ref"] == "appt-42"
    assert response.receipt.policy_alignment == "aligned"
    await client.close()


async def test_forget_sends_scoped_selector_and_idempotency_key() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content.decode()
        seen["idempotency"] = request.headers["idempotency-key"]
        return httpx.Response(
            200,
            json={
                "mode": "memory",
                "deleted": 1,
                "verified": None,
                "request_id": "request-forget",
                "memory_version": 7,
                "primary_wal_lsn": "1A/2B",
            },
        )

    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(handler),
    )
    result = await client.forget(
        "caller-1",
        memory_id="memory-1",
        idempotency_key="forget-request-0001",
    )

    assert seen["path"] == "/v1/forget"
    assert seen["idempotency"] == "forget-request-0001"
    assert json.loads(seen["body"])["memory_id"] == "memory-1"
    assert result.deleted == 1
    assert result.memory_version == 7
    await client.close()


async def test_forget_requires_partition_confirmation() -> None:
    client = CloudClient(
        "http://127.0.0.1:8080",
        api_key="cdb_test",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    )
    with pytest.raises(ValueError, match="confirmation=user_id"):
        await client.forget("caller-1", erase_partition=True)
    await client.close()
