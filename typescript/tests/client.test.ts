import { describe, expect, it, vi } from "vitest";
import { ApiError, CloudClient } from "../src/index.js";
import type { Memory } from "../src/index.js";

const memory: Memory = {
  id: "m1",
  content: "I'd like to come in Thursday afternoon.",
  user_id: "caller-1",
  epistemic_source: "user_stated",
  confidence: 0.95,
  corroboration_count: 1,
  action_relevant: true,
  requires_confirmation: false,
  confirmed: false,
  independent_corroboration: 1,
  injection_suspect: false,
  entity_key: "caller",
  attribute_key: "preferred_visit_day",
  valid_until: null,
  superseded_by: null,
};

function mockFetch(status: number, body: unknown) {
  return vi.fn(
    async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json" },
      }),
  ) as unknown as typeof fetch;
}

function clientWith(fetchFn: typeof fetch): CloudClient {
  return new CloudClient({
    baseUrl: "http://127.0.0.1:8080",
    apiKey: "cdb_test_key",
    fetchFn,
  });
}

describe("CloudClient", () => {
  it("rejects non-project keys at construction", () => {
    expect(
      () => new CloudClient({ baseUrl: "http://x", apiKey: "nope" }),
    ).toThrow("cdb_");
  });

  it("remember sends provenance and bearer auth", async () => {
    const fetchFn = mockFetch(200, {
      memory,
      memory_version: 3,
      primary_wal_lsn: "1A/2B",
    });
    const cdb = clientWith(fetchFn);
    const result = await cdb.remember("caller-1", "Thursday works", {
      source: "user_stated",
      confidence: 0.95,
      idempotencyKey: "remember-request-0001",
    });
    expect(result.id).toBe("m1");
    expect(result.memory_version).toBe(3);
    expect(result.primary_wal_lsn).toBe("1A/2B");
    const [url, init] = vi.mocked(fetchFn).mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect(url.pathname).toBe("/v1/remember");
    expect((init.headers as Record<string, string>).authorization).toBe(
      "Bearer cdb_test_key",
    );
    expect((init.headers as Record<string, string>)["idempotency-key"]).toBe(
      "remember-request-0001",
    );
    const sent = JSON.parse(String(init.body));
    expect(sent.source).toBe("user_stated");
    expect(sent.user_id).toBe("caller-1");
  });

  it("recall returns context and memories", async () => {
    const fetchFn = mockFetch(200, { context: "[...]", memories: [memory] });
    const cdb = clientWith(fetchFn);
    const result = await cdb.recall("caller-1", "when?", {
      minMemoryVersion: 3,
      minPrimaryWalLsn: "1A/2B",
      readConsistency: "replica_fallback",
    });
    expect(result.context).toBe("[...]");
    expect(result.memories).toHaveLength(1);
    const [, init] = vi.mocked(fetchFn).mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect(JSON.parse(String(init.body))).toMatchObject({
      min_memory_version: 3,
      min_primary_wal_lsn: "1A/2B",
      read_consistency: "replica_fallback",
    });
  });

  it("recallForAction returns the trusted list", async () => {
    const fetchFn = mockFetch(200, {
      decision_id: "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
      outcome: "act",
      memories: [memory],
      pending_confirmation_ids: [],
    });
    const cdb = clientWith(fetchFn);
    const result = await cdb.recallForAction("caller-1", "book it");
    expect(result[0].requires_confirmation).toBe(false);
  });

  it("evaluateAction returns the durable receipt target", async () => {
    const fetchFn = mockFetch(200, {
      decision_id: "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
      outcome: "abstain",
      memories: [],
      pending_confirmation_ids: [],
    });
    const cdb = clientWith(fetchFn);
    const result = await cdb.evaluateAction("caller-1", "book it");

    expect(result.decision_id).toBe(
      "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
    );
    expect(result.outcome).toBe("abstain");
  });

  it("reportExecution sends structured fields and an idempotency key", async () => {
    const fetchFn = mockFetch(200, {
      decision_id: "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
      outcome: "act",
      receipt: {
        id: "7ea64cc8-b53e-47e8-819a-84baf550888a",
        decision_id: "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
        action_name: "appointment.book",
        status: "succeeded",
        policy_alignment: "aligned",
        external_ref: "appt-42",
        error_code: null,
        request_id: "req-receipt",
        created_at: "2026-08-19T00:00:00+00:00",
      },
    });
    const cdb = clientWith(fetchFn);

    const result = await cdb.reportExecution(
      "caller-1",
      "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
      "appointment.book",
      "succeeded",
      {
        idempotencyKey: "receipt-request-0001",
        externalRef: "appt-42",
        requestId: "req-receipt",
      },
    );

    const [url, init] = vi.mocked(fetchFn).mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect(url.pathname).toBe("/v1/receipts");
    expect((init.headers as Record<string, string>)["idempotency-key"]).toBe(
      "receipt-request-0001",
    );
    expect(JSON.parse(String(init.body))).toMatchObject({
      action_name: "appointment.book",
      external_ref: "appt-42",
    });
    expect(result.receipt.policy_alignment).toBe("aligned");
  });

  it("pendingConfirmations passes user_id as a query parameter", async () => {
    const fetchFn = mockFetch(200, { memories: [] });
    const cdb = clientWith(fetchFn);
    await cdb.pendingConfirmations("caller-1");
    const [url] = vi.mocked(fetchFn).mock.calls[0] as unknown as [URL];
    expect(url.searchParams.get("user_id")).toBe("caller-1");
  });

  it("confirm posts user_id and memory_id and returns the memory", async () => {
    const fetchFn = mockFetch(200, { memory: { ...memory, confirmed: true } });
    const cdb = clientWith(fetchFn);
    const result = await cdb.confirm("caller-1", "m1");
    expect(result.confirmed).toBe(true);
    const [url, init] = vi.mocked(fetchFn).mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect(url.pathname).toBe("/v1/confirm");
    const sent = JSON.parse(String(init.body));
    expect(sent).toEqual({ user_id: "caller-1", memory_id: "m1" });
  });

  it("confirm surfaces foreign or missing memories as a 404 ApiError", async () => {
    const fetchFn = mockFetch(404, {
      code: "not_found",
      message: "memory not found in this partition",
    });
    const cdb = clientWith(fetchFn);
    const err = await cdb.confirm("caller-1", "other").catch((e: unknown) => e);
    expect((err as ApiError).status).toBe(404);
  });

  it("forget deletes one scoped memory", async () => {
    const fetchFn = mockFetch(200, {
      mode: "memory",
      deleted: 1,
      verified: null,
      request_id: "request-forget",
      memory_version: 7,
      primary_wal_lsn: "1A/2B",
    });
    const cdb = clientWith(fetchFn);

    const result = await cdb.forget("caller-1", {
      memoryId: "m1",
      idempotencyKey: "forget-request-0001",
    });

    const [url, init] = vi.mocked(fetchFn).mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect(url.pathname).toBe("/v1/forget");
    expect((init.headers as Record<string, string>)["idempotency-key"]).toBe(
      "forget-request-0001",
    );
    expect(JSON.parse(String(init.body))).toMatchObject({
      user_id: "caller-1",
      memory_id: "m1",
      erase_partition: false,
    });
    expect(result.deleted).toBe(1);
    expect(result.memory_version).toBe(7);
  });

  it("requires typed confirmation and idempotency for partition erasure", async () => {
    const cdb = clientWith(mockFetch(200, {}));
    await expect(
      cdb.forget("caller-1", { erasePartition: true }),
    ).rejects.toThrow("confirmation=userId");
  });

  it("extractMemories returns a named terminal provider failure", async () => {
    const fetchFn = mockFetch(502, {
      run_id: "form_1",
      status: "provider_error",
      mode: "propose",
      attempts: 2,
      candidates: [],
      memories: [],
      error_code: "provider_error",
      request_id: "req-form",
    });
    const cdb = clientWith(fetchFn);

    const result = await cdb.extractMemories("caller-1", [
      { speaker: "user", content: "I prefer Saturday." },
    ]);

    expect(result.status).toBe("provider_error");
    expect(result.attempts).toBe(2);
  });

  it("extractMemories sends mode, source id, and request id", async () => {
    const fetchFn = mockFetch(200, {
      run_id: "form_1",
      status: "no_memories",
      mode: "commit",
      attempts: 1,
      candidates: [],
      memories: [],
      error_code: null,
      request_id: "req-form",
    });
    const cdb = clientWith(fetchFn);

    await cdb.extractMemories(
      "caller-1",
      [{ speaker: "user", content: "Thanks." }],
      {
        mode: "commit",
        sourceId: "call-1",
        requestId: "req-form",
        idempotencyKey: "formation-request-0001",
      },
    );

    const [url, init] = vi.mocked(fetchFn).mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect(url.pathname).toBe("/v1/extract_memories");
    expect((init.headers as Record<string, string>)["x-request-id"]).toBe(
      "req-form",
    );
    expect((init.headers as Record<string, string>)["idempotency-key"]).toBe(
      "formation-request-0001",
    );
    expect(JSON.parse(String(init.body))).toMatchObject({
      user_id: "caller-1",
      mode: "commit",
      source_id: "call-1",
    });
  });

  it("maps error responses to ApiError with code and request id", async () => {
    const fetchFn = mockFetch(401, {
      code: "unauthenticated",
      message: "unknown or revoked API key",
      request_id: "req-9",
    });
    const cdb = clientWith(fetchFn);
    const err = await cdb.recall("u", "q").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(401);
    expect((err as ApiError).code).toBe("unauthenticated");
    expect((err as ApiError).requestId).toBe("req-9");
  });

  it("maps non-JSON responses to a non_json error", async () => {
    const fetchFn = vi.fn(
      async () => new Response("boom", { status: 502 }),
    ) as unknown as typeof fetch;
    const cdb = clientWith(fetchFn);
    const err = await cdb.health().catch((e: unknown) => e);
    expect((err as ApiError).code).toBe("non_json");
  });

  it("sends X-Request-ID when provided", async () => {
    const fetchFn = mockFetch(200, {
      decision_id: "54a81b8e-52bb-4e57-b4ac-ab78657e89d1",
      outcome: "abstain",
      memories: [],
      pending_confirmation_ids: [],
    });
    const cdb = clientWith(fetchFn);
    await cdb.recallForAction("u", "q", { requestId: "req-77" });
    const [, init] = vi.mocked(fetchFn).mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect((init.headers as Record<string, string>)["x-request-id"]).toBe(
      "req-77",
    );
  });
});
