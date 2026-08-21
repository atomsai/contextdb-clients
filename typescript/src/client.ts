/**
 * CloudClient — the remote client for the ContextDB Cloud data plane.
 *
 * Speaks the versioned contract in clients/openapi/v1alpha.yaml. The API
 * key is a project-wide server credential (`cdb_…`): keep it in your
 * server's secret store, never in a browser or client-side code.
 *
 * Hosted alpha. Not production-ready.
 */

import {
  ActionDecision,
  ApiError,
  ConsistencyToken,
  EpistemicSource,
  ExecutionReceiptResponse,
  ForgetResponse,
  FormationJob,
  FormationJobSubmission,
  FormationMode,
  FormationResponse,
  FormationTurn,
  Health,
  Memory,
  Ready,
  ReadConsistency,
  RecallResult,
  ReceiptStatus,
  RememberItem,
} from "./types.js";

export interface CloudClientOptions {
  baseUrl: string;
  apiKey: string;
  timeoutMs?: number;
  fetchFn?: typeof fetch;
}

export class CloudClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly fetchFn: typeof fetch;

  constructor(options: CloudClientOptions) {
    if (typeof window !== "undefined") {
      throw new Error(
        "@contextdb/cloud is server-only; project API keys must never run in browser code",
      );
    }
    if (!options.apiKey.startsWith("cdb_")) {
      throw new Error("apiKey must be a project key (cdb_…)");
    }
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.fetchFn = options.fetchFn ?? fetch;
  }

  private async call<T>(
    method: string,
    path: string,
    body?: unknown,
    query?: Record<string, string>,
    requestId?: string,
    idempotencyKey?: string,
  ): Promise<T> {
    const url = new URL(this.baseUrl + path);
    for (const [k, v] of Object.entries(query ?? {})) url.searchParams.set(k, v);
    const headers: Record<string, string> = {
      authorization: `Bearer ${this.apiKey}`,
    };
    if (body !== undefined) headers["content-type"] = "application/json";
    if (requestId) headers["x-request-id"] = requestId;
    if (idempotencyKey) headers["idempotency-key"] = idempotencyKey;

    const resp = await this.fetchFn(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    let data: Record<string, unknown> = {};
    try {
      data = (await resp.json()) as Record<string, unknown>;
    } catch {
      throw new ApiError(resp.status, "non_json", "non-JSON response");
    }
    if (!resp.ok) {
      throw new ApiError(
        resp.status,
        String(data.code ?? "error"),
        String(data.message ?? `HTTP ${resp.status}`),
        data.request_id as string | undefined,
      );
    }
    return data as T;
  }

  async health(): Promise<Health> {
    return this.call<Health>("GET", "/health");
  }

  async ready(): Promise<Ready> {
    return this.call<Ready>("GET", "/ready");
  }

  async remember(
    userId: string,
    content: string,
    options: {
      source: EpistemicSource;
      confidence?: number;
      actionRelevant?: boolean;
      entity?: string;
      attribute?: string;
      requestId?: string;
      idempotencyKey?: string;
    },
  ): Promise<Memory> {
    const body: Record<string, unknown> = {
      user_id: userId,
      content,
      source: options.source,
    };
    if (options.confidence !== undefined) body.confidence = options.confidence;
    if (options.actionRelevant !== undefined)
      body.action_relevant = options.actionRelevant;
    if (options.entity !== undefined) body.entity = options.entity;
    if (options.attribute !== undefined) body.attribute = options.attribute;
    const data = await this.call<{ memory: Memory } & ConsistencyToken>(
      "POST",
      "/v1/remember",
      body,
      undefined,
      options.requestId,
      options.idempotencyKey,
    );
    return {
      ...data.memory,
      memory_version: data.memory_version,
      primary_wal_lsn: data.primary_wal_lsn,
    };
  }

  async rememberMany(
    userId: string,
    items: RememberItem[],
    requestId?: string,
    idempotencyKey?: string,
  ): Promise<Memory[]> {
    const data = await this.call<
      { memories: Memory[] } & ConsistencyToken
    >(
      "POST",
      "/v1/remember_many",
      { user_id: userId, items },
      undefined,
      requestId,
      idempotencyKey,
    );
    return data.memories.map((memory) => ({
      ...memory,
      memory_version: data.memory_version,
      primary_wal_lsn: data.primary_wal_lsn,
    }));
  }

  async extractMemories(
    userId: string,
    turns: FormationTurn[],
    options: {
      mode?: FormationMode;
      sourceId?: string;
      maxMemories?: number;
      requestId?: string;
      idempotencyKey?: string;
    } = {},
  ): Promise<FormationResponse> {
    const url = new URL(this.baseUrl + "/v1/extract_memories");
    const headers: Record<string, string> = {
      authorization: `Bearer ${this.apiKey}`,
      "content-type": "application/json",
    };
    if (options.requestId) headers["x-request-id"] = options.requestId;
    if (options.idempotencyKey)
      headers["idempotency-key"] = options.idempotencyKey;
    const body: Record<string, unknown> = {
      user_id: userId,
      turns,
      mode: options.mode ?? "propose",
      max_memories: options.maxMemories ?? 10,
    };
    if (options.sourceId !== undefined) body.source_id = options.sourceId;

    const response = await this.fetchFn(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    let data: Record<string, unknown>;
    try {
      data = (await response.json()) as Record<string, unknown>;
    } catch {
      throw new ApiError(response.status, "non_json", "non-JSON response");
    }
    if ("run_id" in data && "status" in data) {
      return data as unknown as FormationResponse;
    }
    if (!response.ok) {
      throw new ApiError(
        response.status,
        String(data.code ?? "error"),
        String(data.message ?? `HTTP ${response.status}`),
        data.request_id as string | undefined,
      );
    }
    throw new ApiError(
      response.status,
      "invalid_response",
      "formation response is missing terminal status",
      data.request_id as string | undefined,
    );
  }

  async submitFormationJob(
    userId: string,
    turns: FormationTurn[],
    options: {
      idempotencyKey: string;
      mode?: FormationMode;
      sourceId?: string;
      maxMemories?: number;
      deadlineSeconds?: number;
      requestId?: string;
    },
  ): Promise<FormationJobSubmission> {
    const body: Record<string, unknown> = {
      user_id: userId,
      turns,
      mode: options.mode ?? "propose",
      max_memories: options.maxMemories ?? 10,
      deadline_seconds: options.deadlineSeconds ?? 25,
    };
    if (options.sourceId !== undefined) body.source_id = options.sourceId;
    return this.call<FormationJobSubmission>(
      "POST",
      "/v1/formation/jobs",
      body,
      undefined,
      options.requestId,
      options.idempotencyKey,
    );
  }

  async getFormationJob(
    jobId: string,
    requestId?: string,
  ): Promise<FormationJob> {
    return this.call<FormationJob>(
      "GET",
      `/v1/formation/jobs/${encodeURIComponent(jobId)}`,
      undefined,
      undefined,
      requestId,
    );
  }

  async recall(
    userId: string,
    query: string,
    options: {
      topK?: number;
      entity?: string;
      minConfidence?: number;
      minMemoryVersion?: number;
      minPrimaryWalLsn?: string;
      readConsistency?: ReadConsistency;
      requestId?: string;
    } = {},
  ): Promise<RecallResult> {
    const body: Record<string, unknown> = {
      user_id: userId,
      query,
      top_k: options.topK ?? 5,
    };
    if (options.entity !== undefined) body.entity = options.entity;
    if (options.minConfidence !== undefined)
      body.min_confidence = options.minConfidence;
    if (options.minMemoryVersion !== undefined)
      body.min_memory_version = options.minMemoryVersion;
    if (options.minPrimaryWalLsn !== undefined)
      body.min_primary_wal_lsn = options.minPrimaryWalLsn;
    if (
      options.readConsistency !== undefined &&
      options.readConsistency !== "default"
    )
      body.read_consistency = options.readConsistency;
    return this.call<RecallResult>(
      "POST",
      "/v1/recall",
      body,
      undefined,
      options.requestId,
    );
  }

  async recallForAction(
    userId: string,
    query: string,
    options: { topK?: number; requestId?: string } = {},
  ): Promise<Memory[]> {
    const decision = await this.evaluateAction(userId, query, options);
    return decision.memories;
  }

  async evaluateAction(
    userId: string,
    query: string,
    options: { topK?: number; requestId?: string } = {},
  ): Promise<ActionDecision> {
    return this.call<ActionDecision>(
      "POST",
      "/v1/recall_for_action",
      { user_id: userId, query, top_k: options.topK ?? 5 },
      undefined,
      options.requestId,
    );
  }

  async pendingConfirmations(userId: string): Promise<Memory[]> {
    const data = await this.call<{ memories: Memory[] }>(
      "GET",
      "/v1/pending_confirmations",
      undefined,
      { user_id: userId },
    );
    return data.memories;
  }

  /**
   * Record an explicit user confirmation for a pending memory. Closes the
   * ask -> confirm -> act loop: the fact becomes confirmed and passes
   * recallForAction. A memory outside this project's partition throws an
   * ApiError with status 404, indistinguishable from a missing one.
   */
  async confirm(
    userId: string,
    memoryId: string,
    requestId?: string,
    idempotencyKey?: string,
  ): Promise<Memory> {
    const data = await this.call<{ memory: Memory } & ConsistencyToken>(
      "POST",
      "/v1/confirm",
      { user_id: userId, memory_id: memoryId },
      undefined,
      requestId,
      idempotencyKey,
    );
    return {
      ...data.memory,
      memory_version: data.memory_version,
      primary_wal_lsn: data.primary_wal_lsn,
    };
  }

  async forget(
    userId: string,
    options: {
      memoryId?: string;
      entity?: string;
      attribute?: string;
      erasePartition?: boolean;
      confirmation?: string;
      requestId?: string;
      idempotencyKey?: string;
    },
  ): Promise<ForgetResponse> {
    if ((options.entity === undefined) !== (options.attribute === undefined)) {
      throw new Error("entity and attribute must be set together");
    }
    const modes =
      Number(options.memoryId !== undefined) +
      Number(options.entity !== undefined) +
      Number(options.erasePartition === true);
    if (modes !== 1) {
      throw new Error(
        "choose memoryId, entity+attribute, or erasePartition",
      );
    }
    if (
      options.erasePartition &&
      (options.confirmation !== userId || !options.idempotencyKey)
    ) {
      throw new Error(
        "partition erasure requires confirmation=userId and idempotencyKey",
      );
    }
    const body: Record<string, unknown> = {
      user_id: userId,
      erase_partition: options.erasePartition ?? false,
    };
    if (options.memoryId !== undefined) body.memory_id = options.memoryId;
    if (options.entity !== undefined) {
      body.entity = options.entity;
      body.attribute = options.attribute;
    }
    if (options.confirmation !== undefined)
      body.confirmation = options.confirmation;
    return this.call<ForgetResponse>(
      "POST",
      "/v1/forget",
      body,
      undefined,
      options.requestId,
      options.idempotencyKey,
    );
  }

  async reportExecution(
    userId: string,
    decisionId: string,
    actionName: string,
    status: ReceiptStatus,
    options: {
      idempotencyKey: string;
      externalRef?: string;
      errorCode?: string;
      requestId?: string;
    },
  ): Promise<ExecutionReceiptResponse> {
    const body: Record<string, unknown> = {
      user_id: userId,
      decision_id: decisionId,
      action_name: actionName,
      status,
    };
    if (options.externalRef !== undefined)
      body.external_ref = options.externalRef;
    if (options.errorCode !== undefined) body.error_code = options.errorCode;
    return this.call<ExecutionReceiptResponse>(
      "POST",
      "/v1/receipts",
      body,
      undefined,
      options.requestId,
      options.idempotencyKey,
    );
  }
}
