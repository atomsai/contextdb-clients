/**
 * Typed contracts for the data-plane API, mirroring clients/openapi/v1alpha.yaml.
 * Keep these in sync with the contract in the same PR that changes either.
 */

export type EpistemicSource = "user_stated" | "agent_inferred" | "third_party";

export interface ConsistencyToken {
  memory_version: number;
  primary_wal_lsn: string | null;
}

export interface Memory {
  id: string;
  content: string;
  user_id: string | null;
  epistemic_source: EpistemicSource;
  confidence: number;
  corroboration_count: number;
  action_relevant: boolean;
  requires_confirmation: boolean;
  confirmed: boolean;
  independent_corroboration: number;
  injection_suspect: boolean;
  entity_key: string | null;
  attribute_key: string | null;
  valid_until: string | null;
  superseded_by: string | null;
  memory_version?: number;
  primary_wal_lsn?: string | null;
}

export interface RecallResult {
  context: string;
  memories: Memory[];
}

export type ReadConsistency = "default" | "primary" | "replica_fallback";

export type ActionOutcome = "act" | "ask" | "abstain";

export interface ActionDecision {
  decision_id: string;
  outcome: ActionOutcome;
  memories: Memory[];
  pending_confirmation_ids: string[];
}

export type ReceiptStatus = "succeeded" | "failed" | "skipped";
export type PolicyAlignment = "aligned" | "violated";

export interface ExecutionReceipt {
  id: string;
  decision_id: string;
  action_name: string;
  status: ReceiptStatus;
  policy_alignment: PolicyAlignment;
  external_ref: string | null;
  error_code: string | null;
  request_id: string;
  created_at: string;
}

export interface ExecutionReceiptResponse {
  decision_id: string;
  outcome: ActionOutcome;
  receipt: ExecutionReceipt;
}

export type ForgetMode = "memory" | "slot" | "partition";

export interface ForgetResponse extends ConsistencyToken {
  mode: ForgetMode;
  deleted: number;
  verified: boolean | null;
  request_id: string;
}

export interface Health {
  ok: boolean;
  service: string;
  sdk_pin?: string;
}

export interface Ready {
  ready: boolean;
  checks: Record<string, boolean>;
}

export interface RememberItem {
  content: string;
  source?: EpistemicSource;
  confidence?: number;
  action_relevant?: boolean;
  entity?: string;
  attribute?: string;
}

export type FormationMode = "propose" | "commit";

export type FormationStatus =
  | "completed"
  | "no_memories"
  | "provider_unavailable"
  | "provider_error"
  | "invalid_output"
  | "timed_out"
  | "budget_exhausted"
  | "storage_error"
  | "internal_error"
  | "interrupted";

export interface FormationTurn {
  speaker: "user" | "agent" | "third_party";
  content: string;
}

export interface FormationCandidate {
  content: string;
  quote: string;
  turn_indexes: number[];
  source: EpistemicSource;
  confidence: number;
  action_relevant: boolean;
  entity: string | null;
  attribute: string | null;
}

export interface FormationResponse {
  run_id: string;
  status: FormationStatus;
  mode: FormationMode;
  attempts: number;
  candidates: FormationCandidate[];
  memories: Memory[];
  error_code: string | null;
  request_id: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(`[${status}] ${code}: ${message}`);
    this.name = "ApiError";
  }
}
